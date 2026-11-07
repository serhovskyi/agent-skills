"""Behaviour witnesses for harness/hooks: a payload goes in, a verdict comes out.

A grep over the hook source would be class-6 blindness -- a gate measuring STATE while
the defect lives in the ACTION. Every case here runs the hook and reads its verdict.

Each case names the rule id it witnesses (`rule: <id>`); test_hooks_are_armed.py
compares those ids to the ones guard_bash.py actually fires, in both directions.
"""

from pathlib import Path

import pytest
from harness_support import HOOKS, MEMORY_BUDGET, MEMORY_HINT, load_hook, run_hook

GUARD_BASH = HOOKS / "guard_bash.py"
SESSION_STATE = HOOKS / "session_state.py"
WARN_PIPEFAIL = HOOKS / "warn_pipefail.py"

pytestmark = pytest.mark.usefixtures("configured")


def bash(command: str, cwd: Path | None = None) -> dict:
    payload = {"tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return run_hook(GUARD_BASH, payload)


def verdict(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("permissionDecision", "")


def warned(output: dict) -> bool:
    """A warn carries advice in both channels and NO permission decision."""
    return bool(output.get("systemMessage")) and not verdict(output)


def test_a_warn_never_carries_a_permission_decision():
    """rule: git-add-directory. `allow` from a hook skips the permission prompt the
    user would otherwise see, so a warn states no decision at all."""
    out = bash("git add backend/")
    assert warned(out), out
    assert "permissionDecision" not in out.get("hookSpecificOutput", {})
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(
    "command,fragment",
    [
        ("git push origin main", "publishes to the remote"),
        ("git reset --hard HEAD~1", "discards uncommitted work"),
        ("git clean -fd", "deletes untracked files"),
        ("git checkout -- api/app/main.py", "already erased an uncommitted fix"),
        ("git restore api/app/main.py", "overwrites the worktree copy"),
        ("git stash drop stash@{0}", "discards the stash irreversibly"),
        ("git branch -D feature", "force-deletes an unmerged branch"),
        ("git filter-branch --tree-filter true HEAD", "rewrites history"),
        ("git add .", "Stage by name"),
        ("git commit -am 'x'", "stages everything tracked"),
        ("pytest tests/api -q", "must run inside the container"),
        ("npm run test", "must run inside the container"),
        (
            "docker compose exec web npx vitest run --environment node",
            "does not override vitest",
        ),
        ("pkill -f chrome", "matches this hook's own shell"),
    ],
)
def test_the_fourteen_denials_still_bite(command, fragment):
    """rules: git-push, git-reset-hard, git-clean-force, git-checkout-worktree,
    git-restore, git-stash-destructive, git-branch-force-delete, git-history-rewrite,
    git-add-blanket, git-commit-all, host-only-runner, host-only-npm-script,
    vitest-environment-flag, pkill-f-self-match.

    Adding the warn channel must not have cost a single refusal.
    """
    out = bash(command)
    assert verdict(out) == "deny", out
    assert fragment in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize(
    "command",
    [
        "git status --porcelain",
        "git add harness/tests/test_hook_rules.py",
        "git commit -m 'feat: a thing'",
        "git commit -m 'feat: a thing' -- api/app/main.py",
        "make test-api",
        "docker compose exec api pytest tests/api -q",
    ],
)
def test_ordinary_work_is_never_refused(command):
    """The worst outcome of this hook is a session that cannot run a command and finds
    out mid-task. These are the commands a session runs all day."""
    assert verdict(bash(command)) != "deny", command


@pytest.mark.parametrize(
    "command",
    [
        "git status --porcelain",
        "git add harness/tests/test_hook_rules.py",
        "git commit -m 'feat: a thing' -- api/app/main.py",
        "make test-api",
        "docker compose exec api pytest tests/api -q",
    ],
)
def test_the_commands_of_a_normal_turn_are_fully_silent(command):
    """Advice that arrives on every turn stops being read. These say nothing at all."""
    assert bash(command) == {}, command


def test_a_rule_that_reads_the_whole_command_still_speaks_once():
    """rule: headless-window-size. It is judged on the command rather than on one
    argv, so it used to be recorded once per pipeline element -- the same paragraph
    twice, which is how a channel stops being read."""
    out = bash("chrome --headless=new --window-size=390,940 --dump-dom x.html | grep w")
    assert out["systemMessage"].count("does NOT give a 390px viewport") == 1


def test_a_forbidden_form_quoted_inside_a_heredoc_is_not_a_command():
    """A heredoc body is data. Measured: writing this very test file's fixtures warned
    about a --window-size that was a string in a script, not a browser being launched.
    """
    assert (
        bash("python3 - <<'EOF'\nprint('chrome --headless=new --window-size=390,940')\nEOF") == {}
    )


def test_pgrep_f_is_warned_because_it_matches_the_harness_shell():
    """rule: pgrep-f-self-match.

    `pkill -f` was already refused; `pgrep -f` was silent, and it is the same defect.
    """
    out = bash("pgrep -f chrome-headless-shell")
    assert warned(out), out
    assert "own shell" in out["systemMessage"]


def test_pkill_f_is_still_a_refusal_and_now_reads_bundled_flags():
    """rule: pkill-f-self-match. It exits 144 mid-script, so D4 keeps it at deny --
    and `-af` carries the same `-f` the exact-token check used to miss."""
    assert verdict(bash("pkill -f chrome")) == "deny"
    assert verdict(bash("pkill -af chrome")) == "deny"


def test_git_grep_without_untracked_is_warned():
    """rule: git-grep-untracked-blind. A file written this session does not exist for
    plain `git grep`, and the count comes back unchanged with exit 0."""
    out = bash("git grep -hE 'def test_' -- api/tests")
    assert warned(out), out
    assert "--untracked" in out["systemMessage"]


def test_git_grep_with_untracked_is_silent():
    """The green arm. A rule that fires on the fix too teaches nothing."""
    assert bash("git grep --untracked -hE 'def test_' -- api/tests") == {}


@pytest.mark.parametrize("untracked", [0, 4])
def test_the_preamble_names_git_grep_blindness_whether_or_not_untracked_paths_exist(untracked):
    """The note used to fire only where untracked paths already existed -- that is, it
    was silent at exactly the moment the blindness begins."""
    lines = load_hook(SESSION_STATE).preamble("main", "abc1234 x", 2, untracked, "")
    note = next(line for line in lines if "NOTE:" in line)
    assert "--untracked" in note, note


def test_the_hook_that_cannot_measure_says_nothing_at_all(tmp_path):
    """A directory that is not a worktree is not an occasion to guess."""
    assert run_hook(SESSION_STATE, {"cwd": str(tmp_path)}) == {}


# MEMORY.md is loaded into every session, so a line kept there is rent paid every turn.
# The budget was a sentence in a memory file; these make it arrive on its own.


def _index(tmp_path: Path, text: str) -> Path:
    index = tmp_path / "memory" / "MEMORY.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(text, encoding="utf-8")
    return index


def _oversized(tmp_path: Path) -> Path:
    return _index(tmp_path, "- " + "x" * (MEMORY_BUDGET + 100) + "\n")


def test_the_preamble_states_the_overage_when_the_index_is_too_big(tmp_path):
    line = load_hook(SESSION_STATE).budget_line(_oversized(tmp_path), MEMORY_BUDGET)
    assert line and "MEMORY.md" in line and str(MEMORY_BUDGET) in line, line


def test_the_preamble_is_quiet_when_the_index_fits(tmp_path):
    """The green arm: a brake that pulls on every session is a brake nobody reads."""
    index = _index(tmp_path, "- short\n")
    assert load_hook(SESSION_STATE).budget_line(index, MEMORY_BUDGET) is None


def test_a_missing_index_is_silence_not_a_crash(tmp_path):
    index = tmp_path / "nowhere" / "MEMORY.md"
    assert load_hook(SESSION_STATE).budget_line(index, MEMORY_BUDGET) is None


def _session_context(repo: Path, index: Path) -> str:
    out = run_hook(SESSION_STATE, {"cwd": str(repo)}, env={"CLAUDE_MEMORY_INDEX": str(index)})
    return out["hookSpecificOutput"]["additionalContext"]


def test_the_configured_budget_and_hint_reach_the_session(tmp_path, repo_without_config):
    context = _session_context(repo_without_config, _oversized(tmp_path))
    [line] = [line for line in context.splitlines() if "MEMORY:" in line]
    assert str(MEMORY_BUDGET) in line and line.endswith(MEMORY_HINT), line


def test_without_a_config_there_is_no_budget_line(tmp_path, repo_without_config, unconfigured):
    context = _session_context(repo_without_config, _oversized(tmp_path))
    assert "MEMORY:" not in context, context


@pytest.mark.parametrize(
    "command,fragment",
    [
        ("make ci", "`make ci`"),
        ("make verify", "`make verify`"),
        ("git log --all -- docs/plans/x.md", "relative to the cwd"),
        (
            "chrome --headless=new --window-size=390,940 --dump-dom file:///tmp/a.html",
            "innerWidth",
        ),
        ("npx prettier --write web/src/App.tsx", "not this repo's formatter"),
    ],
)
def test_the_ported_lessons_warn(command, fragment):
    """rules: make-ci-is-local, git-log-pathspec-cwd,
    headless-window-size, npx-prettier."""
    out = bash(command)
    assert warned(out), out
    assert fragment in out["systemMessage"], out["systemMessage"]


@pytest.mark.parametrize(
    "command",
    [
        "git stash",
        "git stash push -- api/app/main.py",
        "git stash save wip",
        "git stash pop",
        "git stash apply stash@{0}",
        "git stash -u",
        "git -C /repo stash",
        "git -c user.name=x stash push",
    ],
)
def test_every_stash_form_that_moves_the_worktree_is_refused(command):
    """rule: git-stash-shared-stack."""
    out = bash(command)
    assert verdict(out) == "deny", out
    assert (
        "shared by every parallel session" in out["hookSpecificOutput"]["permissionDecisionReason"]
    )


@pytest.mark.parametrize(
    "command,fragment",
    [
        ("git -C /repo push origin main", "publishes to the remote"),
        ("git -c core.editor=true reset --hard HEAD~1", "discards uncommitted work"),
    ],
)
def test_a_global_option_does_not_hide_the_subcommand(command, fragment):
    """rules: git-push, git-reset-hard."""
    out = bash(command)
    assert verdict(out) == "deny", out
    assert fragment in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_a_global_option_value_is_not_an_argument_of_the_subcommand(tmp_path):
    for command in (
        "git -C . add api/app/main.py",
        "git -C . checkout main",
        f"git -C {tmp_path} add api/app/main.py",
    ):
        assert bash(command) == {}, command


@pytest.mark.parametrize(
    "command",
    ["git stash list", "git stash show", "git stash show -p stash@{0}", "git -C /repo stash list"],
)
def test_the_read_only_stash_forms_are_not_refused(command):
    assert bash(command) == {}, command


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "git checkout -- api/app/main.py",
        "git restore api/app/main.py",
    ],
)
def test_no_refusal_advises_the_stash(command):
    reason = bash(command)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "stash" not in reason.lower()


def test_a_host_pytest_is_pointed_at_its_make_target():
    reason = bash("pytest tests/harness -q")["hookSpecificOutput"]["permissionDecisionReason"]
    assert "make test-api" in reason


@pytest.mark.parametrize("command", ["npm run lint", "npm test"])
def test_a_host_npm_script_is_pointed_at_its_make_target(command):
    reason = bash(command)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "make lint-web" in reason or "make test-web" in reason, reason


@pytest.mark.parametrize(
    "command",
    [
        "make test-api",
        "git log --oneline -5",
        "git log --all -- :/docs/plans/x.md",
        "git stash list",
        "git stash show stash@{0}",
        "chrome --headless=new --dump-dom file:///tmp/wrapper.html",
        "docker compose exec web npx eslint src --max-warnings 0",
    ],
)
def test_the_ported_lessons_stay_silent_on_the_correct_form(command):
    """The green arm of each rule. Advice that fires on the fix too teaches nothing."""
    assert bash(command) == {}, command


def test_a_bare_commit_is_warned_because_it_commits_the_whole_index():
    """rule: git-commit-whole-index.

    Measured on 2026-08-16: a `git commit` naming no paths swallowed a neighbouring
    session's staged rename. The index is shared per worktree; only a pathspec makes a
    commit's contents the caller's own.
    """
    out = bash("git commit -m 'feat: a thing'")
    assert warned(out), out
    assert "-- <paths>" in out["systemMessage"]


@pytest.mark.parametrize(
    "command",
    [
        "pytest tests/api -q",
        "npm run test",
        "make ci",
        "npx prettier --write web/src/App.tsx",
    ],
    ids=["host-only-runner", "host-only-npm-script", "warn-make", "warn-program"],
)
def test_a_repo_rule_is_silent_without_a_config(repo_without_config, unconfigured, command):
    assert bash(command, cwd=repo_without_config) == {}, command


def test_the_config_is_found_in_the_repo_of_the_payload_cwd(
    repo_without_config, configured, unconfigured
):
    (repo_without_config / ".claude").mkdir()
    configured.rename(repo_without_config / ".claude" / "harness.toml")
    assert verdict(bash("pytest tests -q", cwd=repo_without_config)) == "deny"


@pytest.mark.parametrize("config", [True, False], ids=["configured", "unconfigured"])
def test_a_push_refusal_names_the_configured_owner(monkeypatch, repo_without_config, config):
    if not config:
        monkeypatch.delenv("WAVE_HARNESS_CONFIG")
    reason = bash("git push", cwd=repo_without_config)["hookSpecificOutput"][
        "permissionDecisionReason"
    ]
    assert f"Ask {'the maintainer' if config else 'the owner'} to run it" in reason, reason


def _pipefail(command: str, cwd: Path | None = None) -> dict:
    payload = {"tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    return run_hook(WARN_PIPEFAIL, payload)


@pytest.mark.parametrize(
    "command",
    ["pytest -q | tail -5", "make check-api 2>&1 | grep passed", "./manage.py test | tail -5"],
)
def test_a_runner_piped_into_a_pager_is_warned(command):
    out = _pipefail(command)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "pipefail" in out["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(
    "command",
    [
        "set -o pipefail; pytest -q | tail -5",
        "pytest -q | tail -5; echo ${PIPESTATUS[0]}",
        "pytest -q",
    ],
)
def test_a_run_whose_exit_code_is_its_own_is_silent(command):
    assert _pipefail(command) == {}, command


def test_a_configured_runner_is_silent_without_a_config(repo_without_config, unconfigured):
    assert _pipefail("make check-api 2>&1 | grep passed", cwd=repo_without_config) == {}
