"""plan-probe run against a scratch repo whose frontend is not where the probe used to assume:
aliases and packages come from the tree's own tsconfig and package.json files.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from harness_support import GIT_ENV_OVERRIDES, HARNESS, SUBPROCESS_HANG_BUDGET_SECONDS

PLAN_PROBE = HARNESS.parent / "skills" / "wave-prep" / "scripts" / "plan-probe"
TSCONFIG = """{
  // the web client's aliases
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"], },
  },
}
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    files = {
        "web/tsconfig.app.json": TSCONFIG,
        "web/package.json": '{"dependencies": {"flatpickr": "^4.6.0"}}\n',
        "web/src/util/format.ts": "".join(f"export const line{n} = {n}\n" for n in range(1, 21)),
    }
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    env = {**os.environ, **GIT_ENV_OVERRIDES}
    for args in (("init", "-q", "-b", "main"), ("add", "-A")):
        subprocess.run(["git", *args], cwd=tmp_path, env=env, check=True, capture_output=True)
    return tmp_path


def _probe(cwd: Path, plan: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PLAN_PROBE), os.path.relpath(plan, cwd)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
    )


def _plan(repo: Path, text: str) -> Path:
    plan = repo / "plan.md"
    plan.write_text(text, encoding="utf-8")
    return plan


def test_an_aliased_citation_resolves_through_the_tsconfig_paths(repo):
    plan = _plan(repo, "The helper at `@/util/format.ts:12` stays.\n")

    result = _probe(repo, plan)

    assert result.returncode == 0, result.stdout
    assert "citations resolved: 1/1" in result.stdout
    assert "web/src/util/format.ts:12  export const line12 = 12" in result.stdout


def test_a_run_from_a_subdirectory_reads_the_whole_tree(repo):
    plan = _plan(repo, "- Modify: `web/src/util/format.ts`\nSee `web/src/util/format.ts:3`.\n")

    result = _probe(repo / "web", plan)

    assert result.returncode == 0, result.stdout
    assert "citations resolved: 1/1" in result.stdout


def test_a_package_of_any_tracked_package_json_is_not_a_dead_path(repo):
    plan = _plan(repo, "Import `flatpickr/dist/flatpickr.min.css` once.\n")

    result = _probe(repo, plan)

    assert result.returncode == 0, result.stdout
    assert "flatpickr" not in result.stdout.split("Evidence, not a verdict")[0]
