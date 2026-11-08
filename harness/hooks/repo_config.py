"""The repo's half of the harness: `.claude/harness.toml`, found from the session's cwd.

A missing or unreadable file is an empty config, never an error: a hook that crashes on a
repo without one blanks every rule it carries in every other repo too.
"""

import os
import subprocess
import tomllib
from pathlib import Path

CONFIG = Path(".claude") / "harness.toml"


def repo_root(cwd: str | None = None) -> Path | None:
    start = cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def load_checked(cwd: str | None = None) -> tuple[dict, str | None]:
    """The config, and why it is empty when a file exists but cannot be used."""
    override = os.environ.get("WAVE_HARNESS_CONFIG")
    path = Path(override) if override else None
    if path is None:
        root = repo_root(cwd)
        if root is None:
            return {}, None
        path = root / CONFIG
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, None
    except OSError as exc:
        return {}, f"unreadable: {exc.strerror}"
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return {}, f"invalid TOML: {exc}"
    return (data, None) if isinstance(data, dict) else ({}, "not a table")


def load(cwd: str | None = None) -> dict:
    return load_checked(cwd)[0]


def section(config: dict, name: str) -> dict:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}
