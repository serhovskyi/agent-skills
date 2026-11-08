"""The fixtures are synthetic recordings of an invented shop app, shaped line for line like real
pytest, vitest, alembic and git output, escapes and reporter glyphs included.
"""

import os
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest
from harness_support import BIN, SUBPROCESS_HANG_BUDGET_SECONDS

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "evidence_run"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
NOTE = re.compile(
    r"^\[evidence-run\] dropped (?P<dropped>\d+) of (?P<total>\d+) output lines as runner "
    r"noise; full output: (?P<raw>\S+)$"
)
PYTEST_ARGV = ("compose", "exec", "-T", "backend", "pytest", "--no-cov", "-q", "-m", "pg")
VITEST_ARGV = ("compose", "exec", "-T", "frontend", "npx", "vitest", "run", "--project", "dom")
ALEMBIC_ARGV = ("compose", "exec", "-T", "backend", "alembic")
FILTER_FAILED = b"[evidence-run] the filter failed; the output above is whole\n"

EVIDENCE_RUN = BIN / "evidence-run"
SUITE_SUMMARY = BIN / "suite-summary"


def _out_of_order(needles: list[str], haystack: list[str]) -> list[str]:
    misplaced: list[str] = []
    position = 0
    for needle in needles:
        try:
            position = haystack.index(needle, position) + 1
        except ValueError:
            misplaced.append(needle)
    return misplaced


def _env_with(path_prefix: Path | None) -> dict[str, str] | None:
    if path_prefix is None:
        return None
    return {**os.environ, "PATH": f"{path_prefix}:{os.environ['PATH']}"}


class Recording:
    def __init__(
        self,
        tmp_path: Path,
        fixture: str,
        program: str,
        *args: str,
        exit_code: int = 0,
        path_prefix: Path | None = None,
        script: Path = EVIDENCE_RUN,
    ) -> None:
        self.fixture = (FIXTURES / fixture).read_bytes()
        self.stand_in = tmp_path / "bin" / program
        self.stand_in.parent.mkdir(exist_ok=True)
        self.stand_in.write_text(f'#!/bin/sh\ncat "{FIXTURES / fixture}"\nexit {exit_code}\n')
        self.stand_in.chmod(0o755)
        self.args = args
        self.evidence = tmp_path / "evidence.txt"
        self.result = subprocess.run(
            ["bash", str(script), str(self.evidence), str(self.stand_in), *args],
            capture_output=True,
            timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
            env=_env_with(path_prefix),
            check=False,
        )
        self.lines = self.evidence.read_text(encoding="utf-8").splitlines()

    @property
    def body(self) -> list[str]:
        return [line for line in self.lines[1:-1] if not NOTE.match(line)]

    @property
    def notes(self) -> list[re.Match[str]]:
        return [match for line in self.lines if (match := NOTE.match(line))]

    @property
    def fixture_lines(self) -> list[str]:
        return ANSI.sub("", self.fixture.decode("utf-8")).splitlines()

    def lost(self, expected: list[str]) -> list[str]:
        return list((Counter(expected) - Counter(self.body)).elements())

    def reordered(self) -> list[str]:
        return _out_of_order(self.body, self.fixture_lines)

    def leaked(self, *markers: str) -> list[str]:
        return [line for line in self.body if any(marker in line for marker in markers)]


def _pytest_red(tmp_path: Path) -> Recording:
    return Recording(
        tmp_path,
        "pytest-migration-red.txt",
        "docker",
        *PYTEST_ARGV,
        "tests/migrations/test_order_totals_migration.py",
        exit_code=1,
    )


def _vitest_red(tmp_path: Path) -> Recording:
    return Recording(
        tmp_path,
        "vitest-dump-red.txt",
        "docker",
        *VITEST_ARGV,
        exit_code=1,
    )


def test_the_runner_exit_code_command_line_and_exit_line_frame_the_evidence(tmp_path):
    run = _pytest_red(tmp_path)

    assert run.result.returncode == 1
    assert run.lines[0] == " ".join([str(run.stand_in), *run.args]) + " "
    assert run.lines[-1] == "EXIT=1"


def test_a_pytest_red_keeps_assertions_failed_lines_summary_and_the_test_frame(tmp_path):
    run = _pytest_red(tmp_path)
    expected = [
        line
        for line in run.fixture_lines
        if line.startswith(("E ", "FAILED ", ">       run_alembic"))
        or re.match(r"^=+ .+ =+$|^_{3,} test_\w+ _{3,}$|^tests/migrations/\S+:\d+: ", line)
    ]

    lost, reordered = run.lost(expected), run.reordered()
    assert not lost, f"{len(lost)} lines lost"
    assert not reordered, f"{len(reordered)} lines out of the fixture's order"


def test_a_short_traceback_under_a_long_test_name_loses_nothing(tmp_path):
    run = Recording(tmp_path, "pytest-long-name-red.txt", "docker", *PYTEST_ARGV, exit_code=1)

    lost = run.lost(run.fixture_lines)
    assert not lost, f"{len(lost)} lines lost"


def test_a_long_traceback_keeps_the_raising_line_before_its_assertion(tmp_path):
    run = Recording(tmp_path, "pytest-long-tb-red.txt", "docker", *PYTEST_ARGV, exit_code=1)
    expected = [
        ">       assert value == 7",
        "E       assert 6 == 7",
        "tests/test_orders_scratch.py:10: AssertionError",
    ]

    lost, reordered = run.lost(expected), run.reordered()
    assert not lost, f"{len(lost)} lines lost"
    assert not reordered, f"{len(reordered)} lines out of the fixture's order"
    assert run.leaked("value = _doubled(3)") == []


def test_the_warnings_summary_stays_whole(tmp_path):
    run = Recording(tmp_path, "pytest-long-tb-red.txt", "docker", *PYTEST_ARGV, exit_code=1)
    lines = run.fixture_lines
    start = next(i for i, line in enumerate(lines) if "warnings summary" in line)
    end = next(i for i, line in enumerate(lines) if "short test summary" in line)

    lost = run.lost([line for line in lines[start:end] if line])
    assert not lost, f"{len(lost)} lines lost"


def test_a_pytest_red_drops_captured_sections_alembic_logging_and_library_frames(tmp_path):
    run = _pytest_red(tmp_path)

    leaked = run.leaked("Captured", "INFO", "site-packages", "<frozen", "self = ", "_ _ _")
    assert not leaked, f"{len(leaked)} noise lines kept"
    assert len(run.body) < len(run.fixture_lines) // 10


def test_the_drop_note_counts_what_the_evidence_lacks_and_names_the_raw_log(tmp_path):
    run = _pytest_red(tmp_path)
    raw_log = tmp_path / "evidence.txt.raw.log"

    [note] = run.notes
    assert int(note["total"]) == len(run.fixture_lines)
    assert int(note["dropped"]) == len(run.fixture_lines) - len(run.body)
    assert note["raw"] == raw_log.name
    assert run.fixture in raw_log.read_bytes()


def test_a_vitest_red_keeps_results_failures_and_the_summary(tmp_path):
    run = _vitest_red(tmp_path)
    expected = [
        line
        for line in run.fixture_lines
        if re.match(r"^\s*(?:[✓\u00d7\u276f] |FAIL |Test Files |Tests |AssertionError)", line)
    ]

    assert run.result.returncode == 1
    lost, reordered = run.lost(expected), run.reordered()
    assert not lost, f"{len(lost)} lines lost"
    assert not reordered, f"{len(reordered)} lines out of the fixture's order"


def test_a_vitest_red_drops_its_stderr_dumps_and_every_escape(tmp_path):
    run = _vitest_red(tmp_path)

    leaked = run.leaked("stderr |", "ECONNREFUSED", "DOMException", "<VTUROOT>", "\x1b")
    assert not leaked, f"{len(leaked)} noise lines kept"


def test_a_vitest_stdout_dump_is_what_the_test_printed_and_stays(tmp_path):
    run = Recording(tmp_path, "vitest-stdout-green.txt", "docker", *VITEST_ARGV)
    printed = [line for line in run.fixture_lines if "old=" in line]

    assert len(printed) == 5
    lost = run.lost(printed)
    assert not lost, f"{len(lost)} lines lost"


def test_a_git_diff_reaches_the_evidence_byte_for_byte_without_a_note(tmp_path):
    run = Recording(tmp_path, "git-diff-trim.txt", "git", "diff", "HEAD~1", "HEAD")

    recorded = run.evidence.read_bytes().split(b"\n", 1)[1].rsplit(b"EXIT=0\n", 1)[0]
    assert recorded == run.fixture
    assert run.notes == []


def test_the_argv_not_the_content_classifies_a_block_as_runner_output(tmp_path):
    run = Recording(tmp_path, "git-diff-trim.txt", "pytest")

    assert len(run.notes) == 1


def test_alembic_current_drops_its_preamble_and_keeps_its_answer(tmp_path):
    run = Recording(tmp_path, "alembic-current.txt", "docker", *ALEMBIC_ARGV, "current")

    assert run.body == ["012"]
    [note] = run.notes
    assert int(note["dropped"]) == 2


def test_alembic_upgrade_keeps_every_running_upgrade_line(tmp_path):
    run = Recording(tmp_path, "alembic-upgrade.txt", "docker", *ALEMBIC_ARGV, "upgrade", "head")

    assert run.body == run.fixture_lines[2:]
    assert run.leaked("Context impl", "Will assume") == []


def test_a_filter_that_fails_leaves_the_whole_output_and_the_runner_exit_code(tmp_path):
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    broken_python = shadow / "python3"
    broken_python.write_text("#!/bin/sh\nexit 1\n")
    broken_python.chmod(0o755)
    run = Recording(
        tmp_path,
        "pytest-migration-red.txt",
        "docker",
        *PYTEST_ARGV,
        exit_code=1,
        path_prefix=shadow,
    )

    after_command_line = run.evidence.read_bytes().split(b"\n", 1)[1]
    assert after_command_line == run.fixture + FILTER_FAILED + b"EXIT=1\n"
    assert run.result.returncode == 1


def _summary(log: Path, script: Path = SUITE_SUMMARY) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), str(log)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
        check=False,
    )


def _logged(tmp_path: Path, fixture: str, status: int) -> Path:
    log = tmp_path / "suite.log"
    log.write_bytes((FIXTURES / fixture).read_bytes() + f"EXIT={status}\n".encode())
    return log


def _fixture_lines(fixture: str) -> list[str]:
    return ANSI.sub("", (FIXTURES / fixture).read_text(encoding="utf-8")).splitlines()


def test_a_vitest_log_reads_as_its_summary_without_escapes_and_a_labelled_exit():
    result = _summary(FIXTURES / "suite-vitest-green.txt")

    assert result.stdout.splitlines() == [
        " Test Files  1 passed (1)",
        "      Tests  3 passed (3)",
        "suite EXIT=0",
    ]
    assert result.returncode == 0


def test_a_pytest_log_reads_as_its_final_line_and_a_labelled_exit():
    result = _summary(FIXTURES / "suite-pytest-green.txt")

    assert result.stdout.splitlines() == [
        "============================= 14 passed in 26.20s ==============================",
        "suite EXIT=0",
    ]
    assert result.returncode == 0


def test_a_log_that_does_not_end_in_exit_is_not_a_quiet_green(tmp_path):
    whole = (FIXTURES / "suite-vitest-green.txt").read_text(encoding="utf-8")
    truncated = tmp_path / "suite.log"
    truncated.write_text(whole[: whole.rindex("EXIT=")], encoding="utf-8")

    result = _summary(truncated)

    assert result.returncode == os.EX_DATAERR
    assert "suite EXIT=" not in result.stdout
    assert "does not end in an EXIT= line" in result.stderr


def test_a_log_without_a_summary_line_is_not_a_quiet_green(tmp_path):
    result = _summary(_logged(tmp_path, "git-diff-trim.txt", 0))

    assert result.returncode == os.EX_DATAERR
    assert "has no summary line" in result.stderr


def test_a_red_pytest_suite_keeps_its_failed_lines_and_exits_with_its_status(tmp_path):
    lines = _fixture_lines("pytest-migration-red.txt")

    result = _summary(_logged(tmp_path, "pytest-migration-red.txt", 1))

    failed = [line for line in lines if line.startswith("FAILED ")]
    assert len(failed) == 4
    assert result.stdout.splitlines() == [*failed, lines[-1], "suite EXIT=1"]
    assert result.returncode == 1


def test_a_red_vitest_suite_keeps_its_failing_files_and_exits_with_its_status(tmp_path):
    lines = _fixture_lines("vitest-dump-red.txt")

    result = _summary(_logged(tmp_path, "vitest-dump-red.txt", 1))

    failing = [line.rstrip() for line in lines if re.match(r"^\s*(?:FAIL|\u00d7)\s", line)]
    assert len(failing) == 3
    assert result.stdout.splitlines() == [
        *failing,
        " Test Files  1 failed (1)",
        "      Tests  1 failed | 1 passed (2)",
        "suite EXIT=1",
    ]
    assert result.returncode == 1


def test_a_captured_error_log_record_is_not_a_summary_line():
    result = _summary(FIXTURES / "suite-pytest-setup-error.txt")

    assert result.stdout.splitlines() == [
        "ERROR ::test_errors_in_setup - RuntimeError: setup broke",
        "========================== 1 passed, 1 error in 4.15s ==========================",
        "suite EXIT=1",
    ]
    assert result.returncode == 1


def test_a_skipped_only_run_still_reads_as_a_summary():
    result = _summary(FIXTURES / "suite-pytest-skipped.txt")

    assert result.stdout.splitlines() == [
        "============================== 1 skipped in 4.16s ==============================",
        "suite EXIT=0",
    ]
    assert result.returncode == 0


def test_an_unhandled_error_count_precedes_the_suite_exit():
    result = _summary(FIXTURES / "suite-vitest-unhandled.txt")

    assert result.stdout.splitlines() == [
        " Test Files  1 passed (1)",
        "      Tests  1 passed (1)",
        "     Errors  1 error",
        "suite EXIT=1",
    ]
    assert result.returncode == 1


def _linked(tmp_path: Path, script: Path) -> Path:
    link = tmp_path / "linked" / script.name
    link.parent.mkdir(exist_ok=True)
    link.symlink_to(script)
    return link


def test_evidence_run_finds_its_filter_through_a_symlink(tmp_path):
    run = Recording(
        tmp_path,
        "pytest-migration-red.txt",
        "docker",
        *PYTEST_ARGV,
        exit_code=1,
        script=_linked(tmp_path, EVIDENCE_RUN),
    )

    assert FILTER_FAILED not in run.evidence.read_bytes()
    assert len(run.notes) == 1


def test_suite_summary_finds_its_reader_through_a_symlink(tmp_path):
    result = _summary(FIXTURES / "suite-pytest-skipped.txt", _linked(tmp_path, SUITE_SUMMARY))

    assert result.stdout.splitlines()[-1] == "suite EXIT=0"
    assert result.returncode == 0


def test_a_configured_runner_is_filtered_as_runner_output(tmp_path, configured):
    run = Recording(tmp_path, "git-diff-trim.txt", "make", "check-api")

    assert len(run.notes) == 1


def test_a_configured_runner_is_verbatim_without_a_config(tmp_path):
    run = Recording(tmp_path, "git-diff-trim.txt", "make", "check-api")

    recorded = run.evidence.read_bytes().split(b"\n", 1)[1].rsplit(b"EXIT=0\n", 1)[0]
    assert recorded == run.fixture
    assert run.notes == []


@pytest.mark.parametrize("args", [[], ["evidence.txt"]])
def test_evidence_run_without_a_command_is_a_usage_error_not_an_exit_0(tmp_path, args):
    result = subprocess.run(
        ["bash", str(EVIDENCE_RUN), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
        check=False,
    )

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_an_appended_log_is_summarised_by_its_last_run_alone(tmp_path):
    log = tmp_path / "suite.log"
    log.write_bytes(
        (FIXTURES / "suite-pytest-green.txt").read_bytes()
        + (FIXTURES / "pytest-migration-red.txt").read_bytes()
        + b"EXIT=1\n"
    )
    (tmp_path / "red").mkdir()
    red = _summary(_logged(tmp_path / "red", "pytest-migration-red.txt", 1))

    result = _summary(log)

    assert result.stdout.splitlines() == red.stdout.splitlines()
    assert result.returncode == 1


def test_a_second_evidence_run_into_the_same_file_is_what_the_summary_reads(tmp_path):
    for fixture, status in (("suite-pytest-green.txt", 0), ("pytest-migration-red.txt", 1)):
        Recording(tmp_path, fixture, "pytest", exit_code=status)

    result = _summary(tmp_path / "evidence.txt")

    assert "14 passed" not in result.stdout
    assert result.stdout.splitlines()[-1] == "suite EXIT=1"
    assert result.returncode == 1


def test_a_run_appended_after_an_exit_and_cut_off_is_not_read_as_the_earlier_green(tmp_path):
    log = tmp_path / "suite.log"
    log.write_bytes((FIXTURES / "suite-pytest-green.txt").read_bytes() + b"pytest -q\n.....F\n")

    result = _summary(log)

    assert result.returncode == os.EX_DATAERR
    assert "suite EXIT=" not in result.stdout
    assert "does not end in an EXIT= line" in result.stderr
