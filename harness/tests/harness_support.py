import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
HOOKS = HARNESS / "hooks"
BIN = HARNESS / "bin"

# A ceiling for a child that never exits, not a speed expectation.
SUBPROCESS_HANG_BUDGET_SECONDS = 300

GIT_ENV_OVERRIDES = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

MEMORY_BUDGET = 6144
MEMORY_HINT = "Retired lines are listed in memory-retired."

CONFIG = f"""\
[harness]
owner = "the maintainer"

[guard_bash]
host_markers = ["docker compose exec", "docker exec", "make "]

[guard_bash.host_only]
pytest = "make test-api"
ruff = "make lint-api"
vitest = "make test-web"
eslint = "make lint-web"

[guard_bash.host_only_npm]
test = "make test-web"
lint = "make lint-web"

[[guard_bash.warn_make]]
id = "make-ci-is-local"
targets = ["ci", "verify"]
reason = "`make {{target}}` runs only here; CI runs .github/workflows/ci.yml. Green here is not green there."

[[guard_bash.warn_program]]
id = "npx-prettier"
programs = ["prettier"]
reason = "prettier is not this repo's formatter; npx installs a fresh one. Use `make lint-fix-web`."

[session_state]
memory_budget = {MEMORY_BUDGET}
memory_hint = "{MEMORY_HINT}"

[warn_pipefail]
runners = ["make check-api", "./manage.py test"]

[evidence]
runners = ["check-api"]
"""


def run_hook(hook: Path, payload: dict, env: dict | None = None) -> dict:
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
        env={**os.environ, **env} if env else None,
    )
    assert result.returncode == 0, f"{hook.name} exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout) if result.stdout.strip() else {}


def load_hook(hook: Path):
    """Import a hook by path, for the decisions that cannot be reached through stdin."""
    if str(hook.parent) not in sys.path:
        sys.path.insert(0, str(hook.parent))
    spec = importlib.util.spec_from_file_location(f"hook_{hook.stem}", hook)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=path,
        env={**os.environ, **GIT_ENV_OVERRIDES},
        check=True,
        capture_output=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
    )
    return path
