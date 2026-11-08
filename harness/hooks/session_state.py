#!/usr/bin/env python3
"""SessionStart: state the tree's actual position before the first claim about it.

Handoff notes and plan files quote branch names, suite counts and "clean tree"
as if they were durable. They are not: a neighbouring session moves the tree
mid-flight. Numbers here are re-measured at session start, not inherited.

`[session_state] memory_budget` in the repo's harness.toml adds a line when the project's
always-loaded MEMORY.md grows past it; `memory_hint` is appended to that line.
`warn_on_default_branch = false` silences the warning for a repo that commits on its default
branch by design.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import repo_config


def memory_index(cwd: str) -> Path | None:
    """The always-loaded index for THIS project. Claude Code keys it by the cwd with
    separators replaced, so the path is derived rather than configured. Which characters
    besides `/` are replaced is undocumented, so both forms are tried; a project directory
    under neither is no answer."""
    override = os.environ.get("CLAUDE_MEMORY_INDEX")
    if override:
        return Path(override)
    projects = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
    for key in (cwd.replace("/", "-"), re.sub(r"[^A-Za-z0-9-]", "-", cwd)):
        if (projects / key).is_dir():
            return projects / key / "memory" / "MEMORY.md"
    return None


def budget_line(index: Path | None, budget: int | None, hint: str = "") -> str | None:
    """MEMORY.md is loaded into every session: a line kept there is rent paid per turn."""
    if not budget or index is None:
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
            ["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def default_branch(cwd: str) -> str:
    remote_head = git(cwd, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote_head:
        return remote_head.removeprefix("origin/")
    for name in ("main", "master"):
        if git(cwd, "rev-parse", "--verify", "-q", f"refs/heads/{name}"):
            return name
    return "main"


def preamble(
    branch: str,
    head: str,
    tracked: int,
    untracked: int,
    divergence: str,
    default: str = "main",
    warn_on_default: bool = True,
) -> list[str]:
    """The lines the session opens with, as a function of what was measured.

    Kept separate from the measuring so it can be witnessed without a git binary.
    """
    lines = [
        "Tree state, measured now (not inherited from any handoff note):",
        f"  branch:    {branch}",
        f"  HEAD:      {head}",
        f"  modified:  {tracked} tracked, {untracked} untracked",
    ]

    if branch == "(detached)":
        lines.append("  WARNING:   HEAD is detached — branch before committing.")
    elif branch == default:
        if warn_on_default:
            lines.append(
                f"  WARNING:   HEAD is on the default branch ({default}) — "
                "branch before committing."
            )
    elif divergence:
        behind, ahead = [*divergence.split(), "?", "?"][:2]
        lines.append(f"  {'vs ' + default + ':':<10} {ahead} ahead, {behind} behind")

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
    default = default_branch(cwd)
    local = git(cwd, "rev-parse", "--verify", "-q", f"refs/heads/{default}")
    base = default if local else f"origin/{default}"
    divergence = (
        ""
        if branch in (default, "(detached)")
        else git(cwd, "rev-list", "--left-right", "--count", f"{base}...{branch}")
    )

    settings = repo_config.section(repo_config.load(cwd), "session_state")
    lines = preamble(
        branch,
        head,
        len(tracked),
        len(untracked),
        divergence,
        default=default,
        warn_on_default=settings.get("warn_on_default_branch", True) is not False,
    )

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
