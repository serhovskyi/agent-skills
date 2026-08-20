---
name: wave-prep
description: Use when a feature's sub-plans are written and the wave has not started - plan files exist but no wave documents do, the order of links is unrecorded, per-task models are unassigned, or plans may have gone stale against the current tree.
---

# Preparing a wave

## Overview

A wave is N written sub-plans of one feature, executed one link per session. This skill
produces the documents a wave runs on, **without reading a plan body**.

Core principle: **count what can be counted, judge only what needs judgment.** Six plans
of one real wave are 3752 lines. A controller that reads them spends ~120k tokens before
the first dispatch, and a prompt built from that reading has contradicted the plan body
in both directions.

## When to use

- Sub-plans exist; `<wave>-WAVE.md` does not.
- A wave's plans were written before a neighbouring wave landed, and nobody has checked
  whether their addresses still resolve.
- A wave was prepared, then re-ordered or re-scoped.

Not for writing plans. This skill executes nothing and plans nothing.

## Quick reference

| step | who does it | cost |
|---|---|---|
| 1 discover plans, derive order | you | grep |
| 2 count structure | `scripts/plan-extract` | zero tokens |
| 3 probe against the tree | `scripts/plan-probe` | zero tokens |
| 4 judge complexity and gates | one subagent per plan | ~60 lines each |
| 5 write wave documents | you | — |
| 6 review gate | reviewer subagents, only if needed | — |
| 7 print the wave-start block | you | — |

Scripts live in this skill's directory. Address them through it — a bare
`scripts/plan-extract` resolves to the repo's own `scripts/` and fails:

```bash
WP="$(dirname "$0")"   # or the skill's base directory as given to you
"$WP/scripts/plan-extract" docs/superpowers/plans/<wave>-<link>.md
"$WP/scripts/plan-probe"   docs/superpowers/plans/<wave>-{a0,a1,a2}.md --quiet
```

`docs/superpowers/plans/` is where `superpowers:spec-driven-development` writes plans; every
path in this skill assumes it. A repo that keeps plans elsewhere substitutes its own
directory throughout — nothing else changes.

## Step 1 — discover and order

`<wave>` is the plans' shared stem, `<link>` each plan's suffix. Both are derived from
filenames, never invented.

**The glob catches this skill's own output.** `<wave>-WAVE.md`, `<wave>-LINK-*-PROMPT.md`,
`<wave>-HANDOFF-*.md` and any older `<wave>-EXEC-PROMPT.md` share the stem — the chassis
wave's glob returns eleven files for six plans. Exclude those four suffixes before doing
anything else, and re-preparing a wave is what makes this matter, not a first run.

Order comes from what each plan states as its precondition, not from alphabetical order.
If two plans do not order each other, that is a real ambiguity: ask the owner, once, with
your recommendation.

## Step 2 — count the structure

`plan-extract` prints task count, task titles, every declared file, the forecast table
and the global constraints. Everything in it is counted from the file.

**Task headings are matched at any level.** Real plans state tasks as both `## Task N`
and `### Task N`; a `### Task`-only grep reports zero of nine and says nothing. If the
script exits with "no Task N heading", the plan is malformed — do not proceed with zero.

## Step 3 — probe the plans against the tree

```bash
"$WP/scripts/plan-probe" <plans in execution order> --quiet
```

Paths a plan creates count as existing for every plan after it, so a forward reference
between links is not reported as missing.

**Probe against the tree the plan will run on.** Probing an already-executed plan against
a later tree reports every move it performed as a defect. At wave start that tree is the
wave base; later, `wave-close` re-probes only the next plan.

Read the grades — they mean different things:

| grade | meaning | usual action |
|---|---|---|
| `MOVED` | the path is gone and that filename lives elsewhere | the plan points at an address a neighbouring link moved — fix or re-pipeline |
| `DEAD` | path gone, its directory gone too | same, and the plan's mental model of the tree is older than you thought |
| `MISSING` | a `Modify:`/`Delete:` target is absent | usually real; sometimes an earlier task moves it in prose instead of declaring `Create:` |
| `COLLISION` | a `Create:` target already exists | the link may have partly run already |
| `NEW?` | absent, but its directory is live | normally a file the plan creates — informational |

Exit 1 means *something needs a look*, not *the plan is broken*.

## Step 4 — one judgment subagent per plan

Dispatch one subagent per plan. It reads the plan in full; you never do. Give it the
plan path and the extract, and require **at most 60 lines** back in this shape:

```
TASKS: <n>
MODEL PER TASK: T1 <tier> — <one line why>   (one row per task)
GATES: <gate file or name> — <how it can stay silent>   (one row per gate the plan touches)
PREDICATES: <predicate>   (start conditions, as predicates, not descriptions)
COLLISIONS: <task or plan> ↔ <task or plan> — <shared file or interface>
STALE SUSPICIONS: <what looks older than the tree>
```

Model tiers, from a wave that measured them:

| tier | the work looks like |
|---|---|
| `haiku` | greps and a run; no decisions |
| `sonnet` | mechanical multi-file work, or a component whose code the plan already contains |
| `opus` | many judgment calls, new test design, a ratchet whose value must be read from a failure, an i18n conversion with per-string decisions |

Reviewers: floor `sonnet`; a task at `opus` gets an `opus` review; the final link review is
always `opus`. In a fix loop, rounds 4-5 escalate one tier above whatever stalled.

**Always name the model.** An omitted model inherits the controller's — the most
expensive one — and voids the table.

## Step 5 — write the wave documents

See `references/templates.md` for all four.

| document | holds |
|---|---|
| `docs/superpowers/plans/<wave>-WAVE.md` | order and why, gates lens, model policy, baseline method, the don't-do list |
| `docs/superpowers/plans/<wave>-LINK-<id>-PROMPT.md` | start predicates, per-task models, forecast Δ, relay pointer |
| `.superpowers/sdd/<wave>/wave.md` | the registry: link status, measured numbers, deferred minors, issues, decisions |

**Nothing is stated in two documents.** The model table lived in one wave prompt and was
then copied verbatim into every relay; one fact with two sources drifts.

The registry lives under `.superpowers/` **because that path is gitignored**. Wave state
must survive the `git switch` between link branches; a tracked registry travels with the
branch and lies the moment a link merges.

All of these documents are written in English.

## Step 6 — review gate

Dispatch plan reviewers when a plan carries no recorded review, or when the probe found
`MOVED`/`DEAD`/`MISSING`: an architecture-level reviewer plus the reviewer for each layer
the plan touches. These are **plan** reviewers (do the plans hold up?), distinct from the
**code** reviewers `wave-run` dispatches per task. Record both rosters in `WAVE.md`
§ Reviewers so no link has to re-derive them.

Findings become **one** question to the owner: fix in place · re-pipeline separately ·
accept knowingly. A plan whose addresses moved is normally a re-pipeline, not an edit in
flight — silently patching a stale plan hides how stale it was.

## Step 7 — hand the wave to its first session

Print the first link's prompt as a paste-into-a-fresh-session block. That block is the
whole of "start the wave"; there is no separate starter document.

## Common mistakes

| mistake | what happens |
|---|---|
| Reading plan bodies to build the prompt | ~120k tokens spent before the first dispatch, and the wave dies mid-way |
| Trusting a plan's own count of its tasks | prose and body disagree; only the grep is evidence |
| Probing every plan against today's tree | executed links report their own moves as defects |
| Copying the model table into each link prompt | two sources for one fact |
| Filing issues for what the review found | no issue is created without the owner's answer |

## Red flags

- "I'll just skim the plan to see how hard the tasks are" — that is what the digest
  subagent is for.
- "The probe printed a lot, it's probably noise" — read the grades; `MOVED` is never noise.
- "The plan says three tasks" — count them.
- "I'll pick models later" — later is the dispatch, and the dispatch inherits opus.
