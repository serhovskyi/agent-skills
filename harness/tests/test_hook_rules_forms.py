"""The forms a command takes on its way to the same program: lines, comments, heredoc
openers, grouping, wrappers, inner shells, launchers. Each once reached what a rule
refuses with that rule silent, because the rule read argv[0] of the typed command.
"""

import io
import json
from contextlib import redirect_stdout

import pytest
from harness_support import CONFIG, HOOKS, load_hook, run_hook

GUARD_BASH = HOOKS / "guard_bash.py"


def bash(command: str) -> dict:
    return run_hook(GUARD_BASH, {"tool_input": {"command": command}})


def verdict(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("permissionDecision", "")


def warned(output: dict) -> bool:
    return bool(output.get("systemMessage")) and not verdict(output)


@pytest.mark.parametrize(
    "command",
    [
        "git status\ngit push",
        "cd repo\ngit reset --hard",
        "echo a#b; git push",
        "curl http://x/#frag; git push",
        "git commit -F - <<EOF && git reset --hard\nmsg\nEOF",
        "(git push)",
        "x=$(git push)",
        "{ git push; }",
        "for f in a b; do git restore $f; done",
        "if true; then git reset --hard; fi",
        "time git push",
        "timeout 60 git push",
        "env X=1 git push",
        "sudo -u deploy git push",
        "nohup git push &",
        'bash -c "git push"',
        'bash -lc "cd x && git stash"',
        'sh -c "git reset --hard"',
        'eval "git push"',
        "xargs -n 1 git push",
    ],
)
def test_a_refused_git_command_is_refused_in_every_form(configured, command):
    """rules: git-push, git-reset-hard, git-restore, git-stash-shared-stack.

    The first line, the comment-free part, the heredoc opener, a subshell, a loop body,
    a wrapper's argument and an inner shell's -c string are all the same command.
    """
    assert verdict(bash(command)) == "deny", command


@pytest.mark.parametrize(
    "command",
    [
        "git status # git push",
        "cat <<EOF\ngit push\nEOF",
        "cat <<-EOF\n\tgit push\n\tEOF",
        'git commit -m "a#b" -- f',
        'echo "git push"',
        "python3 - <<'EOF'\nprint(1)\nEOF",
    ],
)
def test_a_harmless_command_that_spells_a_refused_one_stays_allowed(configured, command):
    """rules: git-push. A comment, a heredoc body and a quoted word are data."""
    assert verdict(bash(command)) == "", command


@pytest.mark.parametrize(
    "command",
    [
        "make up && pytest api/tests",
        "python -m pytest api/tests",
        "uv run pytest -q",
        "uv run --with foo pytest -q",
        "poetry run ruff check .",
    ],
)
def test_a_host_only_runner_is_refused_behind_a_launcher_or_beside_a_marker(configured, command):
    """rule: host-only-runner. A container marker in another segment, and a launcher in
    front of the program, each ran the runner on the host once."""
    assert verdict(bash(command)) == "deny", command


def test_a_launcher_whose_program_is_not_host_only_is_allowed(configured):
    """rule: host-only-runner."""
    assert verdict(bash("uv run --with pytest python -m pytest harness/tests")) == ""


@pytest.mark.parametrize(
    "command",
    ["git restore --staged --worktree f", "git restore -SW f"],
)
def test_restore_that_touches_the_worktree_is_refused_whatever_else_it_names(command):
    """rule: git-restore. `--staged` alone is read-only for the worktree; with
    `--worktree` it is not."""
    assert verdict(bash(command)) == "deny", command


def test_restore_staged_in_its_short_form_is_allowed():
    """rule: git-restore."""
    assert verdict(bash("git restore -S f")) == ""


@pytest.mark.parametrize(
    "command, rule",
    [
        ("git checkout -f main", "git-checkout-force"),
        ("git switch --discard-changes main", "git-switch-discard"),
        ("git switch -f main", "git-switch-discard"),
    ],
)
def test_a_forced_branch_change_is_refused(command, rule):
    """rules: git-checkout-force, git-switch-discard."""
    out = bash(command)
    assert verdict(out) == "deny", out
    assert "throws away local changes" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_an_ordinary_switch_is_allowed():
    """rules: git-checkout-force, git-switch-discard."""
    assert verdict(bash("git switch main")) == ""


@pytest.mark.parametrize(
    "command",
    [
        'bash scripts/publish.sh "wave-run: tighten the ledger"',
        "./scripts/publish.sh msg",
        "~/waveflow/scripts/publish.sh msg",
        "sh -x scripts/publish.sh msg",
        "source scripts/publish.sh",
        'cd ~/waveflow && bash scripts/publish.sh "msg"',
    ],
)
def test_the_publish_script_is_refused_however_it_is_launched(command):
    """rule: publish-is-the-owners. The guard cannot read the `git push` inside a script
    file, so the file itself is refused by name."""
    out = bash(command)
    assert verdict(out) == "deny", command
    assert "publishing is" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize(
    "command",
    ["cat scripts/publish.sh", "git diff -- scripts/publish.sh", "bash scripts/publish-dry.sh"],
)
def test_reading_or_naming_the_publish_script_is_allowed(command):
    """rule: publish-is-the-owners."""
    assert verdict(bash(command)) == "", command


def _config(tmp_path, text: str):
    path = tmp_path / "harness.toml"
    path.write_text(text, encoding="utf-8")
    return {"WAVE_HARNESS_CONFIG": str(path)}


def test_an_unparseable_config_warns_and_keeps_the_generic_rules(tmp_path):
    """rule: harness-config-unreadable. The repo's rules are off, visibly; the generic
    refusals are not."""
    env = _config(tmp_path, "[guard_bash\nbroken")
    out = run_hook(GUARD_BASH, {"tool_input": {"command": "ls"}}, env)
    assert warned(out) and "did not parse" in out["systemMessage"], out
    out = run_hook(GUARD_BASH, {"tool_input": {"command": "git push"}}, env)
    assert verdict(out) == "deny"


def test_a_config_entry_of_the_wrong_type_is_dropped_with_a_warning_not_a_crash(tmp_path):
    """rule: harness-config-invalid. `warn_make = ["ci"]` once raised, the hook exited 1,
    and the harness read that as no verdict for `make ci && git push`."""
    env = _config(tmp_path, '[guard_bash]\nwarn_make = ["ci"]\nhost_only = ["pytest"]\n')
    out = run_hook(GUARD_BASH, {"tool_input": {"command": "make ci && git push"}}, env)
    assert verdict(out) == "deny", out
    out = run_hook(GUARD_BASH, {"tool_input": {"command": "ls"}}, env)
    assert (
        warned(out) and "warn_make" in out["systemMessage"] and "host_only" in out["systemMessage"]
    )


def test_a_valid_config_raises_neither_warning(configured):
    """rules: harness-config-unreadable, harness-config-invalid."""
    assert CONFIG and bash("ls") == {}


def test_a_crashed_guard_refuses_instead_of_judging_nothing(monkeypatch):
    """rule: guard-crashed. A hook that raised exits 1, which the harness reads as no
    verdict — every refusal silently off."""
    module = load_hook(GUARD_BASH)
    monkeypatch.setattr(module, "segments", lambda command: 1 / 0)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_input": {"command": "ls"}})))
    captured = io.StringIO()
    with redirect_stdout(captured), pytest.raises(SystemExit) as stop:
        module.main()
    assert stop.value.code == 0
    out = json.loads(captured.getvalue())
    assert verdict(out) == "deny"
    assert "ZeroDivisionError" in out["hookSpecificOutput"]["permissionDecisionReason"]
