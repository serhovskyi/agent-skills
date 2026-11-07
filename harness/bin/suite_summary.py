#!/usr/bin/env python3
"""Usage: suite_summary.py <log>"""

import os
import re
import sys
from pathlib import Path

from evidence_filter import ANSI_ESCAPE


class SummaryLine:
    PATTERNS = (
        re.compile(r"^\s*(?:Test Files|Tests|Errors)\s+\d"),
        re.compile(r"^\s*(?:FAIL|\u00d7)\s"),
        re.compile(r"^=+ \S.* in \d+(?:\.\d+)?s(?: \(\d+:\d\d:\d\d\))? =+$"),
        re.compile(r"^(?:FAILED|ERROR) \S"),
    )

    @classmethod
    def of(cls, raw: str) -> str | None:
        line = ANSI_ESCAPE.sub("", raw).rstrip()
        return line if any(pattern.match(line) for pattern in cls.PATTERNS) else None


class SuiteLog:
    EXIT = re.compile(r"^EXIT=(?P<status>\d+)$")

    def __init__(self, path: Path) -> None:
        self.path = path
        self.summary: list[str] = []
        last = ""
        with path.open(encoding="utf-8", errors="surrogateescape") as stream:
            for raw in stream:
                if raw.strip():
                    last = raw.strip()
                if (line := SummaryLine.of(raw)) is not None:
                    self.summary.append(line)
        exit_line = self.EXIT.match(last)
        self.status = int(exit_line["status"]) if exit_line else None


class SuiteSummary:
    def __init__(self, log: SuiteLog) -> None:
        self._log = log

    def problems(self) -> list[str]:
        problems = []
        if self._log.status is None:
            problems.append(
                f"{self._log.path} does not end in an EXIT= line: truncated, or not a suite log"
            )
        if not self._log.summary:
            problems.append(f"{self._log.path} has no summary line: truncated, or not a suite log")
        return problems

    def lines(self) -> list[str]:
        if self._log.status is None:
            return self._log.summary
        return [*self._log.summary, f"suite EXIT={self._log.status}"]

    def exit_status(self) -> int:
        if self.problems():
            return os.EX_DATAERR
        return self._log.status


if __name__ == "__main__":
    [log_path] = sys.argv[1:]
    try:
        summary = SuiteSummary(SuiteLog(Path(log_path)))
    except OSError as error:
        print(f"[suite-summary] {error}", file=sys.stderr)
        sys.exit(os.EX_NOINPUT)
    for line in summary.lines():
        print(line)
    sys.stdout.flush()
    for problem in summary.problems():
        print(f"[suite-summary] {problem}", file=sys.stderr)
    sys.exit(summary.exit_status())
