---
name: wave-retro
description: Use when a wave or one of its links has closed and the owner wants to know what in the agents' environment should change so the next wave goes better - a gate stayed silent, a reviewer missed a defect, a session ran out of context, or an agent searched too long.
disable-model-invocation: true
---

# Retrospective on a wave

## Overview

The owner has asked for a **retrospective**. You are suggesting improvements to the coding
agents' **environment** to improve future runs. You change nothing yourself: the output is a list
of candidates, and the owner picks.

Core principle: **a mistake an agent made is a missing check, pointer or rule — not a reason to
write "be careful" anywhere.**

## Steps

1. **Read the records, not the dialogue.** Default to the wave just closed; the owner may name one
   link, or a single session. The records are, in this order:
   - `docs/superpowers/plans/<wave>-WAVE.md`, its `## Outcome` above all;
   - the link reports (`*-REPORT.md`) and every relay's **what this link learned** — relays
     (`<wave>-HANDOFF-*.md`) are deleted when the wave closes, so read them from the commit
     before that deletion;
   - each link's ledger `.superpowers/sdd/<wave>-<link>/progress.md` and the
     `task-<n>-review.md`, `task-<n>-audit.md` and `final-review-*.md` beside it, and the
     registry `.superpowers/sdd/<wave>/wave.md`;
   - `git log` of the wave's range: fix rounds, reverts, `partial` evidence commits.

   Session transcripts (`~/.claude/projects/<project-slug>/*.jsonl`) are the primary source when a
   record points at a failure it does not explain. Read them through a subagent with a fresh
   context window, one question per subagent; never load a transcript into your own context.

2. **Look for candidates** in the categories below. Each candidate names the record it came from.

3. **Present them to the owner, in order of severity**: what happened, where you read it, the
   change, and the file the change goes into.

## Categories

- **Navigation**: how easy was it for the agent to find the right files? Are there hidden
  dependencies between files? Would a **navigation pointer** make it easier? _Use when_ a session
  took a long time to find a piece of information.
- **Automated checks**: are there automated checks that could catch errors the agent made?
  Linting, typing, tests, filesystem linters? Read the repo's own check commands first (its build
  tool's `lint`/`check` targets, its CI workflow), so a check that already exists but sits unwired
  or silently broken is the finding, not a reinvention. A repo with no **guardrail** (no
  pre-commit hook and no CI job running its lint/typecheck/test command) is itself a finding.
  _Use when_ an agent made a mistake an automated check could have caught, or the repo has no
  guardrail at all.
- **Coding standards**: should a **reviewer agent** be given a new rule to enforce? Should an
  existing rule be removed or clarified? Classify the violation first: a **mechanical** one (a
  fixed syntactic pattern, a banned API, an import shape, a file-location rule) gets a
  deterministic check — a rule in the repo's own linter, a pre-commit hook, a CI job, or a
  `harness.toml` rule — whichever is cheapest. Default to building the check over writing the
  rule. Reserve the reviewer's rules and `CODING_STANDARDS.md` for genuine **judgement calls**.
  _Use when_ a reviewer failed to catch a mistake.
- **Gates**: did a gate stay silent — green over a defect, or red for someone else's reason? Name
  its class from the evidence auditor's catalogue, and the planted violation that would have made
  it bite. _Use when_ an audit returned NOT OURS or UNPROVEN, or a later link found a defect an
  earlier link's gates passed.
- **Global steering files**: are there instructions in `CLAUDE.md` / `AGENTS.md` that should move
  to coding standards, an automated check, or `.claude/wave-profile.md` instead? _Use when_ a
  steering file is particularly large — in the repo OR the user's global scope.
- **Tool economy**: did an agent make expensive tool calls that could be streamlined? Is there
  custom tooling that is particularly token-inefficient? _Use when_ a session ran out of context,
  or an agent made an expensive tool call.
- **No-ops**: instructions in steering files that don't change the agent's behavior. _Use when_
  the steering files are large and unwieldy.
- **Information access**: could the agents' access to information grow? Teeing dev-server logs,
  read-only access to third-party services. _Use when_ a crucial piece of information was not
  available to an agent.

## Where a change goes

| the lesson is about | it goes into |
|---|---|
| this repo's stack, commands, mirrors, traps | `.claude/wave-profile.md` |
| a command an agent must not run here | `.claude/harness.toml` |
| what a layer's reviewer should catch | that reviewer's agent file, or `CODING_STANDARDS.md` |
| a mechanical rule | the repo's linter, a hook or a CI job |
| the wave skills or shipped agents themselves | the waveflow clone — in generic words only, since it is public; never this repo's names, paths or output |

A candidate that edits a skill or an agent is written with `superpowers:writing-skills`.

## Reference

### Implementation vs review

Every task goes through two stages: implementation and review. The implementer carries the most
**context pressure**: it explores, writes code and debugs failures. The reviewer carries the
least: it receives a diff, so it explores nothing and usually writes and debugs nothing.

So the reviewer, not the implementer, imposes coding standards. A rule added to an implementer's
brief competes with everything else in its context; the same rule in a reviewer's agent file is
read against every diff.

### Files

- `CLAUDE.md` / `AGENTS.md` are pushed into the context of every agent working in the repo. Use
  them very sparingly, usually only for **navigation pointers** to other files.
- `CODING_STANDARDS.md` is read during review, not implementation. Add navigation pointers to
  docs folders if it grows beyond about 1,000 lines.
- Docs are reference files, pointed at by other files. Look for an existing doc before writing a
  new one.
- Skills are for reference an agent should be able to find by description, or for commands the
  owner invokes.

---

Adapted from the `retro` skill of [mattpocock/skills](https://github.com/mattpocock/skills),
© 2026 Matt Pocock, MIT — see [CREDITS.md](CREDITS.md) and [LICENSE](LICENSE).
