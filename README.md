# agent-skills

Personal agent skills for AI coding assistants — dev workflow tooling, starting with the
**wave** pipeline for executing multi-plan features without drowning the controller's context.

## Installation

Install on any supported agent (Claude Code, Cursor, Windsurf, OpenCode, and 70+ others):

```bash
npx skills@latest add serhovskyi/agent-skills
```

Or, for manual linking to Claude Code and compatible harnesses:

```bash
git clone https://github.com/serhovskyi/agent-skills ~/agent-skills
bash ~/agent-skills/scripts/link-skills.sh
```

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
| **reviewer subagents** (see below) | every review stage dispatches by role |

### Reviewer roster — supplied by your repo

The skills dispatch reviewers **by role**, not by hardcoded name. Provide agents for the roles
your repo actually has and record them once in `WAVE.md` § Reviewers:

| role | used by | purpose |
|---|---|---|
| plan reviewers — architecture + one per layer | `wave-prep` step 6 | do the plans still hold up against the tree? |
| code reviewers — one per layer | `wave-run`, per task and over the whole link | does the code hold up? |
| evidence auditor | `wave-run`, final review | did the gates this link claims to have moved *actually* go red, and for our reason? |

The evidence auditor is the one worth building if you build only one: it reads the ledger and
the logs, **not** the diff, and it catches gates that stayed silent — path-scoped rules, pinned
equalities, discriminating pairs, environment-green. A wave that skipped review found four
defects in a later pass that its green suite never saw.

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
skills/
└── dev/
    ├── wave-prep/
    │   ├── SKILL.md
    │   ├── references/templates.md    # WAVE.md, LINK-PROMPT, registry
    │   └── scripts/
    │       ├── plan-extract           # countable structure of a plan
    │       └── plan-probe             # plan vs. the live tree
    ├── wave-run/
    │   └── SKILL.md
    └── wave-close/
        ├── SKILL.md
        └── references/templates.md    # link report, relay, post-wave prompt
```

`link-skills.sh` flattens this: `~/.claude/skills/wave-prep` regardless of the category
directory, so categories are for humans reading the repo, not for the harness.

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
`~/agent-skills/skills/dev/wave-prep/SKILL.md`. Edit it however you like, then publish:

```bash
bash ~/agent-skills/scripts/publish.sh "wave-run: name the mirror check per repo"
```

That's it — no copying, no separate commit step.

---

**Without the symlink setup** (e.g. you installed via `npx skills@latest add`), copy and push
manually:

```bash
cp ~/.claude/skills/wave-prep/SKILL.md ~/agent-skills/skills/dev/wave-prep/SKILL.md
bash ~/agent-skills/scripts/publish.sh "update wave-prep"
```

Users who installed via `npx skills@latest add` pull the latest by re-running the same install
command. Users who cloned manually just need `git pull` — the symlinks already point into the
clone, so no relinking is needed.

### Adding a new skill

1. Write the skill at `~/.claude/skills/<skill-name>/SKILL.md`, starting with the required
   frontmatter:
   ```yaml
   ---
   name: skill-name
   description: One-line description of when and why to invoke this skill.
   ---
   ```
2. Create it in the repo under a category (or move it there, then re-link):
   ```bash
   mkdir -p ~/agent-skills/skills/<category>/<skill-name>
   cp ~/.claude/skills/<skill-name>/SKILL.md ~/agent-skills/skills/<category>/<skill-name>/SKILL.md
   bash ~/agent-skills/scripts/link-skills.sh
   ```
3. Publish:
   ```bash
   bash ~/agent-skills/scripts/publish.sh "add <skill-name> skill"
   ```

The `skills` CLI discovers any `SKILL.md` under `skills/` automatically — no registration step.
Skill names must stay unique across categories: `link-skills.sh` links by basename.
