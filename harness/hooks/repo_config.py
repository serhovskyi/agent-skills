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
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def load(cwd: str | None = None) -> dict:
    override = os.environ.get("WAVE_HARNESS_CONFIG")
    path = Path(override) if override else None
    if path is None:
        root = repo_root(cwd)
        if root is None:
            return {}
        path = root / CONFIG
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def section(config: dict, name: str) -> dict:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}
