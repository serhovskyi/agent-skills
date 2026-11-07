#!/usr/bin/env python3
"""SessionStart: state the tree's actual position before the first claim about it.

Handoff notes and plan files quote branch names, suite counts and "clean tree"
as if they were durable. They are not: a neighbouring session moves the tree
mid-flight. Numbers here are re-measured at session start, not inherited.

`[session_state] memory_budget` in the repo's harness.toml adds a line when the project's
always-loaded MEMORY.md grows past it; `memory_hint` is appended to that line.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import repo_config


def memory_index(cwd: str) -> Path:
    """The always-loaded index for THIS project. Claude Code keys it by the cwd with
    separators replaced, so the path is derived rather than configured."""
    override = os.environ.get("CLAUDE_MEMORY_INDEX")
    if override:
        return Path(override)
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return config / "projects" / cwd.replace("/", "-") / "memory" / "MEMORY.md"


def budget_line(index: Path, budget: int | None, hint: str = "") -> str | None:
    """MEMORY.md is loaded into every session: a line kept there is rent paid per turn."""
    if not budget:
        return None
    try:
        size = index.stat().st_size
    except OSError:
        return None
    if size <= budget:
        return None
    line = (
        f"  MEMORY:    MEMORY.md is {size} B, over the {budget} B budget by "
        f"{size - budget}. Retire a line before adding one."
    )
    return f"{line} {hint}" if hint else line


def git(cwd: str, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def preamble(branch: str, head: str, tracked: int, untracked: int, divergence: str) -> list[str]:
    """The lines the session opens with, as a function of what was measured.

    Kept separate from the measuring so it can be witnessed without a git binary.
    """
    lines = [
        "Tree state, measured now (not inherited from any handoff note):",
        f"  branch:    {branch}",
        f"  HEAD:      {head}",
        f"  modified:  {tracked} tracked, {untracked} untracked",
    ]

    if branch not in ("main", "master", "(detached)"):
        if divergence:
            behind, ahead = [*divergence.split(), "?", "?"][:2]
            lines.append(f"  vs main:   {ahead} ahead, {behind} behind")
    else:
        lines.append("  WARNING:   HEAD is on the default branch — branch before committing.")

    # Warning only where untracked paths already exist means staying silent at exactly
    # the moment the blindness starts: before this session has written its first file.
    if untracked:
        lines.append(
            f"  NOTE:      `git grep` is blind to the {untracked} untracked path(s); "
            "use `git grep --untracked`, `find` or `rg` when counting files."
        )
    else:
        lines.append(
            "  NOTE:      no untracked paths yet — but `git grep` will not see the ones this "
            "session writes. Count with `git grep --untracked`, `find` or `rg`."
        )

    return lines


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    cwd = payload.get("cwd") or os.getcwd()
    if not git(cwd, "rev-parse", "--is-inside-work-tree"):
        sys.exit(0)

    branch = git(cwd, "branch", "--show-current") or "(detached)"
    head = git(cwd, "log", "-1", "--format=%h %s")
    porcelain = [line for line in git(cwd, "status", "--porcelain").splitlines() if line]
    untracked = [line for line in porcelain if line.startswith("??")]
    tracked = [line for line in porcelain if not line.startswith("??")]
    divergence = (
        ""
        if branch in ("main", "master", "(detached)")
        else git(cwd, "rev-list", "--left-right", "--count", f"main...{branch}")
    )

    lines = preamble(branch, head, len(tracked), len(untracked), divergence)

    settings = repo_config.section(repo_config.load(cwd), "session_state")
    over_budget = budget_line(
        memory_index(cwd), settings.get("memory_budget"), settings.get("memory_hint", "")
    )
    if over_budget:
        lines.append(over_budget)

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(lines),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
