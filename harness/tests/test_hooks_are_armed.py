"""The rules are armed: every hook is registered and every rule id is unique.

A rule nobody registered never fires.

Parsed with ast, not grepped: the reasons these rules carry quote the very commands
they refuse, so a grep for `decide` or for `allow` reads prose as code.
"""

import ast
import json
import re
import shlex
import tomllib
from pathlib import Path

from harness_support import CONFIG, HARNESS, HOOKS

# Every hook, and the event/matcher pair it is useless without.
REGISTRATION = {
    "guard_bash.py": ("PreToolUse", "Bash"),
    "warn_pipefail.py": ("PostToolUse", "Bash"),
    "session_state.py": ("SessionStart", ""),
    "stop_dirty.py": ("Stop", ""),
}

WITNESSES = sorted(Path(__file__).resolve().parent.glob("test_hook_rules*.py"))
WITNESS = re.compile(r"\brules?: ((?:[a-z0-9]+(?:-[a-z0-9]+)*(?:,\s+)?)+)")


def _guard_bash_tree() -> ast.Module:
    source = (HOOKS / "guard_bash.py").read_text(encoding="utf-8")
    assert source.strip(), "guard_bash.py is empty -- a zero-byte file is not a guard"
    return ast.parse(source)


def _decide_calls() -> list[ast.Call]:
    return [
        node
        for node in ast.walk(_guard_bash_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "decide"
        and len(node.args) >= 3
    ]


def _rule_ids() -> list[str]:
    """The second positional argument of every decide() call that names its id."""
    return [
        call.args[1].value for call in _decide_calls() if isinstance(call.args[1], ast.Constant)
    ]


def _configured_rule_ids() -> set[str]:
    rules = tomllib.loads(CONFIG)["guard_bash"]
    return {rule["id"] for key in ("warn_make", "warn_program") for rule in rules[key]}


def _witnessed_rule_ids() -> set[str]:
    docstrings = (
        ast.get_docstring(node) or ""
        for path in WITNESSES
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.FunctionDef)
    )
    return {
        rule.strip()
        for docstring in docstrings
        for match in WITNESS.finditer(docstring)
        for rule in match.group(1).split(",")
        if rule.strip()
    }


def _registered() -> list[tuple[str, str, str]]:
    plugin = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    return [
        (event, entry.get("matcher", ""), hook["command"])
        for event, entries in plugin["hooks"].items()
        for entry in entries
        for hook in entry["hooks"]
    ]


def _script(command: str) -> Path:
    [token] = [part for part in shlex.split(command) if "${CLAUDE_PLUGIN_ROOT}" in part]
    return Path(token.replace("${CLAUDE_PLUGIN_ROOT}", str(HARNESS)))


def test_every_hook_is_registered_at_the_event_it_needs():
    """Renaming a hook, or moving it to another event, silences it completely."""
    registered = {
        (event, matcher, _script(command).name) for event, matcher, command in _registered()
    }
    missing = [
        (name, event, matcher)
        for name, (event, matcher) in REGISTRATION.items()
        if (event, matcher, name) not in registered
    ]
    assert not missing, (
        f"{missing} are not registered as written -- each one cannot fire, and nothing "
        "else in this plugin would have told you."
    )


def test_every_hook_hooks_json_names_is_on_disk():
    absent = [command for _, _, command in _registered() if not _script(command).is_file()]
    assert not absent, f"{absent} are registered in hooks.json and not on disk"


def test_every_hook_named_here_is_on_disk():
    absent = [name for name in REGISTRATION if not (HOOKS / name).is_file()]
    assert not absent, f"{absent} are expected in hooks/ and not on disk"


def test_every_rule_id_names_exactly_one_verdict():
    """Two rules sharing an id cannot be told apart in a verdict."""
    ids = _rule_ids()
    duplicated = sorted({rule for rule in ids if ids.count(rule) > 1})
    assert not duplicated, duplicated


def test_every_rule_fired_is_witnessed_and_every_witness_names_a_rule():
    fired = set(_rule_ids()) | _configured_rule_ids()
    witnessed = _witnessed_rule_ids()
    assert not fired - witnessed, f"{sorted(fired - witnessed)} fire and no case witnesses them"
    assert not witnessed - fired, f"{sorted(witnessed - fired)} are witnessed and never fire"


def test_the_warn_channel_cannot_answer_a_permission_prompt():
    """`allow` from a PreToolUse hook skips the prompt the user was entitled to see.

    Only emit() is read: the rule REASONS quote commands and would trip a grep.
    """
    emit = next(
        node
        for node in ast.walk(_guard_bash_tree())
        if isinstance(node, ast.FunctionDef) and node.name == "emit"
    )
    literals = {
        node.value
        for node in ast.walk(emit)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "allow" not in literals and "ask" not in literals, (
        "emit() can state a permissionDecision other than deny. A warning that answers "
        "the prompt is not a warning -- it is an approval the user never gave."
    )


def test_the_refusals_are_still_refusals():
    """D4: warnings are for blindness, denial is for irreversible loss. If a `deny`
    quietly became a `warn`, the count here moves and this file says so."""
    decisions = [
        call.args[0].value for call in _decide_calls() if isinstance(call.args[0], ast.Constant)
    ]
    assert decisions.count("deny") == 19, (
        f"guard_bash.py now makes {decisions.count('deny')} refusals, not 19. Adding one "
        "needs the owner's call (D4); losing one is a guard that stopped guarding."
    )
    assert set(decisions) == {"deny", "warn"}, sorted(set(decisions))
