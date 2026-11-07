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
- **Commit trailer:** `Co-Authored-By: Claude <model> <noreply@anthropic.com>`, naming the
  model that wrote the commit. A plan or brief never writes a model's name into it: the
  harness gives each subagent a reminder naming its own model, and that reminder outranks a
  brief — two links of one wave carried Sonnet trailers under a brief that said Opus.

<then profile § Adaptations, verbatim>

## Reviewers

The rosters, named once for the whole wave, copied from profile § Reviewers. `wave-prep`
step 6 uses the plan reviewers; `wave-run` uses the code reviewers per task and again over
the whole link.

| roster | agents |
|---|---|
| plan reviewers | <architecture reviewer> + <one per layer> |
| code reviewers | <one per layer — e.g. backend, frontend> |
| evidence auditor | <the agent that audits gate claims against the logs> |

## Order of links

| # | plan | branch | what it does | forecast Δ (tasks + close) | tasks |
|---|---|---|---|---|---|
| 1 | `…-<id>.md` | `<branch>` | <one line> | <±n> + <n> | <n> |

**Total: Δ = <±n> + <n>, <n> tasks.**

Why this order: <the dependency that forces each pair, one line each — a path one link
creates and the next consumes, a rule that forbids the reverse direction>.

## Model policy

<Copy the tier table and the reviewer rules verbatim out of this skill's own `SKILL.md`,
step 4. That table is their single source; a second copy here would be the drift this
wave file exists to prevent.>

## Baseline method

Before every link, each suite the wave touches, **in the background, one at a time, into log
files**. `$LOG` is a directory in the session's scratchpad, never in the repo. The commands
are profile § Suites, copied here and nowhere else in the wave, so no link re-derives them:

```bash
<suite command> > "$LOG/base-<suite>.log" 2>&1; echo EXIT=$? >> "$LOG/base-<suite>.log"   # one line per suite
grep -hE "<the summary lines profile § Suites names>|EXIT=" "$LOG"/base-*.log > "$E/baseline.txt"
```

**Adopting the previous close.** Every link's close records, through the evidence runner,
before its runs and again after them: `git rev-parse HEAD`, `git rev-parse HEAD:<path>` for
every tree-key path profile § Suites names, and an empty `git status --porcelain` over those
paths. The next link adopts a suite's close count without running it when that suite's key
is unchanged and its paths are clean, and runs it otherwise.

`$E` is the link's evidence directory. `baseline.txt`, and the close's `close-suites.txt` made
the same way, are committed with the link's evidence: the scratchpad logs do not survive a
reboot, and the failure names the "same failures before and after" claim rests on are in
those lines.

Record **every summary number profile § Suites names, and `EXIT=`**, per suite — at least the
total, the file count and the failure count. A file that fails does not change the total, so
one number stays green over red gates.

<then profile § Suites' notes, verbatim — the flags a run must carry and why>

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
5. A red that proves a gate is saved raw — the minimal mutation diff, the full runner
   output, `EXIT=` — as a `.txt` under `docs/superpowers/plans/evidence/<wave>/` (`*.log`
   is gitignored), and named in the report. A red described only in prose is re-produced
   at close.
6. Every gate check runs through the evidence runner (profile § Evidence tooling), including
   one whose expected output is empty: an empty file cannot tell "nothing printed" from
   "never ran", and `EXIT=` can. A diff that must be empty uses `--exit-code`.
7. An absence check reads revisions, never the working tree, and takes its verdict from an
   exit code: it refuses a path missing at the task commit, runs the base control itself and
   refuses a base with no hit. The base is the link base unless the plan names an in-link
   commit for a reason, and an allowed hit's line number is re-measured at the task commit
   with `git grep -n`, never carried from the plan. A hand-written grep with its own exit
   test is not evidence. The exact command is profile § Evidence tooling.
8. A task that plants a red commits twice: the source first, then its evidence, so the plant's
   diff shows only the plant (`wave-run`'s reply contract). A plan step that names one commit
   for both is a conflict the implementer resolves by guessing.
<then profile § Rules for every link, verbatim, numbered on from 9>

## Do not

- <the neighbouring layer this wave must not touch>
- Fix code as the controller.
- Dispatch two implementers at once.
- Restore a mutation with `git checkout`, `git restore` or `git stash`: the tree is shared,
  and each of them also reverts what is not yours. Save a copy before mutating, restore
  from it, and confirm with `cmp` — or mutate a copy inside the container.
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

| | tasks | close allowance | total |
|---|---|---|---|
| Δ <suite name> | <±n> | <+n> | <±n> |
| Δ <other suite, if the link touches one> | <n> | <+n> | <n> |
| ratchets this link moves | <name>: <from> → <to> | | |

**Tasks** is what the plan's tasks add, counted from the plan. **Close allowance** is what
review fixes, evidence rounds and closing minors add after the tasks — the plan never
contains it, so it is estimated, and written here at prep, before the link starts. Default:
**+50% of the task Δ**, rounded up; the four links of one measured wave came in at +27% to
+109%. Raise it, with one line why, for a link whose plan has no recorded review or whose
tasks carry `opus`.

The report measures each column separately, and the 20% rule applies to each: a task Δ more
than 20% off the tasks forecast, or a close Δ more than 20% over the allowance, is the first
line of the report, not a footnote.

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
