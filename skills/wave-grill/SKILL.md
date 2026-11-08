---
name: wave-grill
description: Use when a slice of a feature is about to be specced for a wave but its decisions are not settled - the design needs stress-testing, its terms are fuzzy, or nobody has asked what proves the slice done.
disable-model-invocation: true
---

# Grilling a slice

## Overview

Interview the owner relentlessly until you reach a shared understanding of **one slice** of a
feature. The grill produces decisions, written down as they are made; the spec is written from
them afterwards. It writes no code, no plan and no wave document.

Core principle: **a decision reversed mid-wave costs a link; a decision reversed mid-grill costs
a sentence.** Every branch is visited now, so none is reopened later.

## The design tree, in rounds

Map the slice as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already
settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask
the whole frontier in one round: number each question and give your recommended answer. Then
wait for the owner's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the owner answers reshapes the tree: settled decisions push the frontier outward and
unblock questions that depended on them. Recompute the frontier and ask the next round. A
question whose answer depends on another question still open in this round belongs to a _later_
round, not this one.

**Facts are yours, decisions are the owner's.** When a frontier question needs a fact from the
environment (the tree, the docs, a tool), dispatch a subagent with a fresh context window to find
it; never ask the owner for anything you could look up. Don't block on it: a running exploration
is an unsettled prerequisite, so only the questions downstream of it wait; ask the rest of the
frontier now. The _decisions_ are the owner's: put each to them and wait. Never answer your own
question on the owner's behalf.

## Round 1 — is it one slice?

The first round always carries three questions, whatever else is on the frontier:

1. **Precondition** — what must be true in `main` before this slice can start?
2. **Done-state** — what is observably true when it is finished?
3. **Gates** — which checks go red today and green when it is done?

If the three cannot be stated for this slice alone, it is more than one wave: cut it before going
on, grill the first part, and write the rest under **Not yet specified** or **Out of scope**.

A wide mechanical change (renaming a column, retyping a shared symbol) whose blast radius breaks
every caller at once cannot land green as one link. Sequence it **expand–contract**: add the new
form beside the old, migrate the callers in batches (each its own link, blocked by the expand),
then delete the old form in a link blocked by every batch.

## The gates branch

Every behaviour the slice adds gets one question before the grill can end: **what goes red
without it, and for what reason?** The plans' gate tables and the wave's evidence auditor later
hold each link to exactly this. Prefer a seam the tree already has, as high as possible; a new
seam is a decision, and it goes on the frontier like any other.

## The decisions file

`docs/superpowers/specs/YYYY-MM-DD-<topic>-decisions.md`, beside the spec it will feed. Create it
when the first decision settles and append to it after **every** round. A session can die
mid-grill; a decision that lives only in the dialogue dies with it, and a spec written from a
summary of a grill is confidently wrong about whatever the summary flattened.

```markdown
# Decisions: <slice>

## Destination
<one or two lines: what reaching the end of this slice looks like>

## Decisions
- **<question title>** — <the owner's answer, in a sentence> (round <n>)

## Not yet specified
<in-scope questions you can already see but cannot yet phrase sharply>

## Out of scope
<what was consciously ruled out of this slice, and why>
```

Record the owner's answer, not your recommendation, when they differ. A decision the owner
reverses is struck through and followed by its replacement, never deleted.

## The domain model, as you go

Build the project's vocabulary while you grill — this is the active discipline, not merely
reading a glossary:

- **Challenge against the glossary.** When the owner uses a term that conflicts with
  `GLOSSARY.md`, say so at once: "Your glossary defines 'cancellation' as X, but you seem to mean
  Y. Which is it?"
- **Sharpen fuzzy language.** For a vague or overloaded term, propose a precise canonical one:
  "You're saying 'account': the Customer or the User? Those are different things."
- **Invent concrete scenarios** that probe the boundaries between concepts, and make the owner
  precise about them.
- **Cross-reference with the code.** When the owner states how something works, have a subagent
  check whether the code agrees, and surface a contradiction as a question.
- **Update the glossary inline,** the moment a term is resolved, in the format of
  [references/glossary-format.md](references/glossary-format.md). It holds terms only: no
  implementation details, no decisions — those go to the decisions file.
- **Offer an ADR sparingly** — only when a decision is hard to reverse, surprising without
  context, **and** the result of a real trade-off. Format and examples in
  [references/adr-format.md](references/adr-format.md).

Files are created lazily, when there is something to write: a root `GLOSSARY.md`, or the one a
`GLOSSARY-MAP.md` points to; `docs/adr/` at the first ADR. A repo that keeps its glossary in a
legacy `CONTEXT.md` keeps it there — never start a second glossary beside it.

## When the grill is done

The frontier is empty: every branch visited, the gates branch answered for every behaviour,
nothing silently assumed. Ask the owner to confirm the shared understanding; until they do, it is
not done.

Then the next step is the spec, `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, written
from the decisions file. Write it in this session when there is room — the spec wants the
reasoning first-hand — otherwise in a fresh session pointed at the decisions file.

## Common mistakes

| mistake | instead |
|---|---|
| one question per message | the whole frontier, numbered, each with a recommendation |
| a question that depends on another still open in the same round | move it to a later round |
| asking the owner where something lives in the code | a subagent finds it |
| writing the decisions file at the end | after every round |
| a slice whose done-state needs a second slice to be true | cut it in round 1 |
| implementation detail in `GLOSSARY.md` | it belongs in the decisions file or the spec |

---

Adapted from the `grilling` and `domain-modeling` skills of
[mattpocock/skills](https://github.com/mattpocock/skills), © 2026 Matt Pocock, MIT — see
[CREDITS.md](CREDITS.md) and [LICENSE](LICENSE).
