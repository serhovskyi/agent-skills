# agent-skills

Personal agent skills for AI coding assistants — dev workflow tooling, starting with the
**wave** pipeline for executing multi-plan features without drowning the controller's context,
and the **harness** of hooks and evidence tools that keeps sessions sharing one working tree
honest.

Two plugins, one marketplace, installable separately:

| plugin | what it ships |
|---|---|
| `wave-skills` | `wave-prep` · `wave-run` · `wave-close`, and the two reviewer agents they dispatch |
| `wave-harness` | hooks that refuse irreversible git and warn on blind commands, plus `evidence-run`, `absence-check`, `suite-summary` |

They are independent, but they were measured together: the skills' reply contract records every
gate run through an evidence runner, and `wave-harness` ships one.

Shipped as a Claude Code **plugin**, because the skills dispatch agents and the two have to
arrive together: a skill that dispatches a reviewer nobody installed fails at the review stage,
which is the stage you least want to lose.

## Installation

**As a plugin — skills and agents together (recommended):**

```
/plugin marketplace add serhovskyi/agent-skills
/plugin install wave-skills
```

**As symlinks — if you want to edit the skills as you use them:**

```bash
git clone git@github.com:serhovskyi/agent-skills.git ~/agent-skills
bash ~/agent-skills/scripts/link-skills.sh
```

This links skills into `~/.claude/skills` and `~/.agents/skills`, and agents into
`~/.claude/agents`. Every entry is a symlink into the clone, so the installed files **are** the
repo — edit in place, publish with `scripts/publish.sh`. Pick one route or the other; running
both installs the same content twice.

**The harness, as a plugin or linked for editing:**

```
/plugin install wave-harness
```

```bash
bash ~/agent-skills/scripts/link-harness.sh     # --unlink to remove
```

`link-harness.sh` registers `harness/hooks/hooks.json` in `~/.claude/settings.json` with paths
into the clone (the first run keeps `settings.json.orig`, every run a timestamped `.bak`), and
links the three evidence tools into `~/.local/bin`. A registered hook whose file is gone — the
clone moved or deleted — exits 0 with a message that its guards are off, instead of blocking
every call. Again, one route or the other: both registers every hook twice. Restart sessions
afterwards — hooks are read at session start.

**Skills only, no agents** — for Cursor, Windsurf, OpenCode and other Agent-Skills harnesses:

```bash
npx skills@latest add serhovskyi/agent-skills
```

The `skills` CLI has no notion of agents, so this route installs the three skills alone. Supply
the reviewer agents yourself (see [Reviewer roster](#reviewer-roster) below) or the review stages
have nothing to dispatch.

## Skills

### The wave pipeline — `wave-prep` · `wave-run` · `wave-close`

A **wave** is N written sub-plans of one feature, executed one *link* per session. The three
skills are one pipeline, used in order, and they exist because of a single measured number:

> Six plans of one real wave are **3752 lines ≈ 120k tokens**. A controller that reads them
> spends its whole budget before the first dispatch — and then dies mid-wave.

So the controller never reads a plan body. Subagents do. The controller counts, probes,
dispatches, measures and records.

| skill | when | what it does |
|---|---|---|
| **`wave-prep`** | plans exist, `<wave>-WAVE.md` does not | derives link order, counts structure with a script, probes every plan against the live tree, dispatches one ≤60-line digest subagent per plan, writes the wave documents, prints the first link's start block |
| **`wave-run`** | one link, one fresh session | verifies start predicates, dispatches implementer → reviewer per task with the model named, keeps the ledger, runs the final two-lens link review |
| **`wave-close`** | a link's tasks are done | summary from the ledger, four owner questions one at a time, local merge, re-probes the next plan for drift, writes the relay and the next start block |

**Why three and not one:** `wave-close` reads the *ledger*, never the dialogue — so a link can
be closed from a fresh session when the executing one died, and the owner's decisions are never
asked by a session one message from a compaction.

Three zero-token scripts do the counting, so prose and reality cannot drift:

```bash
WP=~/.claude/skills/wave-prep
"$WP/scripts/plan-extract" docs/superpowers/plans/<wave>-<link>.md      # task table, files, forecast
"$WP/scripts/plan-probe"   docs/superpowers/plans/<wave>-{a,b,c}.md --quiet  # MOVED / DEAD / MISSING / COLLISION
"$WP/scripts/profile-probe" --quiet                                       # the repo profile vs. the tree
```

`plan-probe` catches the failure mode these skills were built around: a plan goes stale the
moment a neighbouring link lands — one link's move once killed six addresses cited by a plan two
waves away.

**Triggers:** "prepare the wave", "run link b2", "close this link", "hand over the next link"

## Requirements

The wave skills are an extension of, and a simplification of working with,
[**superpowers**' spec-driven development](https://github.com/obra/superpowers).

| requirement | why |
|---|---|
| `superpowers` plugin — `spec-driven-development` | writes the sub-plans a wave consumes, into `docs/superpowers/plans/` |
| `superpowers` plugin — `subagent-driven-development` | `wave-run` calls its `task-brief` and `review-package` scripts for the per-task machinery |
| `python3` | the three `wave-prep` scripts; **3.11+** for `wave-harness` (it reads `harness.toml` with `tomllib`) |
| **per-layer reviewer agents** (see below) | two of the four review seats ship here; the stack-specific ones are yours |
| **`.claude/wave-profile.md`** in your repo (see [below](#repo-profile)) | your commands, roster and stack traps; `wave-prep` writes it on first use |
| `wave-harness` *(optional)* | ships the evidence runner the reply contract names; without it the skills fall back to `<cmd> >> <file> 2>&1; echo "EXIT=$?" >> <file>` |

<a id="reviewer-roster"></a>

### Reviewer roster

The skills dispatch reviewers **by role**, never by hardcoded name. Record the roster once in
`WAVE.md` § Reviewers, and every link reads it from there.

**Shipped with this plugin** — both are stack-agnostic, so they work in any repo:

| agent | model | seat |
|---|---|---|
| `gate-evidence-auditor` | opus | `wave-run`, final review — second lens |
| `solution-architect-reviewer` | opus | `wave-prep` step 6 — plan review |

`gate-evidence-auditor` is the one worth having if you have only one. It reads the ledger, the
report files and the logs — **not** the diff — and answers one question per gate: *did it go red,
and for OUR reason?* Verdicts are `OURS` / `NOT OURS` / `UNPROVEN`, and it carries a twelve-class
catalogue of ways a gate stays silent (path-scoped rules, pinned equalities, discriminating pairs
true by absence, environment-green, …). It is read-only and will refuse to move the tree: a proof
that needs a checkout comes back `UNPROVEN` with the exact command for you to run.

**You supply these** — they encode your stack, so a shared copy would be worse than none:

| role | model | what it must know | dispatched by |
|---|---|---|---|
| **frontend code reviewer** | sonnet | your framework and state layer (e.g. Vue 3 + TypeScript + Pinia, or React + TS + Redux). Judges a *finished diff* from a review-package file for wire-contract, reactivity, tenancy, i18n and test-falsifiability defects. Must not crawl the tree or re-run `git diff`. | `wave-run`, per task and over the whole link |
| **backend code reviewer** | sonnet | your framework and persistence layer (e.g. FastAPI + SQLModel, or Django + ORM). Same contract, judging correctness, authorization and persistence. | `wave-run`, per task and over the whole link |
| **frontend plan reviewer** | opus | the same stack, but reviewing a *written plan* before any code exists — what will break, judged against the target architecture rather than the legacy tree. | `wave-prep` step 6 |
| **backend plan reviewer** | opus | ditto for the backend stack. | `wave-prep` step 6 |
| **devops reviewer** *(optional)* | opus | your deploy, CI and migration shape — reversible migrations, table locks, backfills, workflow files. | `wave-prep` step 6, when a plan touches infra |

Four properties make these work, and are worth copying from the two shipped agents:

1. **Read-only.** `tools: Read, Grep, Glob, Bash`, no writes, and never `make`/tests/migrations —
   the owner runs those.
2. **The diff arrives as a file.** The review-package path is in the prompt; reading the tree
   instead is what blows the context these skills exist to protect.
3. **No scope creep.** Surface defects; never request comments, coverage percentages, or
   gold-plating.
4. **Falsifiability over coverage.** Ask whether a test would go red without the behavior — not
   how many lines it touched.

Vertical tasks get **both** code reviewers on the same diff file: two lenses, one package.

<a id="repo-profile"></a>

### The repo profile — what your project adds

The skills name no toolchain. Everything they would otherwise have to guess about your repo
lives in **one tracked file, `.claude/wave-profile.md`**, and the skills cite it section by
section (`profile § Suites`, `profile § Reply contract`, …). `wave-prep` asks for the values
and writes it the first time; after that every wave reads it, and only a lesson about your
stack goes back into it. The template, with every section name the skills look up, is
[`skills/wave-prep/references/profile.md`](skills/wave-prep/references/profile.md).
A filled-in one for an invented Django + React repo is
[`profile-example.md`](skills/wave-prep/references/profile-example.md) — copy its shape, not its
values.

| section | what it holds | example of the shape |
|---|---|---|
| **Suites** | one row per suite: the exact command, the summary lines to record, the paths whose tree hash moves it | `npm test` · `Tests`, `Test Files`, `failed` · `HEAD:web` |
| **Generated mirrors** | tracked files a tool rewrites; `wave-run` checks they are clean at preflight | `api/openapi.json`, `package-lock.json`, or `none` |
| **Reviewers** | the plan, code and evidence rosters — which agent reviews which layer | `src/server/` → your backend code reviewer |
| **Evidence tooling** | the command that records a run with its own `EXIT=`, and an absence check whose exit is the verdict | `scripts/evidence-run <file> <cmd…>`, or `none` for the built-in fallback |
| **Reply contract** | lines added verbatim to every implementer dispatch: your linters and type-check, how your test runner selects one spec | `Before every commit run <evidence runner> <file> eslint --max-warnings 0 <files>` |
| **Run notes** | traps of your stack that make a run read green while running nothing | "a `-t` filter is a regex: escape `()`" |
| **Gate roster** | the commands that list every lint/guard/ratchet file, handed whole to the judgment subagents | `ls tests/lint/` · `cat .importlinter` |
| **Prep checks** | checks `wave-prep` runs against every plan beyond the generic ones | "route names resolve to a leaf in the router" |
| **Adaptations** | repo rules every WAVE carries | "no worktree: work on a branch in place", "the tree is shared" |
| **Rules for every link** | rules appended to the WAVE's numbered list | a gate that never counts as moved, and why |
| **Close report** | the lint, boundary, type-check and CI commands the link report names | `npm run lint` · `tsc --noEmit` · `make ci` |

Four properties keep a profile useful:

1. **Commands, not descriptions.** A line an implementer copies must run as written.
2. **Every rule carries its reason.** One paragraph under the block: which failure it exists
   because of, measured. A rule without one gets dropped by the first person who finds it odd.
3. **`none` is a value.** An empty section reads as "not filled in"; `none` reads as "checked".
4. **Addresses from the repo root.** `profile-probe` re-finds every path, `HEAD:` key, agent,
   make target and npm script the profile names, at every `wave-prep` and every link close —
   so an architectural move turns the profile red at the close of the link that made it, and
   that link updates it. A path written relative to a subdirectory reads as moved.

The plans directory is `docs/superpowers/plans/` by default, the superpowers convention.

The wave registry lives at `.superpowers/sdd/<wave>/wave.md` **because that path is gitignored**.
Wave state must survive the `git switch` between link branches; a tracked registry travels with
the branch and lies the moment a link merges.

## Harness

Hooks for Claude Code sessions that share one working tree — several sessions, one index, one
stash stack. Each rule encodes a loss that already happened.

| hook | event | what it does |
|---|---|---|
| `guard_bash.py` | PreToolUse/Bash | **refuses** irreversible git: `push`, `reset --hard`, `clean -f`, `checkout --`, `checkout -f`, `switch --discard-changes`, `restore` (unless `--staged` alone), any `stash` that moves the shared stack, `branch -D`, history rewrites, blanket `add`, `commit -a`; and `pkill -f`, which matches its own shell. **Warns** on commands that answer truthfully and mean something else: `git grep` blind to untracked files, a pathspec resolved against a stale cwd, `git add <dir>` silently skipping ignored files, a commit of the whole shared index, `pgrep -f`, a headless `--window-size` that does not give that viewport. It judges every command the typed line will run: each line, each side of `;`/`&&`/`\|`, subshells and `$( )`, loop and `if` bodies, the argument of `time`/`timeout`/`env`/`sudo`/`nohup`/`xargs`, the string of `bash -c`/`sh -c`/`eval`, and the program behind `npx`, `python -m`, `uv run`, `poetry run` |
| `warn_pipefail.py` | PostToolUse/Bash | a test run piped into `tail` reports the pager's exit code |
| `session_state.py` | SessionStart | the tree's measured branch, HEAD and dirt, before any handoff note's claims |
| `stop_dirty.py` | Stop | staged and untracked counts when a turn ends |

Refusals are only for irreversible loss; everything routine (commit, merge, switch) runs
unprompted. A warning never states a permission decision, so it can never answer a prompt the
user was entitled to see.

**Evidence tools** — what the wave skills' reply contract runs gates through:

| tool | does |
|---|---|
| `evidence-run <file> <cmd…>` | appends the command line, its output (test-runner noise trimmed, full log kept beside it) and an `EXIT=` printed by its own shell to `<file>`; without a command it is a usage error |
| `absence-check --rev R --base B --pattern ERE [--allow path:n]… -- paths` | "the pattern is gone at R": reads revisions, never the working tree, and refuses a base where the pattern never hit |
| `suite-summary <log>` | the last run's summary lines and its `EXIT=` (an appended log holds several), refusing a run that has none |

### The repo's harness config — `.claude/harness.toml`

The hooks know git and shells; they cannot know your stack. What only your repo knows goes in
one optional file, and a repo without it keeps the generic rules alone. A filled-in example for
an invented repo is [`harness/harness.example.toml`](harness/harness.example.toml).

| section | holds | example |
|---|---|---|
| `[harness]` | `owner` — who runs what the guard refuses | `owner = "the maintainer"` |
| `[guard_bash.host_only]` | programs refused outside a container, and what to run instead | `pytest = "make test-api"` |
| `[guard_bash.host_only_npm]` | npm scripts refused on the host | `test = "make test-web"` |
| `[guard_bash]` `host_markers` | what makes a command count as containerised | `["docker compose exec", "make "]` |
| `[[guard_bash.warn_make]]` | make targets worth a warning, with an `id` and a `reason` | a local `make ci` that CI never runs |
| `[[guard_bash.warn_program]]` | programs worth a warning wherever they run | `npx prettier` in a repo formatted by eslint |
| `[session_state]` | `memory_budget` in bytes for the project's MEMORY.md, and a `memory_hint`; `warn_on_default_branch = false` silences the on-default-branch warning | `memory_budget = 6144` |
| `[warn_pipefail]` / `[evidence]` | `runners` — your own runner commands beyond pytest/vitest/jest/… | `runners = ["make test-api"]` |

Every rule you add carries its reason in the `reason` string: the warning is the only place the
next session reads it.

**What the guard cannot see.** `guard_bash` reads the command the agent typed, down to the
string a `bash -c` carries — but not the commands a script *file* or an interpreter one-liner
will run. `bash scripts/publish.sh` is one command to it, so the `git push` inside is not
refused; neither is a `git stash` inside a Makefile target, nor `subprocess.run(["git",
"push"])` in a `python3 -c`. Put a script whose inner commands must stay the owner's behind
your own rule (`[[guard_bash.warn_program]]` warns; a refusal is a deny rule added to
`guard_bash.py`).

**The guard fails closed, the config fails soft.** A `harness.toml` that does not parse, or an
entry of the wrong type, is reported once per command as a warning and that entry is dropped —
the generic rules keep running, and a repo cannot switch them off through its config. A hook
that crashes refuses the command instead, naming the exception: a crashed guard has judged
nothing, and the harness would otherwise read its exit as "no verdict".

## Structure

```
.claude-plugin/
├── plugin.json                     # the plugin manifest
└── marketplace.json                # lets the repo be added as a marketplace
agents/
├── gate-evidence-auditor.md        # evidence, not code — the second review lens
└── solution-architect-reviewer.md  # plan review, before any code exists
Makefile                            # make test · make lint
harness/
├── .claude-plugin/plugin.json      # the wave-harness plugin
├── hooks/                          # hooks.json + the four hooks, repo_config.py reads harness.toml
├── bin/                            # evidence-run, absence-check, suite-summary
├── tests/                          # pytest; CI runs it (.github/workflows/test.yml)
└── harness.example.toml            # .claude/harness.toml for an invented repo
scripts/
├── link-skills.sh                  # skills + agents, symlinked for editing
├── link-harness.sh                 # hooks + tools, registered for editing
└── publish.sh
skills/
├── wave-prep/
│   ├── SKILL.md
│   ├── references/templates.md     # WAVE.md, LINK-PROMPT, registry
│   ├── references/profile.md       # .claude/wave-profile.md — your repo's half
│   ├── references/profile-example.md  # the same, filled in for an invented repo
│   └── scripts/
│       ├── plan-extract            # countable structure of a plan
│       ├── plan-probe              # plan vs. the live tree
│       └── profile-probe           # repo profile vs. the live tree
├── wave-run/
│   └── SKILL.md
└── wave-close/
    ├── SKILL.md
    └── references/templates.md     # link report, relay, post-wave prompt
```

`agents/` and `skills/` are discovered by convention, so the manifest names no paths. Both are
flat: skill names must be unique, since `link-skills.sh` links by basename and the plugin loader
expects `skills/<name>/SKILL.md`.

## Updating a skill

**Recommended setup:** clone this repo to a permanent location and run `link-skills.sh` once.
After that, `~/.claude/skills/<name>` is a symlink into this repo — editing the skill file in
place *is* editing the repo. Publishing is a single command.

```bash
# One-time setup
git clone git@github.com:serhovskyi/agent-skills.git ~/agent-skills
bash ~/agent-skills/scripts/link-skills.sh
```

Now `~/.claude/skills/wave-prep/SKILL.md` points directly into
`~/agent-skills/skills/wave-prep/SKILL.md`, and `~/.claude/agents/gate-evidence-auditor.md` into
`~/agent-skills/agents/`. Edit either however you like, then publish:

```bash
bash ~/agent-skills/scripts/publish.sh "wave-run: name the mirror check per repo"
```

That's it — no copying, no separate commit step.

**A project-level copy wins over the link.** Claude Code prefers `<repo>/.claude/skills/<name>`
and `<repo>/.claude/agents/<name>.md` over the user-level ones, so a repo that still carries its
own copy of a wave skill or a shipped agent silently runs that copy, and your edits land in the
wrong file. Delete the repo's copies when you switch to the link; what was repo-specific in them
belongs in its `.claude/wave-profile.md`.

---

**Without the symlink setup** (e.g. you installed via `npx skills@latest add`), copy and push
manually:

```bash
cp ~/.claude/skills/wave-prep/SKILL.md ~/agent-skills/skills/wave-prep/SKILL.md
bash ~/agent-skills/scripts/publish.sh "update wave-prep"
```

**A publish denylist keeps private projects out** — see
[Developing inside a private project](#private-project) below.

`publish.sh` stages `skills/`, `agents/`, `harness/`, `scripts/`, `.claude-plugin/`, `.github/`
and `README.md`, so every edit travels with the skill edits.

Plugin users update with `/plugin update wave-skills` (and `wave-harness`); `npx skills@latest add` users re-run the
install. Users who cloned manually just need `git pull` — the symlinks already point into the
clone, so no relinking is needed. Bump `version` in `.claude-plugin/plugin.json` when the plugin
changes meaningfully.

### Adding a new skill

1. Write the skill at `~/.claude/skills/<skill-name>/SKILL.md`, starting with the required
   frontmatter:
   ```yaml
   ---
   name: skill-name
   description: One-line description of when and why to invoke this skill.
   ---
   ```
2. Create it in the repo (or move it there, then re-link):
   ```bash
   mkdir -p ~/agent-skills/skills/<skill-name>
   cp ~/.claude/skills/<skill-name>/SKILL.md ~/agent-skills/skills/<skill-name>/SKILL.md
   bash ~/agent-skills/scripts/link-skills.sh
   ```
3. Publish:
   ```bash
   bash ~/agent-skills/scripts/publish.sh "add <skill-name> skill"
   ```

The `skills` CLI discovers any `SKILL.md` under `skills/` automatically — no registration step.
Skill names must stay unique: `link-skills.sh` links by basename.

### Adding a new agent

Drop a `<name>.md` into `agents/` with the frontmatter below, then re-run `link-skills.sh`.
Nothing registers it — `agents/` is discovered by convention.

```yaml
---
name: agent-name
description: What it reviews, what it does NOT review, and when to dispatch it.
tools: Read, Grep, Glob, Bash
model: opus
---
```

The `description` is what makes an agent dispatchable: state the seat it fills and the seats it
does not, so a controller picking reviewers can tell them apart. Keep shared agents free of
stack and repo specifics — an agent that names your framework belongs in your repo's
`.claude/agents/`, not here.

## Updating the harness

`link-harness.sh` points the registered hooks and the three tools into the clone, so editing
`harness/hooks/*.py` or `harness/bin/*` is live in the next session (hooks are read at session
start). Run the suite before publishing — it is what CI runs:

```bash
cd ~/agent-skills && make test                      # ARGS="harness/tests/test_publish.py" narrows it
```

Adding a rule to `guard_bash.py`:

1. **Decide the verdict.** `deny` is only for irreversible loss; a command that answers truthfully
   and means something else is a `warn`. A warning never states a permission decision —
   `test_the_warn_channel_cannot_answer_a_permission_prompt` holds that line.
2. **Give it a stable id**: `decide("warn", "<rule-id>", "<reason with the loss it prevents>")`.
3. **Witness it.** A case in `tests/test_hook_rules.py` that runs the hook on a payload and reads
   the verdict, with `rule: <rule-id>` in its docstring. `test_hooks_are_armed.py` compares the ids
   fired to the ids witnessed in both directions, so a rule without a witness — or a witness of a
   rule that is gone — is red.
4. **A new refusal moves a pin.** The deny count is pinned (`test_the_refusals_are_still_refusals`);
   raise it in the same commit, deliberately.
5. **A rule only your repo needs is config, not code** — `harness.toml`, above.

<a id="private-project"></a>

## Developing inside a private project

These skills were grown inside a private codebase, and that is the normal way to keep them
sharp: the lessons come from real links. It is also how a private project leaks into this
public repo — an agent fixing a skill from inside that project writes the fix in that project's
words: its commands, test names, shas, recorded output. Three things on the project's side keep
the two apart. As with the reviewer roster, they encode your project, so a shared copy would
be worse than none:

| what | where | what it does |
|---|---|---|
| **publish denylist** | `.git/info/publish-denylist` of your clone (never committed, so never cloned) | the project's names, paths and identifiers, one per line; `publish.sh` refuses, leaving the index as it was, when one is in the added lines, file names or binaries of the staged diff or of any unpushed commit, or in a commit message. It refuses without the file: `touch` it if there is nothing to keep out |
| **one line in the project's `CLAUDE.md`** | the project | "the wave skills and generic hooks live in `<clone>` (linked): edit there, generic words only; this repo's facts go to `.claude/wave-profile.md` / `.claude/harness.toml`" |
| **a write guard** | the project's own PreToolUse `Write\|Edit` hook | refuses a write to `.claude/skills/<published skill>/`, `.claude/agents/<published agent>.md` or `.claude/hooks/<published hook>.py` in the project (it would shadow the link); refuses an edit into the clone that carries a denylisted word; warns on any other edit into the clone that the text is about to be public |

Resolve the path with `realpath` before judging it: `~/.claude/skills/<name>/SKILL.md` *is* the
clone once linked. List the published names from the clone at call time, never from a frozen
list. And when the project keeps a map of its own harness, an entry under `.claude/` that the
map does not name is worth a red test of its own: it catches a shadow copy at the next run even
when no guard saw it written.

