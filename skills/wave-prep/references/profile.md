# Repo profile template — `.claude/wave-profile.md`

The repo's half of the wave skills. The skills name no toolchain; every value they need from
the repo is a section here, cited as **profile § <section>**. Keep the section names exactly:
the skills look them up by name.

Write only what is true of this repo. A section with nothing to say holds `none`, never a
placeholder: an empty section reads as "not filled in", `none` reads as "checked".

`profile-example.md`, next to this file, is the same template filled in for an invented repo —
read it for the shape a finished profile has.

```markdown
# Wave profile — <repo>

Read by `wave-prep`, `wave-run` and `wave-close`. The repo's facts, not a wave's: a lesson
goes here only when it is about this repo's stack.

## Suites

One row per suite. The commands are copied into each WAVE's Baseline method; the tree keys
decide when a link may adopt the previous close instead of re-running.

| suite | command | summary lines to record | tree-key paths |
|---|---|---|---|
| <name> | `<exact command>` | <e.g. `Tests`, `Test Files`, `failed`> | `<paths whose tree hash moves this suite>` |

<Notes a run must respect, with the reason for each: flags that are not optional, suites that
must never run together on this host, settings that turn a warning into a failure.>

## Generated mirrors

<Tracked files a tool rewrites — API client, lockfile, schema dump — or `none`.>

## Reviewers

| roster | agents |
|---|---|
| plan reviewers | <architecture reviewer> + <one per layer> |
| code reviewers | <layer → agent, one row each, e.g. `src/server/` → backend-code-reviewer> |
| evidence auditor | <usually gate-evidence-auditor> |

## Evidence tooling

- **Evidence runner:** `<command> <file> <cmd…>` — writes the command line, the output and an
  `EXIT=` printed by its own shell into `<file>`. `none` means the skills' fallback.
- **Absence check:** `<command and flags>` — reads revisions, runs its own base control, and
  its exit is the verdict. `none` means every absence claim is argued by hand and audited.
- **Suite summary:** `<command>`, if the repo has one, or `none`.

## Reply contract

Lines appended verbatim to every implementer dispatch, after the generic lint line. Each is a
command with its exact form, e.g.:

    Before every commit run `<evidence runner> <file> <linter> <files>` and `<evidence runner> <file> <type-check>`.
    Run a spec under its own project/config: <how this repo's test runner selects one>.

Under the block, one paragraph per line saying which failure it exists because of.

## Run notes

<Traps of this stack that make a targeted run read green while running nothing — how a name
filter is parsed, which flag selects nothing, which output is coloured and breaks a grep.
One bullet each, with the measurement.>

## Gate roster

The commands `wave-prep` runs to list every gate file for its judgment subagents:

    ls <lint/guard test directories>
    cat <import/boundary contract config>

## Prep checks

<Checks `wave-prep` step 6 runs against every plan beyond the generic ones — e.g. where route
names resolve, which container's grep lacks which flags.>

## Adaptations

<Lines copied into each WAVE's "Repo adaptations": worktree or branch in place, whether the
tree is shared, branch prefix.>

## Rules for every link

<Rules appended to the WAVE's numbered list, after the generic eight — e.g. a gate that never
counts as moved for a reason specific to how it is written.>

## Close report

| line | command |
|---|---|
| LINT | `<lint command>` |
| boundaries | `<rule, or none>` |
| TYPES | `<type-check command, or none>` |
| CI | `<ci command>` |
```
