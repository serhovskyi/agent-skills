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

## The repo profile

This skill names no toolchain. The repo's suite commands, generated mirrors, reviewer
roster, evidence runner, the lines it adds to the reply contract and the traps of its stack
live in `.claude/wave-profile.md` (`wave-prep` writes it when it is missing). Wherever this
skill says **profile § X**, read that section; read nothing else of the profile into a
dispatch.

The **evidence runner** is profile § Evidence tooling: a command that records a command
line, its output and an `EXIT=` printed by the shell that ran it into one evidence file. A
repo without one writes the command into the file, then runs
`<cmd> >> <file> 2>&1; echo "EXIT=$?" >> <file>`.

## Preflight — every predicate, before the first dispatch

```bash
git status --porcelain                              # empty, or stop
git status --porcelain <generated mirrors>          # empty, or stop
git branch --show-current                           # the link branch, or stop
git log --oneline <link base>..HEAD                 # exactly the commits the ledger records, or stop
git merge-base --is-ancestor <prev-branch> main     # previous link is in main
```

`<generated mirrors>` is profile § Generated mirrors — tracked files a tool regenerates (an
OpenAPI client, a lockfile, a schema dump). Every `lint`, `test` and `type-check` can
silently rewrite one, so a dirty mirror turns an unrelated command into an unexplained diff.

`<link base>` is `git rev-parse HEAD` at the moment the link branch is created — the
controller creates the ledger then and writes that sha as its first line. At a fresh
start the range is empty; when picking up a session that died mid-link it holds that
session's commits, and every one must appear in the ledger. Where sessions share a tree and
commit as the same git user, the ledger — not the author field — is what tells a foreign
commit from yours.

Then the baseline, by the WAVE's **Baseline method** — its commands and the numbers it
says to record, into the ledger before anything else. This skill does not carry its own
copy of those commands.

A suite is **adopted, not re-run**, when the previous link's close recorded its tree key and
the key still holds: `git rev-parse HEAD:<paths>` equals the recorded hashes and
`git status --porcelain -- <paths>` is empty, for the paths profile § Suites names per
suite. Record the adopted file and both hash sets in the ledger. A close that recorded no
key is run. Commits after the close that touch none of those paths — the close evidence,
the relay, the registry — do not move a key; anything that does, a neighbour's commit
included, does.

Then the link's own predicates from its start prompt.

**Any red predicate is a stop, not a note.** Foreign uncommitted work means another
session owns this tree. An unmergeable previous link means the wave is not ready. A red
suite means "was green → is green" has stopped being evidence. Name the cause, ask, wait.

## The per-task loop

For each task, in order, one at a time:

1. `"$SDD/task-brief" <plan> <n>` → a path. `SDD` is the
   `superpowers:subagent-driven-development` scripts directory.
2. Write `git rev-parse HEAD` into the ledger as the task base, then dispatch the
   implementer **with the model named** from the link prompt's table.

   The dispatch prompt is exactly five parts, in this order: one line of context · the
   brief path · interfaces produced by earlier tasks · the report path · the reply
   contract. Anything else you are tempted to add is already in the brief.

   The reply contract is fixed text, because no brief carries it: the lines below,
   verbatim, with profile § Reply contract inserted where marked, also verbatim.

   ```
   Run every command in the foreground; never end your turn while one is running.
   If `git branch --show-current` is not <link branch>, stop and report; never switch branches.
   Before every commit run the lint gates below on the files the task touched, through `<evidence runner> <file>` so each command and its `EXIT=` land in the task's evidence file. A non-zero exit is fixed before the commit, never committed.
   <profile § Reply contract, verbatim>
   A red that proves a gate: commit the implementation first, so the diff shows only the plant; then cp the files, mutate, `<evidence runner> <file> git status --porcelain` and `<evidence runner> <file> git diff -- <files>` first, then the run, then restore from the copy, cmp, and `git diff --exit-code --stat -- <files>`.
   Your commits carry code and tests only. Evidence files are never in them: they stay in the working tree under the task's evidence directory, and the controller lands them after the audit as the task's one record commit.
   Every `EXIT=` you report or record is printed by the shell that ran the command (the evidence runner, or `; echo "EXIT=$?"` on the runner itself, never after a pipe); never type one, and a run without one is run again.
   Reply with exactly four lines: status · commits · tests (one line, Δ) · caveats.
   ```

   The lint line exists because an implementer's "lint clean" is a claim, not a reading:
   formatting warnings rode four commits of one link until a later task's full lint went
   red, and in another wave a report called its files clean while the formatter check was
   red on them — the task review and the audit both passed it. Through the evidence runner
   the command and its exit are in the file, and the controller reads them rather than the
   claim.

   The planted-red line exists because the rule lived only in the WAVE: one link shipped 23
   evidence files whose mutation was described in prose, and the auditor had to read each
   red's cause back from its failure text. Every close round whose brief carried the form
   produced the diff. Two implementers planted before committing and recorded an empty or
   implementation-mixed mutation diff; the ones that committed first did not.

   The code-only line exists because evidence was landing one file per commit, from the
   implementer and the controller in turn: one link closed with 29 commits, 17 of them
   evidence. Every one of those commits is a ledger row and a `git log <base>..HEAD` line
   the controller reads back. The task's record is one commit (step 6), so nobody but the
   controller commits under the evidence directory.

   The exit line exists because a close record once carried an `EXIT=0` typed by hand
   beside a suite log with no exit at all, and because `git diff --stat` exits 0 on a
   difference: the restore check proved nothing until `--exit-code`.

   A full suite log is never committed: the evidence records its command, the summary lines
   profile § Suites names and the runner's `EXIT=`. One full log reached 85 MB.

   An implementer that backgrounded its suite once ended with no hand-back and no commit;
   another found a shared tree on a neighbouring session's branch and switched it back,
   moving that session's work under it. **Implementers never switch branches.** The
   controller switches only where a step of these skills says so — the link branch at
   start, `main` at the `wave-close` merge.

   **You do not open the plan to write a dispatch.** A task that looks subtle is subtle in
   its own text, and the brief is that text — restating it in the prompt means the
   implementer reads it twice and you read it once too many. If you catch yourself
   reaching for the plan to warn the implementer about something, that warning belongs to
   the reviewer's attention list, not to the dispatch.
3. The implementer writes, tests, commits, writes its report **to a file**, and returns
   four lines: status, commits, one line about tests, caveats.

   Then check the branch against the reply, before the review:

   ```bash
   git branch --show-current                  # still the link branch
   git log --oneline <task base>..HEAD        # exactly the commits the reply names
   ```

   `<task base>` is the sha written into the ledger in step 2 — the same sha step 4 passes
   to `review-package` as `<base>`.

   A commit the reply does not name is foreign — another session committed on the shared
   tree mid-task. It is a stop, not a note: it rides into the review package and the merge
   unless someone decides otherwise. Ask the owner whether it stays on the branch.
4. `"$SDD/review-package" <plan> <base> <head>` → a path. Dispatch the reviewer **by the
   layer the task touched**, using the wave's reviewer roster (`WAVE.md` § Reviewers) —
   one code-reviewer per layer, and **both** for a vertical task: same diff file, two
   lenses. The prompt carries the brief path, the report path, the diff path and the
   wave's gate table. Nothing else: the persona lives in the agent, not in your prompt.

   Reviewer seats are read-only, so a dispatch never names a file for the reviewer to
   write. The verdict comes back as the reply; the controller saves it as
   `task-<n>-review.md` (or `final-review-<lens>.md`) next to the ledger. A reviewer
   handed a review path promises the file and writes nothing, and the ledger is left
   pointing at a file that does not exist.
5. Fix rounds if needed, then the gate audit; rounds 4-5 escalate one tier above whatever
   stalled.

   A green under a name filter is one reading, not determinism. A route witness passed a
   task, a close suite and a fix round, then failed 3 of 8 on clean `main`; the auditor
   accepted it only from a 20-run repeat whose evidence names the sha it ran on. Likewise,
   before the ledger records a plant's "prediction miss", re-run the same plant once on the
   same blob: two outcomes from one plant are timing, not the plan.

   **A task that claims a moved gate or a planted red is audited before it is complete.**
   After the reviewer approves, if the task's plan or brief claims either, dispatch the
   wave's evidence auditor with the ledger, the task's report file and that task's rows of
   the gate table — not the diff. The task is not complete until the audit HOLDS; on
   INCOMPLETE the implementer fills the missing evidence and the task is audited again. The
   controller saves the verdict as `task-<n>-audit.md` next to the ledger. A task that
   claims no gate gets no audit.

   The per-task audit exists because the final audits of two consecutive links returned
   EVIDENCE INCOMPLETE and cost close rounds. Run per task in the next two, it returned
   INCOMPLETE four times, each filled before the next task began; the final audit still
   found one row.
6. Land the task's record, then write the ledger and print the status line.

   The record is one commit, `docs(evidence): <link> T<n>`, made once the audit holds (or
   the review approves, for a task with no gate): every evidence file the task produced —
   the implementer's red, green, plants and lint, each fix round's, and the controller's
   own runs at the task head (full suite, full lint, type-check). The link close lands the
   same way, as one `docs(evidence): <link> close`.

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
| Your own suite runs go in the background, into a log file; read the summary lines and `EXIT=` | full suite output is thousands of lines. This is the controller's rule; implementers run in the foreground (the reply contract) |
| The `EXIT=` you read is one the runner's shell wrote into the log; a log without one is re-run, never summarised | a typed or missing exit code is the one number nobody re-checks, and `\| tail` reports the tail's |
| Your own targeted runs follow profile § Run notes | the controller's plant runs are evidence too, and go green about nothing the same way |
| Never read a subagent transcript | they are larger than everything else combined |
| The ledger is your memory | after a compaction, trust the ledger and `git log`, not recollection |

## Status after every task

Print this — the owner should never have to ask what is left:

```
✅ Task 2/4 · link B2 (5 of 6) · sonnet · 2 fix rounds
   suite 1796 → 1800 (Δ +4: tasks +3 vs +3, close +1 of allowance +2, failed 0)
   remaining: 2 tasks in link · 5 tasks in wave · 1 link after this
```

Δ, never absolutes. "Suite green" is not a status. The `tasks` and `close` figures are the
link's running totals against the link's forecast, so a 20% divergence is judged at the
link's last task, not at task 1. Tests the task's plan text asks for count
against the **tasks** forecast; tests a review fix or evidence round adds count against the
**close allowance** (WAVE link prompt, Forecast).

## Final link review — always opus, two lenses, and the spec when the roster names it

1. **The code**: the whole link's diff against its base — every code-reviewer whose layer
   the link touched, all on opus, all over the **whole** range. Each has so far seen only
   its own tasks; the seams between tasks are what this pass exists for.
2. **The evidence against the logs**: the wave's evidence auditor (`WAVE.md` § Reviewers;
   a `gate-evidence-auditor` agent is the reference implementation, and a repo without one
   must supply the role before trusting this stage). It gets the ledger, the report files,
   the per-task `task-<n>-audit.md` verdicts and the plan's gate table — **not** the diff.
   Did each gate this link claims to have moved actually go red, and for our reason? A gate
   that was already red, or red because of a neighbouring session, proves nothing about
   this link. It never moves the tree: a gate it cannot prove read-only comes back UNPROVEN
   with the command, and running that command is yours.
3. **The diff against the spec**, only when `WAVE.md` § Reviewers names a spec reviewer
   (a `spec-reviewer` agent is the reference implementation) **and** its `**Spec:**` line
   is a path. It gets the same whole-link diff file as the first lens, the spec path from
   `WAVE.md`, and the link's plan path — the reviewer reads the plan, you do not. Save its verdict as `final-review-spec.md` and
   report it beside the other lenses, never merged into them or ranked against them: a
   link can pass the code and still build the wrong thing.
4. **The page, by eye**, when the link changes a screen: the controller shoots light and
   dark frames at desktop and mobile width against the running app and compares them with
   the signed-off mockup, before the lenses above. A value glued to its unit and
   stripped of its muted style («11,4г» for «11,4 г») passed the task review, both final
   lenses' first pass and the whole suite; only the frames showed it.

Review is a stage of the link, not an option. A wave that skipped it found four defects
in a later review that its green suite never saw.

## Gates: the ways they stay silent

Watch for these while reviewing — each has shipped in a real codebase:

- **Path-scoped rules.** Files leave the perimeter; the gate walks a smaller tree and
  stays green.
- **Pinned equalities.** A count that must be lowered in the same commit, or the lint stays
  red for the rest of the link. Read the new value from the failure; never guess it.
- **Discriminating pairs.** Half of a `not.toContain(<file>)` becomes true *by absence*
  when the file is deleted.
- **Environment-green.** A gate that passes because of how it was run, not because of what
  the code does.

One more, below the gates: **a mock agrees with its own fixture.** A unit test that asserts
`push({ name: X })` on a mocked router passes for any `X`, including a layout parent that
renders an empty view. Navigation to a route name a task introduces or copies from the plan
needs one case on the real router that lands where the user should — a plan's route name
shipped a blank page past four green reviews this way.

These five are the controller's attention list. The full catalogue — twelve classes, plus
how a number rots and how an exit code hides behind `| tail` — lives in the evidence
auditor agent, and is not to be copied back here.

## When the link cannot finish

Evidence still in the working tree lands first, as `docs(evidence): <link> T<n> partial`, so
the next session adopts a committed record and not loose files. Then record in the ledger
where it stopped, what is committed, and what the next session needs.
`wave-close` reads the ledger, so a link can be closed from a fresh session; the close
prompt it starts from is written by this session, as `wave-close` describes under "When
closing moves to a fresh session".

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
