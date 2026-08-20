---
name: wave-run
description: Use when executing one link of a prepared wave in a fresh session - a link start prompt exists and its predicates are unverified, a link's tasks are written but none has been dispatched, or a previous session died mid-link and its ledger must be picked up.
---

# Running one link of a wave

## Overview

One session runs one link. You are a **controller**: you dispatch, measure, record and
review.

**You do not edit files under the link's plan. Not product code, not test code, not a
spec, not an import, not a name, not a comment.** The only files you write are the ledger,
the registry and the reports this skill names. There is no size below which this stops
applying, and no file type it excludes: a "one-line fix in a test" is a change that ships
without review, in a repo whose gates live in test files.

Core principle: **your context is the scarce resource, and the ledger is your memory.**
A session that reads task texts, pastes histories and reads transcripts dies halfway
through its own link and re-dispatches work it already did.

## When to use

- A link's start prompt exists and the link has not run.
- A link ran partway and the session was lost; the ledger says where it stopped.

Not for preparing a wave (`wave-prep`) and not for closing one (`wave-close`).

## Preflight — every predicate, before the first dispatch

```bash
git status --porcelain                              # empty, or stop
git status --porcelain <generated mirrors>          # empty, or stop
git merge-base --is-ancestor <prev-branch> main     # previous link is in main
<suite command> 2>&1 | tail -5                      # from WAVE.md § Baseline method
```

`<suite command>` and `<generated mirrors>` are the repo's own, named once in the wave's
`WAVE.md`. They are not for you to invent per link.

Record **the total, the file count and the failure count** in the ledger before anything
else. All three: a failing file does not change the total, so `N tests passed` reads green
while a gate is red underneath.

Then the link's own predicates from its start prompt.

**Any red predicate is a stop, not a note.** Foreign uncommitted work means another
session owns this tree. An unmergeable previous link means the wave is not ready. A red
suite means "was green → is green" has stopped being evidence. Name the cause, ask, wait.

The generated-mirror check is not optional where the repo has one — a tracked file some
tool regenerates (an OpenAPI client, a lockfile, a schema dump). Every `lint`, `test` and
`type-check` can silently rewrite it, so a dirty mirror turns an unrelated command into an
unexplained diff.

## The per-task loop

For each task, in order, one at a time:

1. `"$SDD/task-brief" <plan> <n>` → a path. `SDD` is the
   `superpowers:subagent-driven-development` scripts directory.
2. Dispatch the implementer **with the model named** from the link prompt's table.

   The dispatch prompt is exactly five parts, in this order: one line of context · the
   brief path · interfaces produced by earlier tasks · the report path · the four-line
   reply contract. Anything else you are tempted to add is already in the brief.

   **You do not open the plan to write a dispatch.** A task that looks subtle is subtle in
   its own text, and the brief is that text — restating it in the prompt means the
   implementer reads it twice and you read it once too many. If you catch yourself
   reaching for the plan to warn the implementer about something, that warning belongs to
   the reviewer's attention list, not to the dispatch.
3. The implementer writes, tests, commits, writes its report **to a file**, and returns
   four lines: status, commits, one line about tests, caveats.
4. `"$SDD/review-package" <plan> <base> <head>` → a path. Dispatch the reviewer **by the
   layer the task touched**, using the wave's reviewer roster (`WAVE.md` § Reviewers) —
   one code-reviewer per layer, and **both** for a vertical task: same diff file, two
   lenses. The prompt carries the brief path, the report path, the diff path and the
   wave's gate table. Nothing else: the persona lives in the agent, not in your prompt.
5. Fix rounds if needed; rounds 4-5 escalate one tier above whatever stalled.
6. Write the ledger. Then print the status line.

**Two implementers never run at once.** They conflict in a shared tree.

## Context economy — the rules that cost no quality

**The files a controller opens during a link, in full:** the link's start prompt · the
ledger · the registry · report files written by implementers · the paths that
`task-brief` and `review-package` return · the output of commands you ran.

The plan file is not on that list. `task-brief` reads it for the implementer and
`review-package` frames it for the reviewer; both take its path as an argument, which is
not the same as you reading it. A controller that opens the plan has started paying, in
the one budget the link cannot refill, for information two subagents already have.

| rule | why |
|---|---|
| Never paste task text into a prompt; pass the brief path | otherwise the whole plan settles into your context and is re-read every step |
| Never paste the history of previous tasks | a real session reached a 42k-character prompt that was 99% pasted history |
| The diff reaches the reviewer as a **file**, never through your context | |
| Reports are files; you receive four lines | |
| Run the suite in the background and read `tail -5` | full suite output is thousands of lines |
| Never read a subagent transcript | they are larger than everything else combined |
| The ledger is your memory | after a compaction, trust the ledger and `git log`, not recollection |

## Status after every task

Print this — the owner should never have to ask what is left:

```
✅ Task 2/4 · link B2 (5 of 6) · sonnet · 2 fix rounds
   suite 1796 → 1800 (Δ +4, forecast +4, failed 0)
   remaining: 2 tasks in link · 5 tasks in wave · 1 link after this
```

Δ, never absolutes. "Suite green" is not a status.

## Final link review — always opus, two lenses

1. **The code**: the whole link's diff against its base — every code-reviewer whose layer
   the link touched, all on opus, all over the **whole** range. Each has so far seen only
   its own tasks; the seams between tasks are what this pass exists for. A run measured on
   2026-08-19 found a seam here that no per-task review had seen.
2. **The evidence against the logs**: the wave's evidence auditor (`WAVE.md` § Reviewers;
   a `gate-evidence-auditor` agent is the reference implementation, and a repo without one
   must supply the role before trusting this stage). It gets the ledger, the report files
   and the plan's gate table — **not** the diff. Did each gate this link
   claims to have moved actually go red, and for our reason? A gate that was already red,
   or red because of a neighbouring session, proves nothing about this link. It never
   moves the tree: a gate it cannot prove read-only comes back UNPROVEN with the command,
   and running that command is yours.

Review is a stage of the link, not an option. A wave that skipped it found four defects
in a later review that its green suite never saw.

## Gates: the four ways they stay silent

Watch for these while reviewing — each has shipped in this repo:

- **Path-scoped rules.** Files leave the perimeter; the gate walks a smaller tree and
  stays green.
- **Pinned equalities.** A count that must be lowered in the same commit, or the lint stays
  red for the rest of the link. Read the new value from the failure; never guess it.
- **Discriminating pairs.** Half of a `not.toContain(<file>)` becomes true *by absence*
  when the file is deleted.
- **Environment-green.** A gate that passes because of how it was run, not because of what
  the code does.

These four are the controller's attention list. The full catalogue — twelve classes, plus
how a number rots and how an exit code hides behind `| tail` — lives in the evidence
auditor agent, and is not to be copied back here.

## When the link cannot finish

Record in the ledger where it stopped, what is committed, and what the next session needs.
`wave-close` reads the ledger, so a link can be closed from a fresh session.

## Red flags

**Violating the letter of these rules is violating their spirit.** Each line below was
said by a controller that had already read this skill.

- "It's a one-line fix, faster if I just do it."
- "This file isn't really code."
- "Let me just look at the plan quickly to check what Task N means."
- "The suite is green, so the link is done" — green is not a delta.
- "This gate was already red, probably unrelated" — read its cause before believing that.
- "I'll write the ledger at the end of the link" — the ledger is written per task, because
  the session may not reach the end.
