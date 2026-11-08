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
    """`[guard_bash]` of the repo's harness.toml: what this guard cannot know on its own.

    A repo controls this file, so a wrong type is recorded in `problems` and the entry is
    dropped — never raised. An exception here would end the hook with exit 1, which the
    harness reads as "no verdict", and the generic rules would be off along with the
    repo's. A repo may add rules this way; it may not switch the others off.
    """

    def __init__(self, config: dict) -> None:
        self.problems: list[str] = []
        rules = repo_config.section(config, "guard_bash")
        owner = repo_config.section(config, "harness").get("owner")
        self.owner = owner if isinstance(owner, str) and owner else "the owner"
        self.host_markers = tuple(self._strings(rules, "host_markers", DEFAULT_HOST_MARKERS))
        self.host_only = self._mapping(rules, "host_only")
        self.host_only_npm = self._mapping(rules, "host_only_npm")
        self.warn_make = self._rules(rules, "warn_make", "targets")
        self.warn_program = self._rules(rules, "warn_program", "programs")

    def _strings(self, rules: dict, key: str, default: tuple) -> list[str]:
        value = rules.get(key, list(default))
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return value
        self.problems.append(f"{key} must be a list of strings")
        return list(default)

    def _mapping(self, rules: dict, key: str) -> dict[str, str]:
        value = rules.get(key, {})
        if isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        ):
            return value
        self.problems.append(f'{key} must be a table of program = "what to run instead"')
        return {}

    def _rules(self, rules: dict, key: str, names: str) -> list[dict]:
        value = rules.get(key, [])
        if not isinstance(value, list):
            self.problems.append(f"{key} must be an array of tables")
            return []
        kept = []
        for i, rule in enumerate(value):
            if (
                isinstance(rule, dict)
                and isinstance(rule.get("id"), str)
                and isinstance(rule.get("reason"), str)
                and isinstance(rule.get(names), list)
                and all(isinstance(n, str) for n in rule[names])
            ):
                kept.append(rule)
            else:
                self.problems.append(f"{key}[{i}] needs string id, string reason, list {names}")
        return kept


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


HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)(\w+)\1(?P<opener>[^\n]*)\n.*?^\t*\2[ \t]*$", re.DOTALL | re.MULTILINE
)
PUNCTUATION = "();<>|&\n"
SEPARATOR_CHARS = set("();|&\n")
SEPARATORS = ("&&", "||", ";", "|", "&", "\n", "(", ")")


def strip_heredocs(command: str) -> str:
    """Heredoc bodies are data. Left in, an apostrophe there unbalances the lexer.

    The rest of the opener line stays: `git commit -F - <<EOF && git reset --hard`
    once lost its second command with the body.
    """
    return HEREDOC.sub(lambda m: f"<<{m.group(2)}{m.group('opener')}", command)


def split_tokens(text: str) -> list[str]:
    """Tokenize, degrading to a plain split rather than giving up.

    A lexer error must never blank the guard: `echo it's fine; git push` once
    parsed to zero segments, which every rule below reads as nothing to check.
    A newline is punctuation here, not whitespace: as whitespace it glued every
    later line onto the first command's argv, and `git status\ngit push` was one
    harmless `git status`. Comments are cut by hand below, because the lexer's own
    rule starts one at any `#`, URL fragments and issue refs included.
    """
    for posix in (True, False):
        try:
            lexer = shlex.shlex(text, posix=posix, punctuation_chars=PUNCTUATION)
            lexer.whitespace_split = True
            lexer.whitespace = " \t\r"
            lexer.commenters = ""
            return list(lexer)
        except ValueError:
            continue
    spaced = text
    for sep in SEPARATORS:
        spaced = spaced.replace(sep, f" {sep} ")
    return [t.strip("\"'") for t in spaced.split() if t.strip("\"'")]


def is_separator(token: str) -> bool:
    return bool(token) and set(token) <= SEPARATOR_CHARS


def segments(command: str) -> list[list[str]]:
    """Split a shell command into argv lists, one per pipeline/list element.

    `(`, `)` and newlines separate too, so `(git push)`, `x=$(git push)` and a second
    line are commands of their own. A word that starts with `#` opens a comment that
    runs to the end of its line.
    """
    out: list[list[str]] = []
    current: list[str] = []
    in_comment = False
    for token in split_tokens(strip_heredocs(command)):
        if in_comment and not ("\n" in token and is_separator(token)):
            continue
        in_comment = False
        if is_separator(token):
            if current:
                out.append(current)
            current = []
        elif token.startswith("#"):
            in_comment = True
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


TRANSPARENT = {
    "env",
    "nohup",
    "time",
    "nice",
    "ionice",
    "stdbuf",
    "command",
    "exec",
    "builtin",
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "while",
    "until",
    "do",
    "done",
    "!",
    "{",
    "}",
}
TRANSPARENT_WITH_VALUE = {"timeout", "xargs", "sudo"}
VALUE_FLAGS = {"-n", "-P", "-I", "-L", "-s", "-k", "--max-args", "-u", "-g", "-a", "-d"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
RUN_THROUGH = {"uv", "poetry", "pipenv", "pdm", "hatch", "rye"}
RUN_VALUE_FLAGS = {
    "--with",
    "--with-requirements",
    "--with-editable",
    "--python",
    "-p",
    "--extra",
    "--group",
    "--only-group",
    "--package",
    "--directory",
    "--project",
    "--env-file",
    "--index",
    "-C",
}


def head(argv: list[str]) -> list[str]:
    """Drop what runs the command without being it, so argv[0] is the real program.

    `xargs git push`, `timeout 30 git stash`, `if …; then git reset --hard; fi` and
    `nohup pytest` each slipped every rule here once: the program the rule names stood
    in argv[1] or argv[2].
    """
    i = 0
    while i < len(argv):
        token = os.path.basename(argv[i])
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[i]) or token in TRANSPARENT:
            i += 1
        elif token in TRANSPARENT_WITH_VALUE:
            i += 1
            while i < len(argv) and argv[i].startswith("-"):
                i += 2 if argv[i] in VALUE_FLAGS else 1
            if token == "timeout" and i < len(argv):
                i += 1
        else:
            break
    return argv[i:]


def unwrapped(argv: list[str]) -> list[list[str]]:
    """The commands a shell wrapper will run: `bash -c '<str>'`, `eval <words>`.

    The inner string is a command in its own right and is parsed as one. `bash -c
    "git push"` once reached the remote through this hook, because its argv[0] was bash.
    """
    if not argv:
        return []
    program = os.path.basename(argv[0])
    inner = None
    if program in SHELLS:
        for i, arg in enumerate(argv[1:], 1):
            if _has_short_flag([arg], "c") and i + 1 < len(argv):
                inner = argv[i + 1]
                break
            if not arg.startswith("-"):
                break
    elif program == "eval":
        inner = " ".join(argv[1:])
    if inner is None:
        return [argv]
    return [cmd for seg in segments(inner) for cmd in unwrapped(head(seg))]


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
            "`git reset --hard` discards uncommitted work. "
            "Commit your own paths first: `git commit -m '...' -- <paths>`.",
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

    if sub == "checkout" and ("--force" in flags or _has_short_flag(flags, "f")):
        decide(
            "deny",
            "git-checkout-force",
            "`git checkout -f` throws away local changes to reach the target. Commit your own "
            "paths first: `git commit -- <paths>`.",
        )

    if sub == "switch" and (
        "--discard-changes" in flags or "--force" in flags or _has_short_flag(flags, "f")
    ):
        decide(
            "deny",
            "git-switch-discard",
            "`git switch --discard-changes` throws away local changes. Commit your own paths "
            "first: `git commit -- <paths>`.",
        )

    staged_only = ("--staged" in flags or _has_short_flag(flags, "S")) and not (
        "--worktree" in flags or _has_short_flag(flags, "W")
    )
    if sub == "restore" and not staged_only:
        decide(
            "deny",
            "git-restore",
            "`git restore` overwrites the worktree copy. "
            "Commit your own paths first: `git commit -- <paths>`.",
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
    """argv[0], or the program a launcher runs in its place: `npx X`, `python -m X`,
    `uv run X`, `poetry run X`."""
    program = os.path.basename(argv[0])
    if program in ("npx", "pnpx", "bunx") and len(argv) > 1:
        return os.path.basename(argv[1])
    if re.fullmatch(r"python[0-9.]*", program) and len(argv) > 2 and argv[1] == "-m":
        return argv[2]
    if program in RUN_THROUGH and len(argv) > 2 and argv[1] == "run":
        i = 2
        while i < len(argv) and argv[i].startswith("-"):
            i += 2 if argv[i] in RUN_VALUE_FLAGS else 1
        return os.path.basename(argv[i]) if i < len(argv) else program
    return program


def check_make_targets(argv: list[str]) -> None:
    """`make ` is a host marker by default, so this cannot live in check_host_only."""
    if os.path.basename(argv[0]) != "make" or not argv[1:]:
        return
    for rule in RULES.warn_make:
        if argv[1] in rule.get("targets", ()):
            decide("warn", rule["id"], rule["reason"].replace("{target}", argv[1]))


def check_host_only(argv: list[str]) -> None:
    """Judged on this segment alone: a marker in another segment proves nothing about
    this one, and `make up && pytest …` once ran pytest on the host that way."""
    segment = " ".join(argv)
    if any(marker in segment for marker in RULES.host_markers):
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
    if "vitest" in " ".join(argv) and "--environment" in argv:
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


SCRIPT_RUNNERS = SHELLS | {"source", "."}


def script_run(argv: list[str]) -> str:
    """The file a segment executes: argv[0], or the file handed to a shell."""
    program = os.path.basename(argv[0])
    if program not in SCRIPT_RUNNERS:
        return program
    for arg in argv[1:]:
        if not arg.startswith("-"):
            return os.path.basename(arg)
    return program


def check_publish(argv: list[str]) -> None:
    """`git push` is refused above; a script that ends in one is the same push one
    file away, and this guard cannot read inside files."""
    if script_run(argv) == "publish.sh":
        decide(
            "deny",
            "publish-is-the-owners",
            f"`publish.sh` ends in `git push`, and publishing is {RULES.owner}'s call. Leave "
            "the clone committed and say it is ready to publish.",
        )


def check_config(error: str | None) -> None:
    if error:
        decide(
            "warn",
            "harness-config-unreadable",
            f".claude/harness.toml did not parse ({error}); this repo's own rules are OFF "
            "until it does — only the generic git and gate rules ran on this command.",
        )
    if RULES.problems:
        decide(
            "warn",
            "harness-config-invalid",
            ".claude/harness.toml has entries this guard cannot use, and dropped them: "
            + "; ".join(RULES.problems[:4])
            + ". Everything else in it ran.",
        )


def judge(payload: dict) -> None:
    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        return

    global RULES  # noqa: PLW0603 — the check_* functions read the repo rules at module scope
    config, error = repo_config.load_checked(payload.get("cwd"))
    RULES = RepoRules(config)
    check_config(error)

    code = strip_heredocs(command)
    for argv in (cmd for seg in segments(command) for cmd in unwrapped(head(seg))):
        if not argv:
            continue
        if os.path.basename(argv[0]) == "git":
            check_git(argv)
        check_make_targets(argv)
        check_host_only(argv)
        check_publish(argv)
        check_blind_gates(code, argv)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    try:
        judge(payload)
    except Exception as exc:
        decide(
            "deny",
            "guard-crashed",
            f"guard_bash.py failed on this command ({type(exc).__name__}: {exc}). A guard that "
            "crashed has judged nothing, so Bash is refused until the hook is fixed; "
            "`scripts/link-harness.sh --unlink` turns it off meanwhile.",
        )
    emit()


if __name__ == "__main__":
    main()
