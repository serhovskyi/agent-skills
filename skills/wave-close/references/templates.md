# Closing templates

English, like every document the wave writes.

---

## Link report

Read out of the ledger. Deltas, not absolutes.

```
LINK: <id>     BRANCH: <branch>     BASE: <sha>

SUITE:  <suite> <before> → <after>   (Δ <±n>, forecast <±n>, failed: <n>)
        <other suite> <untouched | before → after>   (prove it from the diff, not from memory)
LINT:   <lint command> — <ok | red, cause>
        <boundary/dependency rule, if the repo has one> — <count, must be 0>
TYPES:  <type-check command> — <ok | red, cause>
CI:     <ci command> — <ok | red, cause>

TASKS: <n>/<m> · models used: <which> · fix rounds: <how many, and where>

GATES THAT WENT RED, AND WHY:
  - <gate> — <cause> — <ours | not ours>

WHERE THE PLAN AND THE TREE DISAGREED:
  - <what the plan said> vs <what the tree showed>

DECISIONS TAKEN IN FLIGHT.
DEFERRED (minor / parked), and which need the owner.
```

A divergence over 20% from the forecast is the **first** line of this report.

---

## Relay — `docs/superpowers/plans/<wave>-HANDOFF-<next>.md`

```markdown
# Relay: link <n> (<id>) closed → link <n+1> (<next>)

## Already done — do not redo

| sha | what |
|---|---|
| `<sha>` | <one line, what changed and why it is finished> |

Suite at close: <n> tests / <n> files / <n> failed. Δ <±n> against a forecast of <±n>.

## Start condition for <next>

| predicate | holds now? | how to check |
|---|---|---|
| link <id> is in `main` | <yes/no> | `git merge-base --is-ancestor <branch> main` |
| <link-specific> | <yes/no> | <command> |

<If a predicate does not hold: say exactly what must happen first, and by whom.>

## What this link learned that hits <next> specifically

- <a trap that was measured, not suspected — with the file and the measurement>

## Debts handed on

| debt | issue | who fixes it |
|---|---|---|
| <name> | <#n, or "not filed — owner decision pending"> | <next link \| post-wave \| nobody> |

## Owner decisions still open

- <decision, stated as a decision, with the recommendation and what it blocks>

## Operational

<Anything about the tree, the branch, or the environment that the next session would
otherwise learn the hard way.>
```

**Do not restate the wave's model policy or gates lens here.** They live in
`<wave>-WAVE.md`; a relay that copies them creates a second source that drifts.

**Do not put measured absolutes in a relay** beyond the closing numbers above. Operational
claims rot within hours; predicates do not.

---

## Post-wave prompt (last link only)

```markdown
# Post-wave: <wave>

The wave is closed. `main` is at `<sha>`; suite <n>/<n>/<n>.

## Per-link outcome

| link | forecast Δ | measured Δ | fix rounds | merged |
|---|---|---|---|---|

## Deferred items, from the registry

| # | from link | what | why it was deferred |
|---|---|---|---|

## Issues filed during the wave

| issue | what |
|---|---|

Start by re-measuring the suite: every number above was true when written.
```
