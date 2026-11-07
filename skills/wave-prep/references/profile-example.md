# Repo profile — a worked example

A filled-in `.claude/wave-profile.md` for an invented repo: a Django API in `api/`, a React +
Vite + Vitest client in `web/`, Postgres in Docker Compose. Nothing here is a default — copy
the **shape**, not the values. The empty template, with what each section is for, is
`profile.md`.

Notice what every section does: it gives a command that runs as written, or `none`, and every
rule carries the failure it exists because of.

```markdown
# Wave profile — example-shop

Read by `wave-prep`, `wave-run` and `wave-close`. The repo's facts, not a wave's: a lesson
goes here only when it is about this repo's stack.

## Suites

| suite | command | summary lines to record | tree-key paths |
|---|---|---|---|
| api | `docker compose exec -T api pytest -q -p no:randomly` | `passed`, `failed`, `^FAILED` | `HEAD:api` + `HEAD:compose.yaml` |
| web | `docker compose exec -T web npm test -- --run` | `Tests`, `Test Files`, `failed` | `HEAD:web` |

- **Never both suites at once**: the dev box has 8 GB, and the two together swap until the
  api suite times out on fixtures that have nothing to do with the change.
- **`-p no:randomly` is not optional for a baseline**: ordering is randomised by default, and
  two baselines of one tree then disagree on which test is flaky.
- `api/pytest.ini` sets `filterwarnings = error`: a new deprecation warning is a red test.

## Generated mirrors

- `web/src/api/schema.d.ts` — regenerated from the OpenAPI spec by `npm run gen:api`, which
  `npm test` runs as a pretest step.
- `api/openapi.yaml` — written by `manage.py spectacular` on every `make lint`.

## Reviewers

| roster | agents |
|---|---|
| plan reviewers | `solution-architect-reviewer` + `django-plan-reviewer` (api), `react-plan-reviewer` (web) |
| code reviewers | `api/` → `django-code-reviewer`; `web/` → `react-code-reviewer` |
| evidence auditor | `gate-evidence-auditor` |

## Evidence tooling

- **Evidence runner:** `none` — the skills' fallback: the command on its own line, then
  `<cmd> >> <file> 2>&1; echo "EXIT=$?" >> <file>`.
- **Absence check:** `none` — every absence claim is a `git grep` at the task commit, its exit
  code recorded, with the same grep at the link base shown to hit.
- **Suite summary:** `none`.

## Reply contract

    Before every commit run `docker compose exec -T web npx eslint --max-warnings 0 <files relative to web/>` and `docker compose exec -T web npx tsc --noEmit` for web files; `docker compose exec -T api ruff check <files relative to api/>` and `docker compose exec -T api ruff format --check <files relative to api/>` for api files.
    A Vitest `-t` filter is a regex: escape `( ) [ ] . ? + *` in a test name. A pytest `-k` filter is an expression: quote it, and never pass a test's full name with brackets.

The lint line exists because "lint clean" in a report was twice false: once eslint warnings
rode three commits until the full `make lint` went red, once `tsc` failed on a change eslint
passed.

The filter line exists because `-t "reset() clears"` matched no test — `()` is an empty
group — and the run reported 0 failed, EXIT=0.

## Run notes

- `npm test -- --project unit` selects nothing: the script already names its projects. Read
  the project from the `|name|` tag in the output instead.
- Vitest colours its summary; a grep over a repeated run passes `-e NO_COLOR=1` to
  `docker compose exec`, or it counts zero runs.
- Page frames for the final review: 1280 and 375 px, light and dark.

## Gate roster

    ls web/src/__guards__/
    ls api/tests/architecture/
    cat api/.importlinter

## Prep checks

- A route name a web plan navigates to exists as a leaf in `web/src/routes.tsx`.
- The `web` image is Alpine: its grep is BusyBox and rejects `--include`. A grep a plan runs
  there is rewritten for the host.

## Adaptations

- **No worktree.** The Postgres volume is external, so a worktree cannot bring the stack up.
  Work on a branch in place: `git switch -c wave/<link>` from a fresh `main`.
- **The tree is shared.** Foreign uncommitted work at preflight is a stop.

## Rules for every link

9. `test_layers_are_respected` only checks modules `.importlinter` names, so a link that
   deletes a module never lists it as a moved gate.

## Close report

| line | command |
|---|---|
| LINT | `make lint` |
| boundaries | `lint-imports` — broken contracts, must be 0 |
| TYPES | `docker compose exec -T web npx tsc --noEmit` |
| CI | `make ci` |
```
