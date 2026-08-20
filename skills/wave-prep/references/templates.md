# Wave document templates

All three are written in English. Fill every angle bracket; a template shipped with a
placeholder still in it is an unfinished document.

---

## `docs/superpowers/plans/<wave>-WAVE.md`

Everything every link shares. Never repeat any of it in a link prompt.

```markdown
# Wave: <name>

One session per link. Memory between links is the ledger and `git log`, never the dialogue.

## Role

The session running a link is a **controller**, not an implementer. It writes no product
code: a controller's own fix skips review and pollutes the context that has to last the
whole link. Use `superpowers:subagent-driven-development` for the per-task machinery.

## Repo adaptations that override the canonical skill

State the ones that are true here, and only those. Each line is a rule a link would
otherwise learn the hard way. Common ones, as examples of the shape:

- **Worktree or branch in place.** If the stack cannot come up in a worktree (an
  `external: true` volume, containerized commands), work on a branch instead:
  `git switch -c <branch prefix>-<link>` from a fresh `main`.
- **A link starts only after the previous link is in `main`.** Each plan states this as its
  own precondition. If a start predicate fails, the usual cause is an unmerged previous
  link, not a defect in the plan — ask rather than starting from an old `main`.
- **Whether the tree is shared.** Where it is, foreign uncommitted work at preflight is a
  stop.
- **Generated mirrors.** Name every tracked file a tool rewrites (API client, lockfile,
  schema dump); `wave-run` checks them at preflight.

## Reviewers

The rosters, named once for the whole wave. `wave-prep` step 6 uses the plan reviewers;
`wave-run` uses the code reviewers per task and again over the whole link.

| roster | agents |
|---|---|
| plan reviewers | <architecture reviewer> + <one per layer> |
| code reviewers | <one per layer — e.g. backend, frontend> |
| evidence auditor | <the agent that audits gate claims against the logs> |

## Order of links

| # | plan | branch | what it does | forecast Δ | tasks |
|---|---|---|---|---|---|
| 1 | `…-<id>.md` | `<branch>` | <one line> | <±n> | <n> |

**Total: Δ = <±n>, <n> tasks.**

Why this order: <the dependency that forces each pair, one line each — a path one link
creates and the next consumes, a rule that forbids the reverse direction>.

## Model policy

<Copy the tier table and the reviewer rules verbatim out of this skill's own `SKILL.md`,
step 4. That table is their single source; a second copy here would be the drift this
wave file exists to prevent.>

## Baseline method

Before every link, the repo's own suite command — named **here and only here**, so no link
re-derives it:

```bash
<the exact command, e.g. make test / npm test / pytest -q> 2>&1 | tail -5
```

Tracked generated mirrors that must be clean at preflight: `<paths, or "none">`.

Record **the total, the file count and the failure count** — all three. A file that fails
does not change the total, so one number stays green over red gates.

The suite must be green at link start. If it is not, do not start: "was green → is green"
stops being evidence. Name the cause and ask.

## Gates this wave moves

| gate | form | how it stays silent |
|---|---|---|

Give this table to every reviewer as an attention list. One gate file can carry several
independent pins, and a grep for the filename does not prove you found them all.

Rules for every link:
1. Ratchet values are read from the failure, never guessed.
2. Line numbers are re-found by content grep.
3. Quotes inside gates are searched for by content, not by position.
4. Red is read for its cause: the tree is shared, and the failure may not be yours.

## Do not

- <the neighbouring layer this wave must not touch>
- Fix code as the controller.
- Dispatch two implementers at once.
- File an issue without the owner's decision.
- Push, or open a PR.
```

---

## `docs/superpowers/plans/<wave>-LINK-<id>-PROMPT.md`

Thin. Everything shared lives in `WAVE.md`, and is referenced, not repeated.

```markdown
# Link <id> — start prompt

Paste this whole file as the first message of a fresh session.

Read `docs/superpowers/plans/<wave>-WAVE.md` first — role, adaptations, model policy,
baseline method and the gates lens live there. This file adds only what is specific to
this link.

**Plan:** `docs/superpowers/plans/<wave>-<id>.md` (<n> tasks, counted)
**Branch:** `<branch>` from a fresh `main`
**Relay from the previous link:** `docs/superpowers/plans/<wave>-HANDOFF-<id>.md`
**Ledger:** `.superpowers/sdd/<wave>-<id>/progress.md`

## Start predicates — all must hold

| predicate | how to check |
|---|---|
| previous link is in `main` | `git merge-base --is-ancestor <prev branch> main` |
| tree clean | `git status --porcelain` empty |
| generated mirrors unmodified | `git status --porcelain <mirrors from WAVE.md>` empty |
| <link-specific predicate> | <command> |

## Model per task

| task | model | why |
|---|---|---|

## Forecast

| | expected |
|---|---|
| Δ <suite name> | <±n> |
| Δ <other suite, if the link touches one> | <n> |
| ratchets this link moves | <name>: <from> → <to> |

A divergence over 20% from this forecast is the first line of the report, not a footnote.

## Open owner decisions this link inherits

<from the relay, or "none">
```

---

## `.superpowers/sdd/<wave>/wave.md`

Untracked on purpose: it must survive `git switch` between link branches.

```markdown
# Wave registry — <wave>

Base: `<sha>` measured <date>. Suite at base: Tests <n> / Files <n> / failed <n>.

## Links

| link | branch | status | tasks | suite before → after | Δ vs forecast | merged |
|---|---|---|---|---|---|---|
| <id> | <branch> | pending \| running \| closed \| merged | <done>/<total> | <n> → <n> | <±n> vs <±n> | <sha> \| no |

## Deferred minors

| # | from link | what | recommendation | owner's decision |
|---|---|---|---|---|

## Issues filed

| issue | from link | what |
|---|---|---|

## Decisions taken mid-wave

| date | decision | who |
|---|---|---|
```
