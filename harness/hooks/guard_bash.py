#!/usr/bin/env python3
"""PreToolUse/Bash guard: destructive git, blind gates, and the repo's own host rules.

Each rule encodes a loss that has already happened in a real codebase, not a style
preference. The rules a repo adds — runners that belong inside a container, make targets
and programs worth a warning — come from its `.claude/harness.toml` (see repo_config).

Two verdicts, and the line between them is the owner's: REFUSAL is only for
irreversible loss -- commit, merge, rebase and branch switching are routine, and
prompting on them was ruled out as friction, so nothing less interrupts the turn.
A WARNING is for a command that will answer truthfully and mean something else: a
count blind to untracked files, a viewport narrower than it claims, a gate that runs
nowhere. Blindness is not loss, so it never blocks; it arrives beside the command
that caused it, which is the only moment it is useful.

Every rule carries a stable id, and tests/test_hooks_are_armed.py refuses to let one
exist without a witness that goes red without it.
"""

import json
import os
import re
import shlex
import sys

import repo_config

DEFAULT_HOST_MARKERS = ("docker compose exec", "docker-compose exec", "docker exec", "make ")


DENIALS: list[tuple[str, str]] = []
WARNINGS: list[tuple[str, str]] = []


class RepoRules:
    """`[guard_bash]` of the repo's harness.toml: what this guard cannot know on its own."""

    def __init__(self, config: dict) -> None:
        rules = repo_config.section(config, "guard_bash")
        self.owner = repo_config.section(config, "harness").get("owner") or "the owner"
        self.host_markers = tuple(rules.get("host_markers", DEFAULT_HOST_MARKERS))
        self.host_only = dict(rules.get("host_only", {}))
        self.host_only_npm = dict(rules.get("host_only_npm", {}))
        self.warn_make = list(rules.get("warn_make", []))
        self.warn_program = list(rules.get("warn_program", []))


RULES = RepoRules({})


def decide(decision: str, rule: str, reason: str) -> None:
    """Record a verdict under a stable rule id. Every rule sees the whole command
    before anything is emitted, and tests/test_hooks_are_armed.py reads these ids."""
    (DENIALS if decision == "deny" else WARNINGS).append((rule, reason))


def emit() -> None:
    """Only irreversible data loss is refused. Routine git is never interrupted:
    commit and merge run unprompted, because a prompt on each one is friction the
    owner has ruled against.

    A warning states no permissionDecision at all: emitting one here would answer a
    prompt the user was entitled to see.
    """
    if DENIALS:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": DENIALS[0][1],
                }
            },
            sys.stdout,
        )
        sys.exit(0)
    if WARNINGS:
        # Rules judged on the whole command are recorded once per pipeline element.
        # The same paragraph twice is how a channel stops being read.
        once = dict.fromkeys(rule for rule, _ in WARNINGS)
        reasons = {rule: reason for rule, reason in WARNINGS}
        advice = "\n".join(reasons[rule] for rule in once)
        json.dump(
            {
                "systemMessage": advice,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": advice,
                },
            },
            sys.stdout,
        )
    sys.exit(0)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\2$", re.DOTALL | re.MULTILINE)
SEPARATORS = ("&&", "||", ";", "|", "&", "\n")


def strip_heredocs(command: str) -> str:
    """Heredoc bodies are data. Left in, an apostrophe there unbalances the lexer."""
    return HEREDOC.sub(" ", command)


def split_tokens(text: str) -> list[str]:
    """Tokenize, degrading to a plain split rather than giving up.

    A lexer error must never blank the guard: `echo it's fine; git push` once
    parsed to zero segments, which every rule below reads as nothing to check.
    """
    for posix in (True, False):
        try:
            lexer = shlex.shlex(text, posix=posix, punctuation_chars=True)
            lexer.whitespace_split = True
            return list(lexer)
        except ValueError:
            continue
    spaced = text
    for sep in SEPARATORS:
        spaced = spaced.replace(sep, f" {sep} ")
    return [t.strip("\"'") for t in spaced.split() if t.strip("\"'")]


def segments(command: str) -> list[list[str]]:
    """Split a shell command into argv lists, one per pipeline/list element."""
    out: list[list[str]] = []
    current: list[str] = []
    for token in split_tokens(strip_heredocs(command)):
        if token in SEPARATORS:
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    if current:
        out.append(current)
    return out


def _has_short_flag(argv: list[str], letter: str) -> bool:
    """`-af` carries `-f`. Reading only the exact token missed `pkill -af` entirely."""
    return any(
        arg.startswith("-") and not arg.startswith("--") and letter in arg[1:] for arg in argv
    )


SELF_MATCH = (
    "matches this hook's own shell: the harness runs `bash -c 'eval \"<command>\"'`, so the "
    "pattern itself stands in that process's cmdline and the match is guaranteed. `pkill -f` "
    "then exits 144 and the rest of the script never runs; `pgrep -f` is red whatever the "
    "truth. Write the check to a file and run the file — its cmdline is just its path — and "
    "prove it BOTH ways: a real hit and a real miss."
)


def head(argv: list[str]) -> list[str]:
    """Drop leading env assignments and sudo so argv[0] is the real program."""
    i = 0
    while i < len(argv) and (
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[i]) or argv[i] == "sudo"
    ):
        i += 1
    return argv[i:]


GIT_GLOBAL_OPTIONS_WITH_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace")
STASH_READ_ONLY = ("list", "show")


def git_subcommand_index(argv: list[str]) -> int:
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if argv[i] in GIT_GLOBAL_OPTIONS_WITH_VALUE else 1
    return i


def check_git(argv: list[str]) -> None:
    sub_index = git_subcommand_index(argv)
    sub = argv[sub_index] if sub_index < len(argv) else ""
    flags = [a for a in argv[sub_index:] if a.startswith("-")]
    rest = argv[sub_index:]

    if sub == "push":
        decide(
            "deny",
            "git-push",
            f"`git push` publishes to the remote — the owner's call. Ask {RULES.owner} to run it.",
        )

    if sub == "reset" and "--hard" in flags:
        decide(
            "deny",
            "git-reset-hard",
            "`git reset --hard` discards uncommitted work. Commit your own paths first: `git commit -m '...' -- <paths>`.",
        )

    if sub == "clean" and any(f.startswith("-") and "f" in f for f in flags):
        decide(
            "deny",
            "git-clean-force",
            "`git clean -f` deletes untracked files, which is where new tests and plans live.",
        )

    if sub == "checkout" and any(a == "--" or a == "." for a in rest):
        decide(
            "deny",
            "git-checkout-worktree",
            "`git checkout --` has already erased an uncommitted fix once. "
            "Commit your own paths instead of reverting the worktree: `git commit -- <paths>`.",
        )

    if sub == "restore" and "--staged" not in flags:
        decide(
            "deny",
            "git-restore",
            "`git restore` overwrites the worktree copy. Commit your own paths first: `git commit -- <paths>`.",
        )

    stash_args = [a for a in argv[sub_index + 1 :] if not a.startswith("-")]
    stash_action = stash_args[0] if stash_args else ""

    if sub == "stash" and stash_action in ("drop", "clear"):
        decide(
            "deny",
            "git-stash-destructive",
            "`git stash drop/clear` discards the stash irreversibly.",
        )

    elif sub == "stash" and stash_action not in STASH_READ_ONLY:
        decide(
            "deny",
            "git-stash-shared-stack",
            "`git stash` moves the worktree through a stack that belongs to the REPOSITORY, "
            "shared by every parallel session: a neighbouring session's push renumbers yours "
            "and a pop applies theirs. Commit your own paths with "
            "`git commit -m '...' -- <paths>`, or copy the files aside. `git stash list` and "
            "`git stash show` stay allowed.",
        )

    if sub == "branch" and "-D" in flags:
        decide(
            "deny", "git-branch-force-delete", "`git branch -D` force-deletes an unmerged branch."
        )

    if sub in ("filter-branch", "filter-repo"):
        decide("deny", "git-history-rewrite", f"`git {sub}` rewrites history.")

    if sub == "add" and any(a in (".", "-A", "--all", "-u", "--update") for a in rest):
        decide(
            "deny",
            "git-add-blanket",
            "Stage by name. A blanket `git add` swallows a neighbouring session's staged files — "
            "that has already happened.",
        )

    if sub == "add":
        for path in (a for a in rest if not a.startswith("-") and a != "add"):
            if path.endswith("/") or os.path.isdir(path):
                decide(
                    "warn",
                    "git-add-directory",
                    f"`git add {path}` skips .gitignore'd files SILENTLY, with exit 0 — only "
                    "`git add <file>` names them. A commit can then claim to carry evidence and "
                    "carry none: nine mutation logs went in this way and one file landed, because "
                    "`.gitignore` holds `*.log`. It also stages whatever a neighbouring session "
                    "left in that directory. Stage by name, and read `git show --stat` afterwards "
                    "rather than the exit code.",
                )
                break

    if sub == "log" and "--" in rest:
        paths = rest[rest.index("--") + 1 :]
        if paths and not all(p.startswith(":/") for p in paths):
            decide(
                "warn",
                "git-log-pathspec-cwd",
                "A git pathspec resolves relative to the cwd, not to the repo root, and this "
                "harness KEEPS the cwd between calls — one `cd frontend/` ten calls ago is "
                "enough. An empty result then arrives with exit 0 and reads as `never "
                "committed` when it means `wrong directory`. Prefix the path with `:/`, or ask "
                "outright: `git ls-files --error-unmatch <path>`.",
            )

    if sub == "grep" and not any(a in ("--untracked", "--no-index") for a in rest):
        decide(
            "warn",
            "git-grep-untracked-blind",
            "`git grep` searches the index and tracked files, so a file written this session "
            "does not exist for it: the count comes back unchanged, with exit 0, and reads as "
            "`my work added nothing`. Pass `--untracked`, or measure after staging by name — "
            "and say in the report which of the two you used.",
        )

    if sub == "commit":
        if any(
            f in ("-a", "--all") or (f.startswith("-") and not f.startswith("--") and "a" in f)
            for f in flags
        ):
            decide(
                "deny",
                "git-commit-all",
                "`git commit -a` stages everything tracked. Stage by name instead.",
            )
        elif "--" not in rest:
            decide(
                "warn",
                "git-commit-whole-index",
                "This commits the WHOLE index, including paths you never named — the index is "
                "shared per worktree, and a neighbouring session's staged rename was swallowed "
                "this way once. Name the paths: `git commit -m '...' "
                "-- <paths>`. Then read `git show --name-status HEAD`.",
            )


def runner(argv: list[str]) -> str:
    """argv[0], or what `npx` is about to fetch and run in its place."""
    program = os.path.basename(argv[0])
    if program in ("npx", "pnpx", "bunx") and len(argv) > 1:
        program = os.path.basename(argv[1])
    return program


def check_make_targets(argv: list[str]) -> None:
    """`make ` is a host marker by default, so this cannot live in check_host_only."""
    if os.path.basename(argv[0]) != "make" or not argv[1:]:
        return
    for rule in RULES.warn_make:
        if argv[1] in rule.get("targets", ()):
            decide("warn", rule["id"], rule["reason"].replace("{target}", argv[1]))


def check_host_only(command: str, argv: list[str]) -> None:
    if any(marker in command for marker in RULES.host_markers):
        return

    program = runner(argv)

    if program in RULES.host_only:
        decide(
            "deny",
            "host-only-runner",
            f"`{program}` must run inside the container. Use `{RULES.host_only[program]}` "
            f"or `docker compose exec <svc> {program} ...`.",
        )

    if program in ("npm", "pnpm", "yarn"):
        script = ""
        if len(argv) > 2 and argv[1] == "run":
            script = argv[2]
        elif len(argv) > 1 and argv[1] in RULES.host_only_npm:
            script = argv[1]
        if script in RULES.host_only_npm:
            decide(
                "deny",
                "host-only-npm-script",
                f"`{program} {script}` must run inside the container. "
                f"Use `{RULES.host_only_npm[script]}`.",
            )


def check_blind_gates(command: str, argv: list[str]) -> None:
    if "vitest" in command and "--environment" in argv:
        decide(
            "deny",
            "vitest-environment-flag",
            "`--environment` does not override vitest `projects` — the run silently keeps the "
            "project's own environment. Select with `--project node` instead.",
        )

    program = os.path.basename(argv[0])
    if program == "pkill" and _has_short_flag(argv, "f"):
        decide("deny", "pkill-f-self-match", f"`pkill -f` {SELF_MATCH}")

    if program == "pgrep" and _has_short_flag(argv, "f"):
        decide("warn", "pgrep-f-self-match", f"`pgrep -f` {SELF_MATCH}")

    for rule in RULES.warn_program:
        if runner(argv) in rule.get("programs", ()):
            decide("warn", rule["id"], rule["reason"])

    if "--window-size" in command and ("--headless" in command or "chrome" in command):
        decide(
            "warn",
            "headless-window-size",
            "`--window-size=390,940` does NOT give a 390px viewport: headless holds a minimum "
            "window width, the page renders at innerWidth 500, and the SCREENSHOT is cropped "
            "to 390 — so a narrow `--window-size` yields a false positive (text looks clipped) "
            "and a false negative (it fits, on a wider screen than claimed). Measure inside an "
            "iframe of that width, with "
            "`--allow-file-access-from-files` and `--virtual-time-budget`, and read "
            "`scrollWidth` — not a picture.",
        )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    global RULES
    RULES = RepoRules(repo_config.load(payload.get("cwd")))

    # A heredoc body is data, and the rules that read the whole command cannot tell a
    # forbidden form from a string that merely spells one.
    code = strip_heredocs(command)
    parsed = [head(argv) for argv in segments(command)]

    for argv in parsed:
        if not argv:
            continue
        if os.path.basename(argv[0]) == "git":
            check_git(argv)
        check_make_targets(argv)
        check_host_only(code, argv)
        check_blind_gates(code, argv)

    emit()


if __name__ == "__main__":
    main()
