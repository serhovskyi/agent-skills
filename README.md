# waveflow

**Wave Development Flow: ship a big feature as a wave — one grilled slice, one spec, N plans,
one link per session.** Two Claude Code plugins: the **wave** pipeline that executes a
multi-plan feature without drowning the controller's context, and the **harness** of hooks and
evidence tools that keeps sessions sharing one working tree honest.

Two plugins, one marketplace, installable separately:

| plugin | what it ships |
|---|---|
| `wave-skills` | `wave-grill` before the wave, `wave-prep` · `wave-run` · `wave-close` for it, `wave-retro` after it, and the four reviewer agents they dispatch |
| `wave-harness` | hooks that refuse irreversible git and warn on blind commands, plus `evidence-run`, `absence-check`, `suite-summary` |

They are independent, but they were measured together: the skills' reply contract records every
gate run through an evidence runner, and `wave-harness` ships one.

Shipped as Claude Code **plugins**, because the skills dispatch agents and the two have to
arrive together: a skill that dispatches a reviewer nobody installed fails at the review stage,
which is the stage you least want to lose.

## Contents

- [Installation](#installation)
- [From feature to wave](#from-feature-to-wave)
- [The wave pipeline](#the-wave-pipeline)
  - [Requirements](#requirements)
  - [Reviewer roster](#reviewer-roster)
  - [The repo profile](#repo-profile)
- [The harness](#the-harness)
  - [Hooks](#hooks)
  - [Evidence tools](#evidence-tools)
  - [The repo's harness config](#harness-config)
  - [What the guard cannot see](#guard-limits)
  - [Tests](#tests)
- [Repository layout](#repository-layout)
- [Development](#development)
  - [Editing and publishing](#editing-and-publishing)
  - [Adding a skill](#adding-a-skill)
  - [Adding an agent](#adding-an-agent)
  - [Changing the harness](#changing-the-harness)
  - [Developing inside a private project](#private-project)
- [Credits](#credits)

## Installation

Pick **one route per component**. Running two routes installs the same content twice — the
plugin and the symlinks, or the plugin and the hook registration.

**Only the plugin and symlink routes install the reviewer agents.** `npx skills add` installs
skills alone — see [Skills only, no agents](#skills-only-no-agents) for what that leaves out.

### As plugins (recommended)

Skills and agents together, and the harness beside them:

```
/plugin marketplace add serhovskyi/waveflow
/plugin install wave-skills
/plugin install wave-harness
```

Update later with `/plugin update wave-skills` (and `wave-harness`).

### As symlinks, to edit the skills as you use them

```bash
git clone git@github.com:serhovskyi/waveflow.git ~/waveflow
bash ~/waveflow/scripts/link-skills.sh
bash ~/waveflow/scripts/link-harness.sh     # --unlink to remove
```

`link-skills.sh` links skills into `~/.claude/skills` and `~/.agents/skills`, and agents into
`~/.claude/agents`. Every entry is a symlink into the clone, so the installed files **are** the
repo — edit in place, publish with `scripts/publish.sh` (see
[Editing and publishing](#editing-and-publishing)).

`link-harness.sh` registers `harness/hooks/hooks.json` in `~/.claude/settings.json` with paths
into the clone (the first run keeps `settings.json.orig`, every run a timestamped `.bak`), and
links the three evidence tools into `~/.local/bin`. A registered hook whose file is gone — the
clone moved or deleted — exits 0 with a message that its guards are off, instead of blocking
every call. Restart sessions afterwards: hooks are read at session start.

Updating is `git pull` in the clone — the symlinks already point into it, so no relinking is
needed.

### Skills only, no agents

For Cursor, Windsurf, OpenCode and other Agent-Skills harnesses:

```bash
npx skills@latest add serhovskyi/waveflow
```

> **This route installs no agents.** The `skills` CLI has no notion of agents, so you get the
> five skills and none of the four reviewers they dispatch. Without them:
>
> | missing agent | what stops working |
> |---|---|
> | `gate-evidence-auditor` | `wave-run`'s per-task gate audit and the final review's evidence lens |
> | `solution-architect-reviewer` | `wave-prep` step 6, the plan review |
> | `spec-reviewer` | the final review's spec lens |
> | `standards-reviewer` | the code review of any layer that has no reviewer of your own |
>
> Copy them from [`agents/`](agents/) into your harness's agent directory, or supply your own
> for each role (see [Reviewer roster](#reviewer-roster)), before the first wave — a review
> stage with nothing to dispatch is the stage you least want to lose.

Installed skills do not update themselves: the CLI copies the files, so re-run the install to
update.

## From feature to wave

The wave skills start where the plans end, and the steps before them decide most of the
outcome. The whole flow, in order:

1. **Cut a slice.** A wave is one decomposed part of a big feature, never the feature whole:
   a part with its own precondition, its own done-state and its own gates. A feature too big
   to grill in one sitting is too big for one wave; cut it first, then grill the first slice.
2. **Grill the slice** — `/wave-grill`. An interview in rounds: each round asks every
   question whose prerequisites are settled, numbered, each with a recommended answer, and
   anything the repo can answer is explored by a subagent instead of asked. The first round
   checks the slice is one slice (precondition, done-state, gates); every behaviour gets a
   "what goes red without it?" question. Decisions go into
   `docs/superpowers/specs/YYYY-MM-DD-<topic>-decisions.md` after every round, terms into
   `GLOSSARY.md`, the rare hard-to-reverse trade-off into `docs/adr/`. It ends when every
   branch of the decision tree is resolved — reversed decisions mid-wave are what this step
   exists to prevent.
3. **Spec it** — spec-driven development. The grilled decisions become one design spec,
   `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, committed. The spec is what the
   plans, the reviewers and the wave-close questions are measured against.
4. **Plan it, one sub-plan per link.** `superpowers:writing-plans` writes the plans into
   `docs/superpowers/plans/<wave>-<link>.md`, one file per link, sharing a stem. Each plan
   states the link it depends on: `wave-prep` derives the link order from those preconditions,
   never from the alphabet. A wide mechanical change that cannot land green as one link
   (a renamed column, a retyped shared symbol) is planned **expand–contract**: add the new
   form beside the old, migrate callers in batches, one link each, then delete the old form.
5. **Then the wave:** `wave-prep` once, `wave-run` and `wave-close` once per link, each link
   in a fresh session.
6. **Retro, when it went badly** — `/wave-retro` reads the closed wave's records and proposes
   changes to the agents' environment — checks, pointers, reviewer rules, the repo profile —
   for the owner to pick from.

The pipeline below consumes step 4. It does not grill, spec or plan — a wave prepared from an
ungrilled slice runs fine and ships the wrong thing.

`wave-grill` and `wave-retro` run only when you invoke them: a grill needs the owner at the
keyboard, and a retro is the owner's call.

## The wave pipeline

`wave-prep` · `wave-run` · `wave-close`

A **wave** is N written sub-plans of one feature, executed one *link* per session. The three
skills are one pipeline, used in order, and they exist because of a single measured number:

> Six plans of one real wave are **3752 lines ≈ 120k tokens**. A controller that reads them
> spends its whole budget before the first dispatch — and then dies mid-wave.

So the controller never reads a plan body. Subagents do. The controller counts, probes,
dispatches, measures and records.

| skill | when | what it does |
|---|---|---|
| **`wave-prep`** | plans exist, `<wave>-WAVE.md` does not | derives link order, counts structure with a script, probes every plan against the live tree, dispatches one ≤60-line digest subagent per plan, writes the wave documents, prints the first link's start block |
| **`wave-run`** | one link, one fresh session | verifies start predicates, dispatches implementer → reviewer per task with the model named, keeps the ledger, runs the final link review — code, evidence, and the spec when the roster names a spec reviewer |
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

### Requirements

The wave skills do not work without [**superpowers**](https://github.com/obra/superpowers):
a wave is the sub-plans its spec-driven development writes, and `wave-run` runs each task
through its subagent-driven-development scripts.

| requirement | why |
|---|---|
| `superpowers` plugin — `brainstorming`, `writing-plans` | spec-driven development: the spec a wave implements (`docs/superpowers/specs/`) and the sub-plans it consumes (`docs/superpowers/plans/`), see [From feature to wave](#from-feature-to-wave) |
| `superpowers` plugin — `subagent-driven-development` | `wave-run` calls its `task-brief` and `review-package` scripts for the per-task machinery |
| `python3` | the three `wave-prep` scripts; **3.11+** for `wave-harness` (it reads `harness.toml` with `tomllib`) |
| **your project's reviewer agents** — a frontend and a backend *code* reviewer, a frontend and a backend *plan* reviewer, optionally a devops reviewer (see [Reviewer roster](#reviewer-roster)) | they encode your stack, so they live in your repo's `.claude/agents/`, not here; the four stack-agnostic seats (`gate-evidence-auditor`, `solution-architect-reviewer`, `spec-reviewer`, `standards-reviewer`) ship with the plugin |
| **`.claude/wave-profile.md`** in your repo (see [below](#repo-profile)) | your commands, roster and stack traps; `wave-prep` writes it on first use |
| `wave-harness` *(optional)* | ships the evidence runner the reply contract names; without it the skills fall back to `<cmd> >> <file> 2>&1; echo "EXIT=$?" >> <file>` |

<a id="reviewer-roster"></a>

### Reviewer roster

The skills dispatch reviewers **by role**, never by hardcoded name. Record the roster once in
`WAVE.md` § Reviewers, and every link reads it from there.

**Shipped with this plugin** — all four are stack-agnostic, so they work in any repo:

| agent | model | seat |
|---|---|---|
| `gate-evidence-auditor` | opus | `wave-run`, final review — second lens |
| `solution-architect-reviewer` | opus | `wave-prep` step 6 — plan review |
| `spec-reviewer` | opus | `wave-run`, final review — the spec lens, when the roster names it |
| `standards-reviewer` | sonnet | `wave-run`, per task and final — the code reviewer of a layer that has none of its own |

`gate-evidence-auditor` is the one worth having if you have only one. It reads the ledger, the
report files and the logs — **not** the diff — and answers one question per gate: *did it go red,
and for OUR reason?* Verdicts are `OURS` / `NOT OURS` / `UNPROVEN`, and it carries a twelve-class
catalogue of ways a gate stays silent (path-scoped rules, pinned equalities, discriminating pairs
true by absence, environment-green, …). It is read-only and will refuse to move the tree: a proof
that needs a checkout comes back `UNPROVEN` with the exact command for you to run.

`spec-reviewer` judges the whole link's diff against the design spec, scoped to the part of the
spec the link's plan owns: what is missing or wrong, what nobody asked for, and where the plan
itself departs from the spec — each with the spec line quoted. `standards-reviewer` judges a diff
against the repo's documented standards plus a fixed baseline of twelve code smells, the smells
always as judgement calls the repo's own standards override. Its findings and the spec lens's are
reported side by side, never merged or ranked against each other: code can follow every standard
and build the wrong thing, or build the right thing against every convention.

**You supply these** — they encode your stack, so a shared copy would be worse than none:

| role | model | what it must know | dispatched by |
|---|---|---|---|
| **frontend code reviewer** | sonnet | your framework and state layer (e.g. Vue 3 + TypeScript + Pinia, or React + TS + Redux). Judges a *finished diff* from a review-package file for wire-contract, reactivity, tenancy, i18n and test-falsifiability defects. Must not crawl the tree or re-run `git diff`. | `wave-run`, per task and over the whole link |
| **backend code reviewer** | sonnet | your framework and persistence layer (e.g. FastAPI + SQLModel, or Django + ORM). Same contract, judging correctness, authorization and persistence. | `wave-run`, per task and over the whole link |
| **frontend plan reviewer** | opus | the same stack, but reviewing a *written plan* before any code exists — what will break, judged against the target architecture rather than the legacy tree. | `wave-prep` step 6 |
| **backend plan reviewer** | opus | ditto for the backend stack. | `wave-prep` step 6 |
| **devops reviewer** *(optional)* | opus | your deploy, CI and migration shape — reversible migrations, table locks, backfills, workflow files. | `wave-prep` step 6, when a plan touches infra |

Four properties make these work, and are worth copying from the shipped agents:

1. **Read-only.** `tools: Read, Grep, Glob, Bash`, no writes, and never `make`/tests/migrations —
   the owner runs those.
2. **The diff arrives as a file.** The review-package path is in the prompt; reading the tree
   instead is what blows the context these skills exist to protect.
3. **No scope creep.** Surface defects; never request comments, coverage percentages, or
   gold-plating.
4. **Falsifiability over coverage.** Ask whether a test would go red without the behavior — not
   how many lines it touched.

Vertical tasks get **both** code reviewers on the same diff file: two lenses, one package.

The roster is open by layer, not fixed at these five. Profile § Reviewers is one row per
layer (`api/` → agent, `web/` → agent, `infra/` → agent, …), and every stage reads it by
path: a task gets the reviewer of each layer it touched, the final link review gets every
reviewer whose layer the link touched. A repo with five layers lists five code reviewers.
Beyond the evidence-auditor and spec-reviewer rows, it does not carry a second lens on the
*same* layer — a security or accessibility reviewer has no path of its own, so its concerns
belong in the layer reviewer's description.

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

## The harness

`wave-harness` is the second plugin: four hooks and three command-line tools for Claude Code
sessions that share one working tree — several sessions, one index, one stash stack, one
`cwd` that persists between calls. It knows git and shells; what only your repo knows comes
from an optional `.claude/harness.toml`. Each rule encodes a loss that already happened in a
real codebase, not a style preference, and every rule carries a stable id with a test that
goes red without it. It needs **Python 3.11+** (it reads the config with `tomllib`) and
nothing else.

The wave skills do not require it, but they were measured with it: the reply contract they
hand every implementer records each gate run through `evidence-run`, and without the plugin
the skills fall back to a bare `<cmd> >> <file> 2>&1; echo "EXIT=$?" >> <file>`.

### Hooks

| hook | event | what it does |
|---|---|---|
| `guard_bash.py` | PreToolUse/Bash | judges the command before it runs: **refuses** irreversible loss, **warns** on commands that answer truthfully and mean something else — the two tables below |
| `warn_pipefail.py` | PostToolUse/Bash | a test runner piped into `tail`, `head`, `grep`, `wc`, … reports the pager's exit code: `pytest … \| tail -5` exits 0 on a red suite, and that has been read as a pass. The note arrives on the command that caused it, not in review. Knows pytest, vitest, jest, playwright, `npm test`, `make test`, `make ci`, `go test`, `cargo test`, mypy, ruff; `[warn_pipefail] runners` adds yours |
| `session_state.py` | SessionStart | prints the tree as **measured now** — branch, HEAD, tracked and untracked counts, ahead/behind the default branch — before any handoff note's claims. Warns on a detached HEAD or a HEAD on the default branch, notes how many untracked paths `git grep` cannot see, and warns when the project's always-loaded `MEMORY.md` is over its byte budget |
| `stop_dirty.py` | Stop | staged and untracked counts when a turn ends, so nothing is left behind unnamed |

**Two verdicts, and the line between them is the owner's.** A *refusal* is only for
irreversible loss: commit, merge, rebase and branch switching are routine and run
unprompted, because a prompt on each one was ruled out as friction. A *warning* is for a
command that answers truthfully and means something else — a count blind to untracked
files, a viewport narrower than it claims, a gate that runs nowhere. Blindness is not loss,
so it never blocks; it arrives beside the command that caused it, the only moment it is
useful.

**How a verdict reaches the session.** A refusal is a `permissionDecision: deny` with the
first rule's reason. A warning is the reasons, one paragraph per rule id, as
`additionalContext` beside the command — it states **no** permission decision at all, so it
can never answer a prompt the user was entitled to see; a test holds that line. The guard
judges every command the typed line will run: each line, each side of `;`/`&&`/`|`,
subshells and `$( )`, loop and `if` bodies, the argument of
`time`/`timeout`/`env`/`sudo`/`nohup`/`xargs`, the string of `bash -c`/`sh -c`/`eval`, and
the program behind `npx`, `python -m`, `uv run`, `poetry run`. Heredoc bodies are stripped
first, so a `git push` quoted inside a file you write is not a push.

**What `guard_bash` refuses** — the push, the throw-away, the shared stack, the blanket:

| rule id | command | why |
|---|---|---|
| `git-push` | `git push` | the push is the owner's; `publish.sh` carries the one that belongs to this repo |
| `git-reset-hard` · `git-clean-force` · `git-checkout-force` · `git-switch-discard` | `reset --hard`, `clean -f`, `checkout -f`, `switch --discard-changes` | throw away local changes, possibly a neighbouring session's, to reach the target |
| `git-checkout-worktree` · `git-restore` | `checkout -- <path>`, `restore` (unless `--staged` alone) | overwrite the worktree copy; `checkout --` has already erased an uncommitted fix once. Commit your own paths instead: `git commit -- <paths>` |
| `git-stash-shared-stack` · `git-stash-destructive` | any `stash` that moves the stack; `stash drop/clear` | the stash stack belongs to the repository, shared by every parallel session: a neighbour's push renumbers yours and a pop applies theirs. `stash list/show` are fine |
| `git-branch-force-delete` | `branch -D` | unmerged work gone with it |
| `git-history-rewrite` | `filter-branch`, `filter-repo` | rewrites history others have built on. `rebase`, `merge` and `commit --amend` are routine and run unprompted |
| `git-add-blanket` · `git-commit-all` | `add -A`/`.`/`-u`, `commit -a` | swallow a neighbouring session's staged files — that has already happened |
| `publish-is-the-owners` | `publish.sh` run by any path or shell | the push inside it is the owner's |
| `pkill-f-self-match` | `pkill -f <pattern>` | the pattern matches the shell running it |
| `vitest-environment-flag` | `vitest --environment …` | does not override vitest `projects`: the run silently keeps the project's own environment. Use `--project` |
| `host-only-runner` · `host-only-npm-script` | programs and npm scripts your `harness.toml` names | a runner that must run inside the container; the refusal names what to run instead |
| `guard-crashed` | anything, when the hook itself raised | a crashed guard has judged nothing; the refusal names the exception and the `--unlink` that turns it off meanwhile |

**What it warns on** — answers that are true and mean something else:

| rule id | command | the blind spot |
|---|---|---|
| `git-grep-untracked-blind` | `git grep` without `--untracked` | searches the index and tracked files only; a file written this session does not exist for it, so the count comes back unchanged with exit 0 |
| `git-log-pathspec-cwd` | `git log`/`diff`/… with a relative pathspec | a pathspec resolves against the cwd, which this harness keeps between calls: one `cd frontend/` ten calls ago makes an empty result read as "never committed". Prefix `:/` |
| `git-add-directory` | `git add <dir>` | skips `.gitignore`d files silently with exit 0; nine mutation logs went in this way and one landed, because `.gitignore` holds `*.log` |
| `git-commit-whole-index` | `git commit -m …` without `-- <paths>` | commits the whole shared index, including a neighbour's staged rename |
| `pgrep-f-self-match` | `pgrep -f` | matches its own shell |
| `headless-window-size` | a headless browser with a narrow `--window-size` | the window has a minimum width, the page renders wider and the screenshot is cropped: a false positive and a false negative at once. Measure inside the page |
| your `warn_make` / `warn_program` ids | make targets and programs your `harness.toml` names | the `reason` string you wrote |
| `harness-config-unreadable` · `harness-config-invalid` | any command, once | the repo's `harness.toml` did not parse, or an entry was dropped — the generic rules still ran |

### Evidence tools

What the wave skills' reply contract runs gates through. `link-harness.sh` links them into
`~/.local/bin`; the plugin ships them under its own `bin/`.

| tool | does | exit |
|---|---|---|
| `evidence-run <file> <cmd…>` | appends to `<file>` the command line, its output and an `EXIT=<n>` printed by its own shell. The whole output goes to `<file>.raw.log` beside it; what lands in `<file>` is filtered — test-runner noise and long tracebacks trimmed, `git`/`diff`/`grep`/`cat`/`ls` output kept verbatim. If the filter itself fails, the raw output goes in whole with a line saying so. Without a command it is a usage error | the command's own |
| `absence-check --rev R --base B --pattern ERE [--allow path:n]… -- paths` | proves "the pattern is gone at R": greps the revisions, never the working tree, and refuses a base where the pattern never hit — a check that was always green proves nothing | `0` gone at R · `1` hits remain · `2` invalid check · `3` no hit at base |
| `suite-summary <log>` | the last run's summary lines and its `EXIT=` from an evidence log (an appended log holds several runs); refuses a log with no run in it | `0` found · non-zero otherwise |

The `EXIT=` line is the point: a runner's output can be green and its exit red, or the
reverse, and only the shell that ran it knows. `[evidence] runners` in `harness.toml` tells
the filter which of your own commands to treat as test runners.

<a id="harness-config"></a>

### The repo's harness config — `.claude/harness.toml`

The hooks know git and shells; they cannot know your stack. What only your repo knows goes in
one optional file, and a repo without it keeps the generic rules alone. A filled-in example for
an invented Django + React repo where every dev command runs inside Docker Compose is
[`harness/harness.example.toml`](harness/harness.example.toml).

| section | holds | example |
|---|---|---|
| `[harness]` | `owner` — who runs what the guard refuses ("ask `<owner>` to run it") | `owner = "the maintainer"` |
| `[guard_bash]` `host_markers` | what makes a command count as containerised, so `host_only` does not apply | `["docker compose exec", "make "]` |
| `[guard_bash.host_only]` | programs refused on the host, each with what to run instead | `pytest = "make test-api"` |
| `[guard_bash.host_only_npm]` | npm scripts refused on the host | `test = "make test-web"` |
| `[[guard_bash.warn_make]]` | make targets worth a warning, with an `id` and a `reason` (`{target}` is substituted) | a local `make ci` that CI never runs |
| `[[guard_bash.warn_program]]` | programs worth a warning wherever they run, also as `npx <program>` | `npx prettier` in a repo formatted by eslint |
| `[session_state]` | `memory_budget` in bytes for the project's always-loaded `MEMORY.md`, a `memory_hint` appended to that warning; `warn_on_default_branch = false` for a repo that commits on its default branch by design | `memory_budget = 6144` |
| `[warn_pipefail]` | `runners` — your own runner commands beyond pytest/vitest/jest/… | `runners = ["./manage.py test"]` |
| `[evidence]` | `runners` — the commands `evidence-run` filters as test-runner output | `runners = ["test-api", "test-web"]` |

Every rule you add carries its reason in the `reason` string: the warning is the only place the
next session reads it.

**The guard fails closed, the config fails soft.** A `harness.toml` that does not parse, or an
entry of the wrong type, is reported once per command as a warning and that entry is dropped —
the generic rules keep running, and a repo cannot switch them off through its config. A hook
that crashes refuses the command instead, naming the exception: a crashed guard has judged
nothing, and the harness would otherwise read its exit as "no verdict".

<a id="guard-limits"></a>

### What the guard cannot see

`guard_bash` reads the command the agent typed, down to the string a `bash -c` carries — but
not the commands a script *file* or an interpreter one-liner will run. `bash scripts/publish.sh`
is one command to it, so it refuses that file by name rather than the `git push` inside; a
`git stash` inside a Makefile target, or `subprocess.run(["git", "push"])` in a `python3 -c`,
it does not see at all. Put a script of your own whose inner commands must stay the owner's
behind your own rule (`[[guard_bash.warn_program]]` warns; a refusal is a deny rule added to
`guard_bash.py`).

It also judges one session's commands only. A neighbouring session without the harness can
still move the stash stack or push; the session-start and stop hooks exist so that at least
the damage is measured, not inherited from a note.

### Tests

`make test` runs the harness suite under `harness/tests/`, the same thing CI runs
(`.github/workflows/test.yml`); `make lint` runs ruff over the hooks, the tools, the tests and
the `wave-prep` scripts, with the rules in `ruff.toml`, and `make format` applies them. Three
files carry the structure:

- `test_hook_rules.py` — one witness per rule: a payload, the hook, the verdict, with
  `rule: <id>` in the docstring. `test_hook_rules_forms.py` runs the same rules through the
  command *forms* — pipes, subshells, `bash -c`, `xargs`, loops — that the guard unwraps.
- `test_hooks_are_armed.py` — compares the rule ids the hooks can fire with the ids the
  witnesses name, in both directions, and pins the number of refusals.
- `test_evidence_run.py`, `test_absence_check.py`, `test_publish.py` — the tools and the
  publish script against a throwaway clone.

## Repository layout

```
.claude-plugin/
├── plugin.json                     # the wave-skills plugin manifest
└── marketplace.json                # lets the repo be added as a marketplace
agents/
├── gate-evidence-auditor.md        # evidence, not code — the second review lens
├── solution-architect-reviewer.md  # plan review, before any code exists
├── spec-reviewer.md                # the link's diff against the spec
└── standards-reviewer.md           # a diff against documented standards + a smell baseline
Makefile                            # make test · make lint · make format
ruff.toml                           # lint and format rules; also lists the extensionless scripts
harness/
├── .claude-plugin/plugin.json      # the wave-harness plugin
├── hooks/                          # hooks.json + the four hooks, repo_config.py reads harness.toml
├── bin/                            # evidence-run, absence-check, suite-summary
├── tests/                          # pytest; CI runs it (.github/workflows/test.yml)
└── harness.example.toml            # .claude/harness.toml for an invented repo
scripts/
├── link-skills.sh                  # skills + agents, symlinked for editing
├── link-harness.sh                 # hooks + tools, registered for editing
└── publish.sh                      # stage, denylist-check, commit, push
skills/
├── wave-grill/
│   ├── SKILL.md
│   ├── references/glossary-format.md
│   ├── references/adr-format.md
│   └── LICENSE, CREDITS.md         # adapted from mattpocock/skills, MIT
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
├── wave-close/
│   ├── SKILL.md
│   └── references/templates.md     # link report, relay, post-wave prompt
└── wave-retro/
    ├── SKILL.md
    └── LICENSE, CREDITS.md         # adapted from mattpocock/skills, MIT
THIRD-PARTY-NOTICES.md              # what is adapted from where, and its license
```

`agents/` and `skills/` are discovered by convention, so the manifest names no paths. Both are
flat: skill names must be unique, since `link-skills.sh` links by basename and the plugin loader
expects `skills/<name>/SKILL.md`.

## Development

### Editing and publishing

With the [symlink setup](#as-symlinks-to-edit-the-skills-as-you-use-them),
`~/.claude/skills/wave-prep/SKILL.md` points directly into
`~/waveflow/skills/wave-prep/SKILL.md`, and `~/.claude/agents/gate-evidence-auditor.md` into
`~/waveflow/agents/`. Editing the installed file *is* editing the repo. Edit either however
you like, then publish:

```bash
bash ~/waveflow/scripts/publish.sh "wave-run: name the mirror check per repo"
```

That's it — no copying, no separate commit step. `publish.sh` stages `skills/`, `agents/`,
`harness/`, `scripts/`, `.claude-plugin/`, `.github/`, `README.md`, `LICENSE`, `THIRD-PARTY-NOTICES.md`, `.gitignore`,
`Makefile`, `ruff.toml` and `package.json`, so every edit travels with the skill edits. Bump `version` in `.claude-plugin/plugin.json` (and
`harness/.claude-plugin/plugin.json`) when a plugin changes meaningfully.

**A project-level copy wins over the link.** Claude Code prefers `<repo>/.claude/skills/<name>`
and `<repo>/.claude/agents/<name>.md` over the user-level ones, so a repo that still carries its
own copy of a wave skill or a shipped agent silently runs that copy, and your edits land in the
wrong file. Delete the repo's copies when you switch to the link; what was repo-specific in them
belongs in its `.claude/wave-profile.md`.

**Without the symlink setup** (e.g. you installed via `npx skills@latest add`), copy into a
clone and publish from there:

```bash
cp ~/.claude/skills/wave-prep/SKILL.md ~/waveflow/skills/wave-prep/SKILL.md
bash ~/waveflow/scripts/publish.sh "update wave-prep"
```

**A publish denylist keeps private projects out** — see
[Developing inside a private project](#private-project).

### Adding a skill

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
   mkdir -p ~/waveflow/skills/<skill-name>
   cp ~/.claude/skills/<skill-name>/SKILL.md ~/waveflow/skills/<skill-name>/SKILL.md
   bash ~/waveflow/scripts/link-skills.sh
   ```
3. Publish:
   ```bash
   bash ~/waveflow/scripts/publish.sh "add <skill-name> skill"
   ```

The `skills` CLI discovers any `SKILL.md` under `skills/` automatically — no registration step.
Skill names must stay unique: `link-skills.sh` links by basename.

### Adding an agent

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

### Changing the harness

`link-harness.sh` points the registered hooks and the three tools into the clone, so editing
`harness/hooks/*.py` or `harness/bin/*` is live in the next session (hooks are read at session
start). Run the suite before publishing — it is what CI runs:

```bash
cd ~/waveflow && make test                      # ARGS="harness/tests/test_publish.py" narrows it
make lint                                           # ruff check + format --check, rules in ruff.toml
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
5. **A rule only your repo needs is config, not code** — [`harness.toml`](#harness-config).

<a id="private-project"></a>

### Developing inside a private project

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

## Credits

`wave-grill`, `wave-retro`, `spec-reviewer` and `standards-reviewer` are adapted from
[mattpocock/skills](https://github.com/mattpocock/skills) by Matt Pocock, under the MIT License.
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) lists what came from where and carries the
license; each adapted skill keeps its own `LICENSE` and a `CREDITS.md` saying what changed, so
the notice travels with a skill installed on its own.
