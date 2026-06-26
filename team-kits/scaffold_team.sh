#!/usr/bin/env bash
# Scaffold a team kit into the current repository (Unix).
# Usage: scaffold_team.sh dev-team
# Copies the kit's agents into ./.claude/agents/ and its constitution into ./CLAUDE.md.
# project_memory/ is NOT created here — the PM/technical-writer creates it from the global templates.
set -euo pipefail

TEAM="${1:-}"
if [ -z "$TEAM" ]; then
  echo "Usage: scaffold_team.sh <team>" >&2
  exit 1
fi

KIT="$HOME/.claude/team-kits/$TEAM"
if [ ! -d "$KIT" ]; then
  echo "Team kit not found: $KIT" >&2
  exit 1
fi

REPO="$(pwd)"
echo "Scaffolding team '$TEAM' into $REPO"

mkdir -p "$REPO/.claude/agents"
for f in "$KIT"/agents/*.md; do
  [ -e "$f" ] || continue
  cp -f "$f" "$REPO/.claude/agents/$(basename "$f")"
  echo "  [ok] agent: $(basename "$f")"
done

if [ -f "$KIT/constitution/CLAUDE.md" ]; then
  cp -f "$KIT/constitution/CLAUDE.md" "$REPO/CLAUDE.md"
  echo "  [ok] CLAUDE.md (local constitution)"
fi

echo "Team '$TEAM' installed locally. Next: work via @project-manager."
