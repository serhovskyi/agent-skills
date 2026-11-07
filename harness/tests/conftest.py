from pathlib import Path

import pytest
from harness_support import CONFIG, git_init

SESSION_VARIABLES = (
    "WAVE_HARNESS_CONFIG",
    "CLAUDE_PROJECT_DIR",
    "CLAUDE_MEMORY_INDEX",
    "CLAUDE_CONFIG_DIR",
)


@pytest.fixture(autouse=True)
def outside_any_session(monkeypatch, tmp_path):
    """A Claude Code session exports CLAUDE_PROJECT_DIR, and the hooks would read that
    repo's harness.toml instead of the one a case names."""
    for name in SESSION_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def configured(monkeypatch, tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("config") / "harness.toml"
    path.write_text(CONFIG, encoding="utf-8")
    monkeypatch.setenv("WAVE_HARNESS_CONFIG", str(path))
    return path


@pytest.fixture
def unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("WAVE_HARNESS_CONFIG", raising=False)


@pytest.fixture
def repo_without_config(tmp_path_factory) -> Path:
    return git_init(tmp_path_factory.mktemp("repo") / "repo")
