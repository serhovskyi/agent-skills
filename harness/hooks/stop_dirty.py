#!/usr/bin/env python3
"""Stop: name what is still uncommitted, with counts, when a turn ends."""

import json
import os
import subprocess
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    cwd = payload.get("cwd") or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        sys.exit(0)
    if result.returncode != 0:
        sys.exit(0)

    entries = [line for line in result.stdout.splitlines() if line]
    if not entries:
        sys.exit(0)

    staged = [e for e in entries if e[:1] not in (" ", "?")]
    untracked = [e for e in entries if e.startswith("??")]
    unstaged = len(entries) - len(staged) - len(untracked)

    # Unstaged edits mid-task are the normal state and saying so every turn is noise.
    # A live index can be swallowed by a neighbouring commit; untracked paths are
    # invisible to `git grep`. Those two are worth interrupting for.
    if not staged and not untracked:
        sys.exit(0)

    json.dump(
        {
            "systemMessage": (
                f"Uncommitted: {len(staged)} staged, {unstaged} unstaged, "
                f"{len(untracked)} untracked."
            )
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
