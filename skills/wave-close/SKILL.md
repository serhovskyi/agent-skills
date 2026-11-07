---
name: wave-close
description: Use when a link's tasks are done and reviewed but its summary, minor-issue triage, merge decision and relay do not exist yet, or when the session that ran the link died and closing has to happen somewhere else.
---

# Closing a link and handing over the next

## Overview

Closing a link is four decisions and two documents. It reads the **ledger and the
registry**, never the dialogue — so a fresh session can close a link whose executing
session died, and so the owner's decisions are never asked by a session that is one
message from a compaction.

Core principle: **ask one question at a time, each with a recommendation, and ask early.**
A deferred decision becomes a decision made by default.

## When to use

- Every task of a link is done and the final review has run.
- A link finished but was never closed: no summary, no relay, unclear merge state.
- The whole wave's last link is done (the loop terminates instead of relaying).

## When closing moves to a fresh session

The session that ran the link writes `docs/superpowers/plans/<wave>-CLOSE-<id>-PROMPT.md`
and stops. That prompt names **this skill**, the link, the ledger and registry paths, the
review and evidence files, and the owner decisions already taken — and nothing about the
shape of the steps below. A close prompt that restates a step drifts from it: one asked
for a separate `-SUMMARY.md` where step 6 says otherwise. Where the prompt and this skill
disagree on how a step is done, the skill wins.

## The order

1. Summary
2. Minors triage — one question
3. Architectural findings — one question
4. Merge gate — one question
5. Re-probe the next plan — one question if it drifted
6. Write the relay, refresh the next prompt, update the registry, print the paste block
7. Propagate the link to the vault

Questions go to the owner in this order and one at a time. Never batch them, and never
proceed on an assumed answer.

## 1. Summary

Read it out of the ledger, in the shape `references/templates.md` gives. Rules:

- **Δ, never absolutes.** "Suite green" is not a report.
- **A divergence over 20% from either forecast column is the first line**, not a footnote:
  tasks Δ against the tasks forecast, close Δ against the close allowance (link prompt,
  Forecast).
- Gates that went red get a line each: which, why, and **ours or not ours**.
- Divergences between what the plan said and what the tree showed get a line each. They
  are the raw material of the relay.

## 2. Minors triage — one question

Collect every small thing the link produced and did not fix: a rough edge a reviewer
noted, a test that is thin, prose that no longer matches, a name that reads wrong.

Give each one **your recommendation** first, then ask a single question whose options are
built from those recommendations:

- fix all of them now, in this session, via subagents
- fix only the ones recommended; defer the rest
- defer all to a post-wave session
- file an issue for a specific one

Whatever is deferred is written into the registry **with the link that produced it**, so
the post-wave prompt is later assembled from a record rather than from memory.

## 3. Architectural findings — one question

Anything the link surfaced that asks to be generalized — a pattern repeated a third time,
a helper that wants to be a service, a boundary that keeps leaking — gets its own
question: file an issue · fold into this wave · drop it knowingly.

**No issue is ever filed without that answer.** An unasked "I'll just file it" turns the
tracker into a second, unowned plan.

## 4. Merge gate — one question

Ask whether to merge the link's branch into `main`.

On yes, the controller merges **locally** and never pushes:

```bash
git status --porcelain                    # empty, or stop
git switch main
git merge --no-ff <branch>
# on main, after the merge: the WAVE's Baseline method, every suite the link touched
git rev-parse --short HEAD
```

The tree is shared: uncommitted work at this point belongs to another session, and
`git switch main` would carry it onto `main` or fail against it. Check before switching,
not after.

**A conflict is a stop.** `git merge --abort`, then ask. Do not resolve it — a merge
resolution is code written by the controller — and do not run the suite over a tree that
still carries conflict markers, because whatever it prints is about the markers.

Report the post-merge suite numbers and the new sha. Push and PR are the owner's, always.

If the suite is red **after** a merge that was green before it, say so immediately and do
not proceed to the relay: the next link's start predicate is now false.

## 5. Re-probe the next plan

The link just changed the tree, so the next plan may now point at addresses that moved.
This is normal, not exceptional — one link's move killed six addresses cited by a plan two
waves away.

```bash
"$WP/scripts/plan-probe" docs/superpowers/plans/<wave>-<next>.md --quiet
```

`WP` is the `wave-prep` skill's directory. Read the grades: `MOVED` and `DEAD` mean the
next plan cites something this wave moved or deleted.

The profile is re-probed in the same step, because a link that moves a directory, renames an
agent or splits a make target has just made the profile cite a dead address to every later
dispatch:

```bash
"$WP/scripts/profile-probe" --quiet
```

A red profile line is not an owner question: the link that moved the address updates the
profile in its close, in the same commit as the relay, and the relay names the line. The
profile is the repo's, so the fix states the new address, never the history of the move.

On plan drift, one question: patch the plan in place (only when it is documentation-level — a
path, a line reference, a name) · re-pipeline it separately (when the drift changes what
the plan *does*). Silently patching a plan that needs a re-pipeline hides how stale it was.

## 6. Write the handover

| document | where |
|---|---|
| relay | `docs/superpowers/plans/<wave>-HANDOFF-<next>.md` |
| next link's prompt | refresh predicates and open decisions in place |
| registry | `.superpowers/sdd/<wave>/wave.md` — status, numbers, deferrals, issues |

Then print the next link's prompt as a paste-into-a-fresh-session block.

Everything written here is English.

**On the last link there is no relay.** Write the wave summary instead — forecast against
measured Δ per link, gates that went red and why, decisions taken — plus, if anything was
deferred, one post-wave prompt assembled from the registry. The summary is a closing
`## Outcome` section of `<wave>-WAVE.md`, not a new file.

Then retire the wave's session documents, in one commit on `main` after the last merge:

| delete | keep |
|---|---|
| `<wave>-LINK-*-PROMPT.md` · `<wave>-HANDOFF-*.md` · `<wave>-CLOSE-*-PROMPT.md` · raw `evidence/` files no document names | `<wave>-WAVE.md` · specs · plans · `*-REPORT.md` · `evidence/*.md` and every evidence file a document, test or comment names · mockups · the post-wave prompt |

They existed to start one session each; once the wave is closed nothing reads them, and a
grep over `plans/` keeps finding their stale predicates. A raw evidence file — a suite log,
a probe dump, a snapshot — earns its keep only by being cited: a gate's red run that a
REPORT names is the proof the auditor reads, an unnamed one is output nobody will open.
Measure by basename (`git grep -F`) before deleting; age is never the criterion. Before deleting, read every relay's
**debts handed on** and **what this link learned**: whatever is still open and absent from
the link reports moves into the summary or the post-wave prompt. A debt that lives only in a
deleted relay is a debt nobody will find — `git log` keeps the text, not the reason to look.

## 7. Propagate the link to a knowledge vault — optional

Only if the owner keeps one. Run `/obsidian-save` here, in the closing session, before the
paste block ends the work.

The closing session is the only one that holds all of it: the measured Δ, the four answers,
what went red and whose fault it was. A later session reconstructs that from documents and
gets it thinner; the `SessionEnd` fallback writes without the owner's answers at all.

What travels: the link's dev-log with its Δ, decisions that outlive the branch, debts by
name. What stays here: plan text, evidence files, suite output, shas as facts. Where the
repo states its own propagation rules they apply, and the vault's own `_CLAUDE.md`
outranks them.

Skip silently when `OBSIDIAN_VAULT_PATH` is unset — the vault is the owner's, not the
repo's dependency, and this whole step is optional.

## What belongs in a relay

A relay is not a diff summary. It carries what the next link cannot re-derive:

- what is already done, by sha, one line each — so it is not redone;
- the next link's **start condition as a predicate**, and whether it currently holds;
- what this link **learned** that hits the next one specifically;
- debts handed on by name, each with its issue number or an explicit "not filed";
- owner decisions still open, stated as decisions, not as background.

Operational claims rot like numbers. A relay that says "the suite is 1796" is stale within
hours; one that says "record the suite before starting" stays true.

The one number a relay may hand on is the close count **with its tree keys**: the start
predicate names the close file, the hashes it recorded and the `git rev-parse` that checks
them, so the next link adopts the count only while the tree it was measured on still holds
(`wave-run`, Preflight). A close file without the keys hands on nothing — the next link runs
its baseline.

The close is re-recorded every time its tree key moves, and each re-record holds the same line
as the first: **every `EXIT=` in the close file is printed by the shell that ran the command**
— the evidence runner (profile § Evidence tooling), or `; echo "EXIT=$?"` on the runner
itself, never after a pipe.
None is typed, and a command with no `EXIT=` under it is run again before the file is
handed on. A diff the close claims empty is recorded with `--exit-code`: `git diff --stat`
exits 0 on a difference. One close shipped a hand-typed lint `EXIT=0` beside a suite log with
no exit at all, and took a third round to re-record.

## Common mistakes

| mistake | what happens |
|---|---|
| Batching the four questions | the owner answers the loudest one and the others resolve by default |
| Closing from the executing session at 95% context | the questions get asked badly, or not at all |
| Reporting absolutes | nobody can tell whether the link did what it forecast |
| Copying the wave's model table into the relay | one fact, two sources, guaranteed drift |
| Patching a stale next plan quietly | the next link starts on a plan nobody re-reviewed |

## Red flags

- "I'll ask about the minors and the merge together to save a round trip."
- "The next plan is probably fine, it's from the same wave."
- "I'll note the deferred items in my summary" — the registry is the record; a summary is
  read once.
- "The merge is obvious, I'll just do it" — the merge is a question, every time.
