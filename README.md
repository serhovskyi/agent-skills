# agent-skills

Personal agent skills for AI coding assistants — dev workflow tooling, starting with the
**wave** pipeline for executing multi-plan features without drowning the controller's context.

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

Two zero-token scripts do the counting, so prose and reality cannot drift:

```bash
WP=~/.claude/skills/wave-prep
"$WP/scripts/plan-extract" docs/superpowers/plans/<wave>-<link>.md      # task table, files, forecast
"$WP/scripts/plan-probe"   docs/superpowers/plans/<wave>-{a,b,c}.md -q  # MOVED / DEAD / MISSING / COLLISION
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
| `python3` | the two `wave-prep` scripts |
| **per-layer reviewer agents** (see below) | two of the four review seats ship here; the stack-specific ones are yours |

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

### Repo-specific values

The skills name no toolchain. Each wave states its own, once, in `WAVE.md`:

- **suite command** (`make test`, `npm test`, `pytest -q`, …) — plus the rule that all three
  numbers get recorded: total, file count, failure count. A failing file does not change the
  total, so one number stays green over red gates.
- **generated mirrors** — tracked files a tool rewrites (an OpenAPI client, a lockfile, a schema
  dump). `wave-run` checks they are clean at preflight, because `lint`/`test`/`type-check` can
  silently regenerate one and turn an unrelated command into an unexplained diff.
- **plans directory** — `docs/superpowers/plans/` by default, the superpowers convention.

The wave registry lives at `.superpowers/sdd/<wave>/wave.md` **because that path is gitignored**.
Wave state must survive the `git switch` between link branches; a tracked registry travels with
the branch and lies the moment a link merges.

## Structure

```
.claude-plugin/
├── plugin.json                     # the plugin manifest
└── marketplace.json                # lets the repo be added as a marketplace
agents/
├── gate-evidence-auditor.md        # evidence, not code — the second review lens
└── solution-architect-reviewer.md  # plan review, before any code exists
skills/
├── wave-prep/
│   ├── SKILL.md
│   ├── references/templates.md     # WAVE.md, LINK-PROMPT, registry
│   └── scripts/
│       ├── plan-extract            # countable structure of a plan
│       └── plan-probe              # plan vs. the live tree
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

---

**Without the symlink setup** (e.g. you installed via `npx skills@latest add`), copy and push
manually:

```bash
cp ~/.claude/skills/wave-prep/SKILL.md ~/agent-skills/skills/wave-prep/SKILL.md
bash ~/agent-skills/scripts/publish.sh "update wave-prep"
```

`publish.sh` stages `skills/`, `agents/` and `.claude-plugin/`, so agent and manifest edits
travel with skill edits.

Plugin users update with `/plugin update wave-skills`; `npx skills@latest add` users re-run the
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
