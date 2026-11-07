#!/usr/bin/env python3
"""PostToolUse/Bash: a test run piped into a pager reports the pager's exit code.

`pytest ... | tail -5` exits 0 on a red suite. This has already been read as a
pass, so the reminder fires on the command that caused it, not in review.
`[warn_pipefail] runners` in the repo's harness.toml adds the repo's own runner commands.
"""

import json
import re
import sys

import repo_config

RUNNERS = (
    "pytest",
    "vitest",
    "jest",
    "playwright",
    "npm run test",
    "npm test",
    "make test",
    "make ci",
    "go test",
    "cargo test",
    "mypy",
    "ruff",
)
PAGERS = re.compile(r"\|\s*(tail|head|less|more|grep|sed|awk|cut|sort|uniq|wc)\b")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    extra = repo_config.section(repo_config.load(payload.get("cwd")), "warn_pipefail")
    names = (*RUNNERS, *extra.get("runners", ()))
    runners = re.compile(r"(?<!\w)(" + "|".join(re.escape(name) for name in names) + r")(?!\w)")
    if not (runners.search(command) and PAGERS.search(command)):
        sys.exit(0)
    if "pipefail" in command or "PIPESTATUS" in command:
        sys.exit(0)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    "The exit code just reported belongs to the last command in the pipe, not to "
                    "the test runner — a failing suite exits 0 through `| tail`. Do not call this "
                    "run green on that basis; re-run with `set -o pipefail;` prefixed, or read the "
                    "runner's own pass/fail summary line."
                ),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
