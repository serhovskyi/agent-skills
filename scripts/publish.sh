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

git add skills/ agents/ .claude-plugin/
git commit -m "$MSG"
git push
echo "Published."
