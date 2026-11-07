#!/usr/bin/env python3
"""Usage: evidence_filter.py <raw-log> <offset> <command...>"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import repo_config

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
LINE = re.compile(r"[^\n]*\n|[^\n]+$")


class Command:
    VERBATIM_PROGRAMS = frozenset(
        {"git", "cmp", "diff", "grep", "cat", "sed", "head", "tail", "wc", "ls"}
    )
    RUNNERS = frozenset(
        {
            "pytest",
            "py.test",
            "vitest",
            "alembic",
            "jest",
            "playwright",
        }
        | set(repo_config.section(repo_config.load(), "evidence").get("runners", ()))
    )

    def __init__(self, argv: list[str]) -> None:
        self._argv = argv

    def is_runner(self) -> bool:
        if not self._argv or Path(self._argv[0]).name in self.VERBATIM_PROGRAMS:
            return False
        words = (word for arg in self._argv for word in arg.split())
        return any(Path(word).name in self.RUNNERS for word in words)


class AlembicPreamble:
    LINE = re.compile(r"^INFO  \[alembic\.runtime\.migration\] (?:Context impl |Will assume )")

    def kept(self, lines: list[str]) -> list[str]:
        return [line for line in lines if not self.LINE.match(line)]


class VitestDumps:
    HEADER = re.compile(r"^stderr \| ")
    REPORTER = re.compile(r"^\s*(?:[✓×❯↓] |FAIL |PASS |Test Files |Tests )|^⎯")  # noqa: RUF001 - vitest's own reporter glyphs

    def kept(self, lines: list[str]) -> list[str]:
        kept: list[str] = []
        in_dump = False
        for index, line in enumerate(lines):
            if self.HEADER.match(line):
                in_dump = True
            elif not in_dump or self.REPORTER.match(line):
                in_dump = False
                kept.append(line)
            elif not line.strip() and self._reporter_resumes_after(lines, index):
                in_dump = False
        return kept

    def _reporter_resumes_after(self, lines: list[str], index: int) -> bool:
        following = next((line for line in lines[index + 1 :] if line.strip()), None)
        if following is None or following[0].isspace():
            return True
        return bool(self.HEADER.match(following) or self.REPORTER.match(following))


class PytestTracebacks:
    SECTION = re.compile(r"^=+ (?P<name>.+?) =+\s*$")
    TEST_HEADER = re.compile(r"^_+ (?=.*[^_ ]).+ _+\s*$")
    SUBSECTION = re.compile(r"^-{3,} (?P<name>.+?) -{3,}\s*$")
    LOCATION = re.compile(r"^(?P<path>[^\s:]+):\d+:(?: (?P<rest>.*))?$")
    ASSERTION = re.compile(r"^E(?: |$)")
    CHAINED = re.compile(r"^(?:The above exception|During handling of the above exception)")
    TRACEBACK_SECTIONS = frozenset({"FAILURES", "ERRORS"})

    def kept(self, lines: list[str]) -> list[str]:
        kept: list[str] = []
        section = ""
        captured = False
        pending: list[tuple[bool, str]] = []
        source_follows = False
        for line in lines:
            text = line.rstrip("\r\n")
            heading = self.SECTION.match(text)
            subsection = self.SUBSECTION.match(text)
            test_header = self.TEST_HEADER.match(text)
            if heading or subsection or test_header:
                kept.extend(self._settled(pending, in_project_frame=False))
                pending = []
            if heading:
                section, captured = heading["name"], False
                kept.append(line)
            elif subsection:
                captured = subsection["name"].startswith("Captured ")
                if not captured:
                    kept.append(line)
            elif test_header:
                captured = False
                kept.append(line)
            elif captured:
                pass
            elif section not in self.TRACEBACK_SECTIONS:
                kept.append(line)
            elif self.ASSERTION.match(text) or self.CHAINED.match(text):
                pending.append((False, line))
            elif text.startswith(">"):
                pending.append((True, line))
            elif location := self.LOCATION.match(text):
                in_project_frame = self._is_project(location["path"])
                kept.extend(self._settled(pending, in_project_frame))
                pending = []
                if in_project_frame:
                    kept.append(line)
                    source_follows = (location["rest"] or "").startswith("in ")
                    continue
            elif source_follows and text.startswith("    "):
                kept.append(line)
            source_follows = False
        kept.extend(self._settled(pending, in_project_frame=False))
        return kept

    @staticmethod
    def _settled(pending: list[tuple[bool, str]], in_project_frame: bool) -> list[str]:
        return [line for is_mark, line in pending if in_project_frame or not is_mark]

    @staticmethod
    def _is_project(path: str) -> bool:
        return not path.startswith(("/", "<")) and "site-packages" not in path


class RunnerOutput:
    PASSES = (AlembicPreamble(), VitestDumps(), PytestTracebacks())

    def __init__(self, text: str) -> None:
        self._lines = LINE.findall(ANSI_ESCAPE.sub("", text))

    def total(self) -> int:
        return len(self._lines)

    def kept(self) -> list[str]:
        lines = self._lines
        for noise in self.PASSES:
            lines = noise.kept(lines)
        return lines


class EvidenceBlock:
    def __init__(self, raw_log: Path, offset: int, argv: list[str]) -> None:
        with raw_log.open("rb") as stream:
            stream.seek(offset)
            self._output = stream.read()
        self._raw_log = raw_log
        self._command = Command(argv)

    def rendered(self) -> bytes:
        if not self._command.is_runner():
            return self._output
        output = RunnerOutput(self._output.decode("utf-8", errors="surrogateescape"))
        kept = output.kept()
        body = "".join(kept)
        if body and not body.endswith("\n"):
            body += "\n"
        dropped = output.total() - len(kept)
        note = (
            f"[evidence-run] dropped {dropped} of {output.total()} output lines as runner noise;"
            f" full output: {self._raw_log.name}\n"
        )
        return (body + note).encode("utf-8", errors="surrogateescape")


if __name__ == "__main__":
    raw_log, offset, *argv = sys.argv[1:]
    sys.stdout.buffer.write(EvidenceBlock(Path(raw_log), int(offset), argv).rendered())
