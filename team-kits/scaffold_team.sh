#!/usr/bin/env bash
# Scaffold a team kit into the current repository (Unix).
# Usage: scaffold_team.sh dev-team
# Copies the kit's agents into ./.claude/agents/ and its constitution into ./CLAUDE.md.
# project_memory/ is NOT created here — the PM creates it from the global templates at startup.
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

# Back up any existing local team files before overwriting (project_memory is left untouched).
STAMP="$(date +%Y%m%d-%H%M%S)"
BDIR="$REPO/.claude/backups/$STAMP"
backup_local() { [ -e "$1" ] || return 0; mkdir -p "$BDIR"; cp -R "$1" "$BDIR/$(basename "$1")"; }
backup_local "$REPO/CLAUDE.md"
backup_local "$REPO/.claude/settings.json"
backup_local "$REPO/.claude/agents"
[ -d "$BDIR" ] && echo "  [ok] backed up existing team files -> .claude/backups/$STAMP"

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

# Enforcement layer: hooks + settings.json travel with the team.
if [ -d "$KIT/hooks" ]; then
  mkdir -p "$REPO/.claude/hooks"
  for f in "$KIT"/hooks/*; do
    [ -e "$f" ] || continue
    cp -f "$f" "$REPO/.claude/hooks/$(basename "$f")"
    echo "  [ok] hook: $(basename "$f")"
  done
fi
# Role skills travel with the team (preloaded into the agents via their `skills:` frontmatter).
if [ -d "$KIT/skills" ]; then
  mkdir -p "$REPO/.claude/skills"
  for d in "$KIT"/skills/*/; do
    [ -e "$d" ] || continue
    name="$(basename "$d")"
    rm -rf "$REPO/.claude/skills/$name"
    cp -R "$d" "$REPO/.claude/skills/$name"
    echo "  [ok] skill: $name"
  done
fi
if [ -f "$KIT/settings/settings.json" ]; then
  mkdir -p "$REPO/.claude"
  cp -f "$KIT/settings/settings.json" "$REPO/.claude/settings.json"
  echo "  [ok] .claude/settings.json (session agent + enforcement hooks)"
fi

echo "Team '$TEAM' installed locally. The main agent is now your Project Manager — just keep prompting."
