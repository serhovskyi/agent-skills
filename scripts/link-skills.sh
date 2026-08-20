#!/usr/bin/env bash

set -euo pipefail

# Links all skills in the repository into the local skill directories used by
# each agent harness:
#   - ~/.claude/skills   — Claude Code
#   - ~/.agents/skills   — Agent-Skills-standard harnesses (OpenCode, Cursor, etc.)
# and every agent in agents/ into ~/.claude/agents.
# Each entry is a symlink into this repo, so `git pull` keeps installed skills
# up to date automatically.
#
# This is the editing workflow: the linked files ARE the repo, so edit in place
# and publish with scripts/publish.sh. Installing the plugin instead
# (/plugin marketplace add serhovskyi/agent-skills) gets you the same content
# read-only, and the two are alternatives — do not run both.

REPO="$(cd "$(dirname "$0")/.." && pwd)"

DESTS=("$HOME/.claude/skills" "$HOME/.agents/skills")

names=()
srcs=()

while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  names+=("$(basename "$src")")
  srcs+=("$src")
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/deprecated/*' -print0)

for DEST in "${DESTS[@]}"; do
  if [ -L "$DEST" ]; then
    resolved="$(readlink -f "$DEST")"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $DEST is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$DEST\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$DEST"

  for i in "${!names[@]}"; do
    name="${names[$i]}"
    src="${srcs[$i]}"
    target="$DEST/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      rm -rf "$target"
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done

# Agents are a separate harness mechanism from skills: they live in
# ~/.claude/agents and are linked per FILE, not per directory.
AGENT_DEST="$HOME/.claude/agents"

if [ -d "$REPO/agents" ]; then
  if [ -L "$AGENT_DEST" ]; then
    resolved="$(readlink -f "$AGENT_DEST")"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $AGENT_DEST is a symlink into this repo ($resolved)." >&2
        echo "Remove it (rm \"$AGENT_DEST\") and re-run; the script will recreate it as a real dir." >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$AGENT_DEST"

  for agent_md in "$REPO"/agents/*.md; do
    [ -e "$agent_md" ] || continue
    name="$(basename "$agent_md")"
    target="$AGENT_DEST/$name"

    if [ -e "$target" ] && [ ! -L "$target" ]; then
      rm -f "$target"
    fi

    ln -sfn "$agent_md" "$target"
    echo "linked agent $name -> $agent_md ($AGENT_DEST)"
  done
fi
