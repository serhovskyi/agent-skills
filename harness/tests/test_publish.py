"""The two scripts that touch state outside the clone, run against scratch copies of it.

publish.sh against a bare remote: what it refuses never reaches the remote, and a refusal
leaves the index as it found it. link-harness.sh against a scratch CLAUDE_CONFIG_DIR: the
user settings it rewrites are what every session in every repo reads its hooks from.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from harness_support import GIT_ENV_OVERRIDES, HARNESS, SUBPROCESS_HANG_BUDGET_SECONDS, git_init

PUBLISH = HARNESS.parent / "scripts" / "publish.sh"
LINK_HARNESS = HARNESS.parent / "scripts" / "link-harness.sh"
SECRET = "Quillfeather"
PUBLISHED = ("skills", "agents", "harness", "scripts", ".claude-plugin", ".github")


def _env(home: Path, **extra: str) -> dict[str, str]:
    env = {
        **os.environ,
        **GIT_ENV_OVERRIDES,
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "Publish Test",
        "GIT_AUTHOR_EMAIL": "publish@example.invalid",
        "GIT_COMMITTER_NAME": "Publish Test",
        "GIT_COMMITTER_EMAIL": "publish@example.invalid",
    }
    env.pop("PUBLISH_WITHOUT_DENYLIST", None)
    env.pop("GIT_INDEX_FILE", None)
    return {**env, **extra}


class Clone:
    def __init__(self, tmp_path: Path) -> None:
        self.home = tmp_path
        self.remote = tmp_path / "remote.git"
        self.path = tmp_path / "clone"
        self.path.mkdir()
        self.git("init", "-q", "--bare", "-b", "main", str(self.remote), cwd=tmp_path)
        self.git("init", "-q", "-b", "main")
        for directory in PUBLISHED:
            self.write(f"{directory}/.keep", "")
        self.write("README.md", "readme\n")
        self.write("LICENSE", "license\n")
        self.write(".gitignore", "*.log\n")
        self.write("Makefile", "test:\n\ttrue\n")
        self.write("ruff.toml", "line-length = 100\n")
        self.write("package.json", "{}\n")
        (self.path / "scripts" / "publish.sh").write_bytes(PUBLISH.read_bytes())
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-q", "-u", "origin", "main")
        self.denylist = self.path / ".git" / "info" / "publish-denylist"
        self.denylist.parent.mkdir(exist_ok=True)
        self.denylist.write_text(f"# private words\n{SECRET.lower()}\n\n", encoding="utf-8")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.path,
            env=_env(self.home),
            capture_output=True,
            text=True,
            check=True,
            timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
        ).stdout

    def write(self, name: str, text: str | bytes) -> None:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            target.write_bytes(text)
        else:
            target.write_text(text, encoding="utf-8")

    def publish(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.path / "scripts" / "publish.sh"), *args],
            cwd=self.path,
            env=_env(self.home, **env),
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
            check=False,
        )

    def edit_tracked(self) -> None:
        with (self.path / "README.md").open("a", encoding="utf-8") as readme:
            readme.write("more\n")

    def remote_head(self) -> str:
        return self.git("rev-parse", "main", cwd=self.remote).strip()

    def staged(self) -> list[str]:
        return self.git("diff", "--cached", "--name-only").splitlines()


@pytest.fixture
def clone(tmp_path: Path) -> Clone:
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    return Clone(tmp_path)


def _refused(clone: Clone, result: subprocess.CompletedProcess[str], before: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Refused" in result.stderr, result.stderr
    assert clone.remote_head() == before


def test_a_word_at_the_head_of_a_large_diff_is_refused(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    filler = "".join(f"line {n} of generic text\n" for n in range(12000))
    clone.write("skills/big/SKILL.md", f"made for {SECRET}\n{filler}")

    result = clone.publish("add big")

    _refused(clone, result, before)
    assert f"  {SECRET.lower()}" in result.stderr.splitlines()


def test_a_word_in_a_new_file_name_is_refused(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.write(f"skills/{SECRET}-notes/SKILL.md", "generic text\n")

    result = clone.publish("add notes")

    _refused(clone, result, before)
    assert "file names" in result.stderr


def test_a_word_inside_a_binary_is_refused_and_every_binary_is_named(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.write("skills/art/logo.png", b"\x00\x01" + SECRET.encode() + b"\x00")

    result = clone.publish("add art")

    _refused(clone, result, before)
    assert "skills/art/logo.png (binary)" in result.stderr


def test_a_clean_binary_is_published_with_a_warning(clone):
    clone.write("skills/art/logo.png", b"\x00\x01generic\x00")

    result = clone.publish("add art")

    assert result.returncode == 0, result.stderr
    assert "adds a binary file" in result.stderr and "skills/art/logo.png" in result.stderr


def test_a_word_in_the_commit_message_is_refused(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.write("skills/x/SKILL.md", "generic text\n")

    result = clone.publish(f"port the {SECRET} lesson")

    _refused(clone, result, before)
    assert "the commit message" in result.stderr


def test_an_unpushed_commit_carrying_a_word_is_refused_and_named(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.write("skills/early/SKILL.md", f"from {SECRET}\n")
    clone.git("add", "-A")
    clone.git("commit", "-q", "-m", "early draft")
    early = clone.git("rev-parse", "--short", "HEAD").strip()
    clone.write("skills/later/SKILL.md", "generic text\n")

    result = clone.publish("later")

    _refused(clone, result, before)
    assert f"unpushed commit {early} (early draft), added lines" in result.stderr
    assert clone.git("rev-parse", "--short", "HEAD").strip() == early


def test_an_unpushed_commit_message_carrying_a_word_is_refused(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.write("skills/early/SKILL.md", "generic text\n")
    clone.git("add", "-A")
    clone.git("commit", "-q", "-m", f"seen in {SECRET}")
    clone.write("skills/later/SKILL.md", "generic text\n")

    result = clone.publish("later")

    _refused(clone, result, before)
    assert "message" in result.stderr and "unpushed commit" in result.stderr


def test_a_missing_denylist_is_a_refusal_that_says_how_to_acknowledge_it(clone):
    before = clone.remote_head()
    clone.edit_tracked()
    clone.denylist.unlink()
    clone.write("skills/x/SKILL.md", "generic text\n")

    result = clone.publish("x")

    _refused(clone, result, before)
    assert "touch .git/info/publish-denylist" in result.stderr


def test_an_empty_denylist_acknowledges_there_is_nothing_to_keep_out(clone):
    clone.denylist.write_text("", encoding="utf-8")
    clone.write("skills/x/SKILL.md", f"{SECRET} is fine here\n")

    result = clone.publish("x")

    assert result.returncode == 0, result.stderr
    assert clone.remote_head() == clone.git("rev-parse", "HEAD").strip()


def test_the_override_publishes_without_a_denylist(clone):
    clone.denylist.unlink()
    clone.write("skills/x/SKILL.md", "generic text\n")

    result = clone.publish("x", PUBLISH_WITHOUT_DENYLIST="1")

    assert result.returncode == 0, result.stderr
    assert clone.remote_head() == clone.git("rev-parse", "HEAD").strip()


def test_an_untracked_new_skill_is_something_to_publish(clone):
    clone.write("skills/fresh/SKILL.md", "generic text\n")

    result = clone.publish("add fresh")

    assert result.returncode == 0, result.stderr
    assert "Nothing to publish" not in result.stdout
    assert "skills/fresh/SKILL.md" in clone.git("ls-tree", "-r", "--name-only", "origin/main")


def test_a_refusal_leaves_the_index_as_it_was_before_the_run(clone):
    clone.edit_tracked()
    clone.write("skills/kept/SKILL.md", "generic text\n")
    clone.git("add", "skills/kept/SKILL.md")
    clone.write("skills/leak/SKILL.md", f"{SECRET}\n")

    result = clone.publish("x")

    assert result.returncode == 1, result.stderr
    assert clone.staged() == ["skills/kept/SKILL.md"]
    assert "the index is as it was" in result.stderr


class LinkedClone:
    def __init__(self, tmp_path: Path) -> None:
        self.path = tmp_path / "clone"
        (self.path / "scripts").mkdir(parents=True)
        shutil.copytree(HARNESS, self.path / "harness", ignore=shutil.ignore_patterns("tests"))
        shutil.copy2(LINK_HARNESS, self.path / "scripts" / "link-harness.sh")
        self.config = tmp_path / "config"
        self.settings = self.config / "settings.json"
        self.bin = tmp_path / "bin"
        self.env = {
            **os.environ,
            "HOME": str(tmp_path),
            "CLAUDE_CONFIG_DIR": str(self.config),
            "WAVE_HARNESS_BIN": str(self.bin),
        }

    def link(self, *args: str, via: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str((via or self.path) / "scripts" / "link-harness.sh"), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
            check=False,
        )

    def commands(self, event: str | None = None) -> list[str]:
        hooks = json.loads(self.settings.read_text(encoding="utf-8")).get("hooks", {})
        return [
            hook["command"]
            for name, entries in hooks.items()
            if event in (None, name)
            for entry in entries
            for hook in entry["hooks"]
        ]

    def run_registered(self, event: str, payload: dict) -> subprocess.CompletedProcess[str]:
        [command] = [c for c in self.commands(event) if "/harness/hooks/" in c]
        return subprocess.run(
            ["bash", "-c", command],
            input=json.dumps(payload),
            env=self.env,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_HANG_BUDGET_SECONDS,
            check=False,
        )


@pytest.fixture
def linked(tmp_path: Path) -> LinkedClone:
    return LinkedClone(tmp_path)


def test_a_hook_file_gone_with_a_moved_clone_switches_its_guard_off_loudly(linked, tmp_path):
    assert linked.link().returncode == 0
    (linked.path / "harness" / "hooks" / "guard_bash.py").unlink()

    payload = {"tool_input": {"command": "ls"}, "cwd": str(tmp_path)}
    result = linked.run_registered("PreToolUse", payload)

    assert result.returncode == 0, result.stderr
    message = json.loads(result.stdout)["systemMessage"]
    assert "guard_bash.py is missing" in message and "--unlink" in message


def test_a_present_hook_file_still_answers_through_the_registration(linked, tmp_path):
    repo = git_init(tmp_path / "repo")
    assert linked.link().returncode == 0

    result = linked.run_registered("SessionStart", {"cwd": str(repo)})

    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "branch:" in context


def test_relinking_through_a_symlinked_path_registers_each_hook_once(linked, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(linked.path)

    assert linked.link().returncode == 0
    assert linked.link(via=alias).returncode == 0

    assert len(linked.commands()) == 4
    assert all(str(alias) not in command for command in linked.commands())


def test_unlinking_through_a_symlinked_path_removes_the_hooks_and_the_tools(linked, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(linked.path)
    assert linked.link().returncode == 0

    assert linked.link("--unlink", via=alias).returncode == 0

    assert linked.commands() == []
    assert list(linked.bin.iterdir()) == []


def test_a_registration_from_an_older_clone_path_is_replaced_and_a_foreign_hook_kept(linked):
    linked.config.mkdir()
    stale = 'python3 "/somewhere/old/harness/hooks/guard_bash.py"'
    foreign = {"type": "command", "command": "echo mine"}
    entry = {"matcher": "Bash", "hooks": [{"type": "command", "command": stale}, foreign]}
    linked.settings.write_text(json.dumps({"hooks": {"PreToolUse": [entry]}}), encoding="utf-8")

    assert linked.link().returncode == 0

    commands = linked.commands("PreToolUse")
    assert stale not in commands
    assert "echo mine" in commands and len(commands) == 2


def test_a_mistyped_mode_is_refused_and_touches_nothing(linked):
    result = linked.link("--unlnk")

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert not linked.config.exists() and not linked.bin.exists()


def test_the_first_backup_survives_every_later_run(linked):
    linked.config.mkdir()
    original = '{"theme": "dark"}\n'
    linked.settings.write_text(original, encoding="utf-8")

    assert linked.link().returncode == 0
    assert linked.link().returncode == 0

    assert (linked.config / "settings.json.orig").read_text(encoding="utf-8") == original
    assert len(list(linked.config.glob("settings.json.*.bak"))) == 2


def test_a_symlinked_settings_file_is_written_through_not_replaced(linked, tmp_path):
    linked.config.mkdir()
    dotfile = tmp_path / "dotfiles" / "settings.json"
    dotfile.parent.mkdir()
    dotfile.write_text("{}\n", encoding="utf-8")
    linked.settings.symlink_to(dotfile)

    assert linked.link().returncode == 0

    assert linked.settings.is_symlink()
    assert len(linked.commands()) == 4
