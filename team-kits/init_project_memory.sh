#!/usr/bin/env bash
# Create ./project_memory/ from a team kit's templates -- deterministic, copy-if-absent (Unix).
# Usage: init_project_memory.sh dev-team
# Run by the entry gate BEFORE scaffolding (and as the PM startup backfill) so the project_memory
# bootstrap is a SCRIPT step, not ~20 files copied by hand. Never overwrites a file that already
# exists, so it is safe to re-run and never clobbers a draft/filled artifact.
set -euo pipefail

TEAM="${1:-}"
if [ -z "$TEAM" ]; then
  echo "Usage: init_project_memory.sh <team>" >&2
  exit 1
fi

SRC="$HOME/.claude/team-kits/$TEAM/templates/project_memory"
if [ ! -d "$SRC" ]; then
  echo "Templates not found: $SRC" >&2
  exit 1
fi

REPO="$(pwd)"
DST="$REPO/project_memory"
mkdir -p "$DST"

copied=0; kept=0
while IFS= read -r rel; do
  rel="${rel#./}"
  target="$DST/$rel"
  if [ -e "$target" ]; then kept=$((kept + 1)); continue; fi   # copy-if-absent: never clobber
  mkdir -p "$(dirname "$target")"
  cp "$SRC/$rel" "$target"
  copied=$((copied + 1))
done < <(cd "$SRC" && find . -type f -not -path '*/__pycache__/*')
echo "[ok] project_memory/ ready ($copied created, $kept already present) from kit '$TEAM'."
