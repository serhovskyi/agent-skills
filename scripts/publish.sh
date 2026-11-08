#!/usr/bin/env bash

# Commit and push any changes to skills in this repo.
# Usage: bash scripts/publish.sh ["optional commit message"]
#
# If you installed skills via link-skills.sh, editing ~/.claude/skills/<name>/SKILL.md
# edits the file directly in this repo — just run this script afterwards.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
MSG="${1:-"update skills"}"
PUBLISHED=(skills/ agents/ harness/ scripts/ .claude-plugin/ .github/ README.md LICENSE THIRD-PARTY-NOTICES.md .gitignore Makefile ruff.toml package.json)

cd "$REPO"

if [ -z "$(git status --porcelain -- "${PUBLISHED[@]}")" ]; then
  echo "Nothing to publish — no changes detected."
  exit 0
fi

# A local, uncommitted list of words that must never reach this public repo: names, paths
# and identifiers of the private projects these skills are developed in. .git/info is never
# cloned, so a fresh clone has none until it is created.
DENYLIST="$REPO/.git/info/publish-denylist"
if [ ! -f "$DENYLIST" ] && [ "${PUBLISH_WITHOUT_DENYLIST:-}" != 1 ]; then
  cat >&2 <<EOF
Refused: $DENYLIST does not exist.
It lists the words that must never reach this public repo (names, paths and identifiers of
the private projects these skills are developed in), one per line, # for comments.
Create it; an empty file (touch .git/info/publish-denylist) states there is nothing to keep out.
PUBLISH_WITHOUT_DENYLIST=1 publishes once without it.
EOF
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
WORDS="$TMP/words"
: > "$WORDS"
if [ -f "$DENYLIST" ]; then
  sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$DENYLIST" | grep -v -e '^#' -e '^$' > "$WORDS" || true
fi

# The scan stages into a scratch index, so a refusal leaves the real one exactly as it was.
REAL_INDEX="$(git rev-parse --git-path index)"
export GIT_INDEX_FILE="$TMP/index"
if [ -f "$REAL_INDEX" ]; then
  cp "$REAL_INDEX" "$GIT_INDEX_FILE"
fi
git add -- "${PUBLISHED[@]}"

GIT=(git -c core.quotePath=false)
: > "$TMP/hits"
: > "$TMP/report"

# check <label> <file> [binary]: a binary's matching "lines" are not worth printing.
check() {
  if grep -naiF -f "$WORDS" -- "$2" > "$TMP/hit"; then
    cat "$TMP/hit" >> "$TMP/hits"
    if [ -n "${3:-}" ]; then
      echo "  in $1 (binary)" >> "$TMP/report"
    else
      echo "  in $1:" >> "$TMP/report"
      head -5 "$TMP/hit" | cut -c1-200 | sed 's/^/    /' >> "$TMP/report"
    fi
  fi
}

# A change reaches the remote as diff text, file names and binary blobs; each is read.
# scan_change <label> <blob rev prefix: ":" for the index, "<sha>:" for a commit> <git diff...>
scan_change() {
  local label=$1 blob=$2
  shift 2
  "$@" -p -U0 --no-color --no-ext-diff | grep -a '^+' > "$TMP/added" || true
  check "$label, added lines" "$TMP/added"
  "$@" --name-only --diff-filter=ACR > "$TMP/names"
  check "$label, file names" "$TMP/names"
  "$@" --numstat --diff-filter=ACR | awk -F'\t' '$1 == "-" && $2 == "-" { print $3 }' > "$TMP/binaries"
  while IFS= read -r path; do
    echo "warning: $label adds a binary file; look at it before it is public: $path" >&2
    git cat-file blob "$blob$path" > "$TMP/blob"
    check "$label, $path" "$TMP/blob" binary
  done < "$TMP/binaries"
}

scan_change "the staged diff" ":" "${GIT[@]}" diff --cached

printf '%s\n' "$MSG" > "$TMP/message"
check "the commit message" "$TMP/message"

# git push publishes every local commit the remote lacks, not only the one made here.
if git rev-parse -q --verify HEAD > /dev/null; then
  branch="$(git branch --show-current)"
  if [ -n "$branch" ] && git rev-parse -q --verify "refs/remotes/origin/$branch" > /dev/null; then
    unpushed=(HEAD --not "refs/remotes/origin/$branch")
  else
    unpushed=(HEAD --not --remotes)
  fi
  for commit in $(git rev-list --reverse "${unpushed[@]}"); do
    label="unpushed commit $(git log -1 --format='%h (%s)' "$commit")"
    git log -1 --format=%B "$commit" > "$TMP/message"
    check "$label, message" "$TMP/message"
    scan_change "$label" "$commit:" "${GIT[@]}" diff-tree -r --root -m --first-parent --no-commit-id "$commit"
  done
fi

if [ -s "$TMP/report" ]; then
  {
    echo "Refused: words from .git/info/publish-denylist would be published:"
    while IFS= read -r word; do
      if grep -qaiF -- "$word" "$TMP/hits"; then echo "  $word"; fi
    done < "$WORDS"
    cat "$TMP/report"
    echo "Nothing was committed or pushed, and the index is as it was before this run."
    echo "Reword them generically (an unpushed commit needs amending or a rebase), then re-run."
  } >&2
  exit 1
fi

unset GIT_INDEX_FILE
git add -- "${PUBLISHED[@]}"
git commit -m "$MSG"
git push
echo "Published."
