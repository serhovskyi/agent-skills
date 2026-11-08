"""Catches an absence row that reads green without having looked: a path missing at the
revision, a base that never held the name, a hit deleted only in the working tree, an allow that
matches nothing. The verdict is the exit code of a script run against a git history, which no
linter executes.
"""

import os
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest
from harness_support import BIN, GIT_ENV_OVERRIDES, SUBPROCESS_HANG_BUDGET_SECONDS

GIT_ENV = {**os.environ, **GIT_ENV_OVERRIDES}
IDENTITY = ("-c", "user.name=Absence Check", "-c", "user.email=absence-check@example.invalid")


class Repo(NamedTuple):
    path: Path
    base: str
    rev: str


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *IDENTITY, *args],
        cwd=path,
        env=GIT_ENV,
        capture_output=True,
        text=True,
        check=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
    ).stdout.strip()


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)


def _commit(path: Path, message: str) -> str:
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", message)
    return _git(path, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    _git(tmp_path, "init", "-q", "-b", "main")
    _write(
        tmp_path,
        {
            "app/legacy.py": "import os\nLegacyClient()\n",
            "docs/old notes.md": "LegacyClient\n",
            "app/keep.py": "x = 1\n",
        },
    )
    base = _commit(tmp_path, "base")
    _write(tmp_path, {"app/legacy.py": "import os\n"})
    return Repo(tmp_path, base, _commit(tmp_path, "rev"))


def _check(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BIN / "absence-check"), *args],
        cwd=repo,
        env=GIT_ENV,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
        check=False,
    )


def _flags(repo: Repo, *overrides: str) -> tuple[str, ...]:
    defaults = {"--rev": repo.rev, "--base": repo.base, "--pattern": "LegacyClient"}
    kept = [
        part for flag, value in defaults.items() if flag not in overrides for part in (flag, value)
    ]
    return (*kept, *overrides)


def _tree_id(repo: Repo, path: str) -> str:
    return _git(repo.path, "rev-parse", f"{repo.rev}:{path}")


def test_a_clean_revision_exits_0_and_prints_its_keys(repo):
    run = _check(
        repo.path, "--rev", "main", "--base", "main~1", "--pattern", "LegacyClient", "--", "app"
    )

    assert run.returncode == 0
    lines = run.stdout.splitlines()
    assert lines[:2] == [f"rev {repo.rev}", f"base {repo.base}"]
    assert lines[2] == f"path app {_tree_id(repo, 'app')}"
    assert lines[3] == "base-hits 1"


def test_a_remaining_hit_exits_1_and_is_printed(repo):
    run = _check(repo.path, *_flags(repo), "--", "app", "docs/old notes.md")

    assert run.returncode == 1
    assert "docs/old notes.md:1:LegacyClient" in run.stdout.splitlines()


def test_an_allowed_hit_passes_and_a_stale_allow_is_refused(repo):
    paths = ("--", "app", "docs/old notes.md")

    allowed = _check(repo.path, *_flags(repo, "--allow", "docs/old notes.md:1"), *paths)
    stale = _check(repo.path, *_flags(repo, "--allow", "docs/old notes.md:7"), *paths)

    assert allowed.returncode == 0
    assert stale.returncode == 2
    assert "docs/old notes.md:7" in stale.stderr


def test_an_allow_without_a_line_is_refused(repo):
    run = _check(
        repo.path, *_flags(repo, "--allow", "docs/old notes.md"), "--", "docs/old notes.md"
    )

    assert run.returncode == 2
    assert "docs/old notes.md" in run.stderr


def test_two_allows_are_both_honoured(repo):
    (repo.path / "app/keep.py").write_text("LegacyClient()\n")
    rev2 = _commit(repo.path, "a second hit")
    paths = ("--", "app", "docs/old notes.md")

    one = _check(repo.path, *_flags(repo, "--rev", rev2, "--allow", "docs/old notes.md:1"), *paths)
    both = _check(
        repo.path,
        *_flags(repo, "--rev", rev2, "--allow", "docs/old notes.md:1", "--allow", "app/keep.py:1"),
        *paths,
    )

    assert one.returncode == 1
    assert both.returncode == 0


def test_a_path_missing_at_the_revision_exits_2(repo):
    (repo.path / "app" / "untracked.py").write_text("x = 1\n")

    for path in ("app/legasy.py", "app/untracked.py"):
        run = _check(repo.path, *_flags(repo), "--", path)
        assert run.returncode == 2
        assert path in run.stderr


def test_a_path_deleted_at_the_revision_exits_2(repo):
    (repo.path / "app" / "legacy.py").unlink()
    rev2 = _commit(repo.path, "legacy deleted")

    run = _check(repo.path, *_flags(repo, "--rev", rev2), "--", "app/legacy.py")

    assert run.returncode == 2
    assert "app/legacy.py" in run.stderr


def test_a_base_without_a_hit_exits_3(repo):
    run = _check(repo.path, *_flags(repo, "--pattern", "NeverWritten"), "--", "app")

    assert run.returncode == 3


def test_a_working_tree_deletion_does_not_hide_a_hit_at_the_revision(repo):
    (repo.path / "docs" / "old notes.md").unlink()

    assert _check(repo.path, *_flags(repo), "--", "docs/old notes.md").returncode == 1


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("--rev", "0" * 40), "0" * 40),
        (("--pattern", "a("), "a("),
        (("--rev",), "--rev"),
        (("--rev", "main", "--rev", "main"), "--rev given twice"),
    ],
    ids=["unknown-rev", "invalid-ere", "missing-value", "repeated-flag"],
)
def test_an_invalid_check_exits_2_and_names_its_fault(repo, args, named):
    run = _check(repo.path, *_flags(repo, *args), "--", "app")

    assert run.returncode == 2
    assert named in run.stderr
