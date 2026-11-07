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

usage() {
  echo "usage: bash scripts/link-harness.sh [--link | --unlink]" >&2
  exit 2
}

[ $# -le 1 ] || usage
case "${1:-}" in
  "" | --link) MODE=link ;;
  --unlink) MODE=unlink ;;
  *) usage ;;
esac

# Resolved, so a clone reached through a symlink registers under the same paths every time.
REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd -P)"
HARNESS="$REPO/harness"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
BIN="${WAVE_HARNESS_BIN:-$HOME/.local/bin}"

python3 - "$HARNESS" "$SETTINGS" "$MODE" <<'PY'
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

harness, settings, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
if settings.is_symlink():
    settings = settings.resolve()
spec = json.loads((harness / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
PLUGIN_COMMAND = re.compile(r'^python3 "\$\{CLAUDE_PLUGIN_ROOT\}/(?P<script>[^"]+)"$')
names = {
    Path(m["script"]).name
    for entries in spec.values()
    for entry in entries
    for hook in entry["hooks"]
    if (m := PLUGIN_COMMAND.match(hook["command"]))
}


def ours(command: str) -> bool:
    """A registration from this clone, or from wherever it lived before it was moved."""
    if str(harness / "hooks") in command:
        return True
    return "/harness/hooks/" in command and any(name in command for name in names)


def guarded(command: str) -> str:
    """A PreToolUse or Stop hook that exits 2 blocks every Bash call or every turn's end, in
    every repo; a hook file gone with a moved clone must switch the guards off, loudly."""
    m = PLUGIN_COMMAND.match(command)
    if not m:
        return command.replace("${CLAUDE_PLUGIN_ROOT}", str(harness))
    path = str(harness / m["script"])
    message = json.dumps(
        {
            "systemMessage": f"wave-harness: {path} is missing; its guards are OFF. "
            "Re-run scripts/link-harness.sh or --unlink."
        }
    )
    script = '[ -f "$1" ] && exec python3 "$1"; printf "%s\\n" "$2"'
    return f"bash -c {shlex.quote(script)} wave-harness {shlex.quote(path)} {shlex.quote(message)}"


data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
backups = []
if settings.exists():
    original = settings.with_name(settings.name + ".orig")
    if not original.exists():
        shutil.copy2(settings, original)
        backups.append(original.name)
    stamped = settings.with_name(f"{settings.name}.{datetime.now():%Y%m%d-%H%M%S-%f}.bak")
    shutil.copy2(settings, stamped)
    backups.append(stamped.name)

hooks = data.setdefault("hooks", {})
for event in list(hooks):
    kept = []
    for entry in hooks[event]:
        entry["hooks"] = [h for h in entry.get("hooks", []) if not ours(h.get("command", ""))]
        if entry["hooks"]:
            kept.append(entry)
    if kept:
        hooks[event] = kept
    else:
        del hooks[event]

if mode == "link":
    for event, entries in spec.items():
        for entry in entries:
            linked = json.loads(json.dumps(entry))
            for hook in linked["hooks"]:
                hook["command"] = guarded(hook["command"])
                print(f"hook {event}/{entry.get('matcher') or '*'} -> {hook['command']}")
            hooks.setdefault(event, []).append(linked)
if not hooks:
    del data["hooks"]

settings.parent.mkdir(parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(dir=settings.parent, prefix=f".{settings.name}.")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if settings.exists():
        shutil.copymode(settings, temporary)
    os.replace(temporary, settings)
except BaseException:
    Path(temporary).unlink(missing_ok=True)
    raise
verb = "unlinked from" if mode == "unlink" else "registered in"
print(f"{verb} {settings} (backup: {', '.join(backups) or 'none, it did not exist'})")
PY

mkdir -p "$BIN"
for tool in evidence-run absence-check suite-summary; do
  target="$BIN/$tool"
  if [ "$MODE" = unlink ]; then
    if [ -L "$target" ] && [ "$(readlink -f "$target")" = "$HARNESS/bin/$tool" ]; then
      rm "$target"
      echo "unlinked $tool"
    fi
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
