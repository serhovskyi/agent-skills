#!/usr/bin/env bash

# Commit and push any changes to skills in this repo.
# Usage: bash scripts/publish.sh ["optional commit message"]
#
# If you installed skills via link-skills.sh, editing ~/.claude/skills/<name>/SKILL.md
# edits the file directly in this repo — just run this script afterwards.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
MSG="${1:-"update skills"}"

cd "$REPO"

if git diff --quiet && git diff --cached --quiet; then
  echo "Nothing to publish — no changes detected."
  exit 0
fi

git add skills/ agents/ harness/ scripts/ .claude-plugin/ .github/ README.md .gitignore

# A local, uncommitted list of words that must never reach this public repo: names, paths
# and identifiers of the private projects these skills are developed in.
DENYLIST="$REPO/.git/info/publish-denylist"
if [ -f "$DENYLIST" ]; then
  added=$(git diff --cached -U0 | grep -E '^\+' | grep -vE '^\+\+\+ ' || true)
  hits=$(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$DENYLIST" | while IFS= read -r word; do
    if printf '%s\n' "$added" | grep -qiF -- "$word"; then echo "$word"; fi
  done)
  if [ -n "$hits" ]; then
    echo "Refused: the staged diff adds words from .git/info/publish-denylist:" >&2
    printf '  %s\n' $hits >&2
    git diff --cached -U0 | grep -niF -f <(printf '%s\n' $hits) | head -20 >&2
    echo "Nothing was committed. Reword them generically, then re-run." >&2
    git reset -q
    exit 1
  fi
fi
git commit -m "$MSG"
git push
echo "Published."
