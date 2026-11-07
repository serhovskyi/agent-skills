#!/usr/bin/env bash

set -euo pipefail

# The editing workflow for the wave-harness plugin, the way link-skills.sh is for the skills:
# registers harness/hooks/hooks.json in the user settings with paths into this clone, and puts
# the evidence tools on PATH as symlinks. Edit in place, publish with scripts/publish.sh.
# Installing the plugin instead (/plugin install wave-harness) is the read-only route; do not
# run both, or every hook fires twice.
#
#   bash scripts/link-harness.sh            # link (idempotent)
#   bash scripts/link-harness.sh --unlink   # remove this clone's hooks and tools

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HARNESS="$REPO/harness"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
BIN="${WAVE_HARNESS_BIN:-$HOME/.local/bin}"
MODE="${1:-link}"

python3 - "$HARNESS" "$SETTINGS" "$MODE" <<'PY'
import json
import shutil
import sys
from pathlib import Path

harness, settings, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
marker = str(harness / "hooks")
data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
if settings.exists():
    shutil.copy2(settings, settings.with_suffix(".json.bak"))

hooks = data.setdefault("hooks", {})
for event in list(hooks):
    kept = []
    for entry in hooks[event]:
        entry["hooks"] = [h for h in entry.get("hooks", []) if marker not in h.get("command", "")]
        if entry["hooks"]:
            kept.append(entry)
    if kept:
        hooks[event] = kept
    else:
        del hooks[event]

if mode != "--unlink":
    spec = json.loads((harness / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for event, entries in spec.items():
        for entry in entries:
            linked = json.loads(json.dumps(entry).replace("${CLAUDE_PLUGIN_ROOT}", str(harness)))
            hooks.setdefault(event, []).append(linked)
            for hook in linked["hooks"]:
                print(f"hook {event}/{entry.get('matcher') or '*'} -> {hook['command']}")
if not hooks:
    del data["hooks"]

settings.parent.mkdir(parents=True, exist_ok=True)
settings.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"{'unlinked from' if mode == '--unlink' else 'registered in'} {settings} (backup: .json.bak)")
PY

mkdir -p "$BIN"
for tool in evidence-run absence-check suite-summary; do
  target="$BIN/$tool"
  if [ "$MODE" = "--unlink" ]; then
    [ -L "$target" ] && [ "$(readlink -f "$target")" = "$HARNESS/bin/$tool" ] && rm "$target" && echo "unlinked $tool"
  else
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      echo "error: $target exists and is not a symlink; move it aside and re-run." >&2
      exit 1
    fi
    ln -sfn "$HARNESS/bin/$tool" "$target"
    echo "linked $tool -> $HARNESS/bin/$tool ($BIN)"
  fi
done

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "note: $BIN is not on PATH; add it, or call the tools by full path." ;;
esac
echo "Restart Claude Code sessions: hooks are read at session start."
