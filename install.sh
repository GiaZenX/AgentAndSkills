#!/usr/bin/env bash
# Linux/macOS installer for agents-and-skills
# Usage:
#   ./install.sh                  # Install for both Claude Code and Copilot (asks to confirm)
#   ./install.sh --target claude  # Only Claude Code
#   ./install.sh --target copilot # Only Copilot
#   ./install.sh --force          # Skip the confirmation prompt (still backs up first)
#
# Behavior: backs up the existing agents-and-skills artifacts to ~/.claude/backups/<timestamp>/,
# shows a notice, asks to confirm, then overwrites them. ~/.claude/settings.json is MERGED
# (our keys added; your personal keys preserved) and the previous file is backed up.

set -euo pipefail

TARGET="both"
FORCE=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --force|-y) FORCE=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
GLOBAL_CLAUDE_SRC="$REPO_ROOT/global/claude"
GLOBAL_COPILOT_SRC="$REPO_ROOT/global/copilot"
TEAM_KITS_SRC="$REPO_ROOT/team-kits"
MERGE_SCRIPT="$REPO_ROOT/global/merge_settings.py"

CLAUDE_GLOBAL="$HOME/.claude"
CLAUDE_SKILLS="$HOME/.claude/skills"
CLAUDE_AGENTS="$HOME/.claude/agents"
CLAUDE_TEAM_KITS="$HOME/.claude/team-kits"
COPILOT_SKILLS="$HOME/.copilot/skills"

case "$(uname -s)" in
    Darwin) VSCODE_PROMPTS="$HOME/Library/Application Support/Code/User/prompts" ;;
    *)      VSCODE_PROMPTS="$HOME/.config/Code/User/prompts" ;;
esac

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_GLOBAL/backups/$STAMP"

PYTHON="$(command -v python3 || command -v python || true)"

backup_item() {
    local path="$1"
    [[ -e "$path" ]] || return 0
    mkdir -p "$BACKUP_DIR"
    cp -R "$path" "$BACKUP_DIR/$(basename "$path")"
}

install_skills() {
    local dest="$1"; local label="$2"
    mkdir -p "$dest"
    for skill in "$SKILLS_SRC"/*/; do
        name="$(basename "$skill")"
        rm -rf "$dest/$name"
        cp -R "$skill" "$dest/$name"
        echo "  [ok]   $label : $name"
    done
}

install_file() {
    local src="$1"; local dest="$2"; local label="$3"
    if [[ ! -e "$src" ]]; then echo "  [warn] not found: $src"; return; fi
    mkdir -p "$(dirname "$dest")"
    cp -f "$src" "$dest"
    echo "  [ok]   $label"
}

echo "agents-and-skills installer"
echo "This OVERWRITES the agents-and-skills files in ~/.claude (CLAUDE.md, agents, skills,"
echo "team-kits, statusline) and MERGES ~/.claude/settings.json (your personal keys are kept)."
echo "A backup of the current files is saved to: $BACKUP_DIR"
if [[ $FORCE -eq 0 ]]; then
    read -r -p "Continue? (y/N) " answer
    case "$answer" in y|Y|yes|j|ja) ;; *) echo "Aborted."; exit 1 ;; esac
fi

echo
echo "-> Backing up to $BACKUP_DIR"
backup_item "$CLAUDE_GLOBAL/CLAUDE.md"
backup_item "$CLAUDE_GLOBAL/settings.json"
backup_item "$CLAUDE_GLOBAL/statusline.py"
backup_item "$CLAUDE_AGENTS"
backup_item "$CLAUDE_SKILLS"
backup_item "$CLAUDE_TEAM_KITS"
if [[ -d "$VSCODE_PROMPTS" ]]; then
    for f in "$VSCODE_PROMPTS"/*.agent.md "$VSCODE_PROMPTS/COPILOT.instructions.md"; do
        [[ -e "$f" ]] && backup_item "$f"
    done
fi
echo "  [ok]   backup complete"

echo
echo "-> Team kits (shared staging)"
if [[ -d "$TEAM_KITS_SRC" ]]; then
    rm -rf "$CLAUDE_TEAM_KITS"; mkdir -p "$CLAUDE_TEAM_KITS"
    cp -R "$TEAM_KITS_SRC/." "$CLAUDE_TEAM_KITS/"
    echo "  [ok]   team-kits -> ~/.claude/team-kits"
fi

if [[ "$TARGET" == "both" || "$TARGET" == "claude" ]]; then
    echo
    echo "-> Claude Code"
    install_skills "$CLAUDE_SKILLS" "skill"
    install_file "$GLOBAL_CLAUDE_SRC/CLAUDE.md" "$CLAUDE_GLOBAL/CLAUDE.md" "CLAUDE.md -> ~/.claude/CLAUDE.md"
    install_file "$GLOBAL_CLAUDE_SRC/statusline.py" "$CLAUDE_GLOBAL/statusline.py" "statusline.py -> ~/.claude/statusline.py"
    if [[ -d "$GLOBAL_CLAUDE_SRC/agents" ]]; then
        for f in "$GLOBAL_CLAUDE_SRC/agents"/*.md; do
            [[ -e "$f" ]] || continue
            install_file "$f" "$CLAUDE_AGENTS/$(basename "$f")" "agent: $(basename "$f")"
        done
    fi
    if [[ -n "$PYTHON" && -f "$MERGE_SCRIPT" && -f "$GLOBAL_CLAUDE_SRC/settings.json" ]]; then
        "$PYTHON" "$MERGE_SCRIPT" "$GLOBAL_CLAUDE_SRC/settings.json" "$CLAUDE_GLOBAL/settings.json"
    else
        echo "  [warn] python not found or merge script missing - skipped settings.json merge."
        echo "         Add the keys from global/claude/settings.json to ~/.claude/settings.json manually."
    fi
fi

if [[ "$TARGET" == "both" || "$TARGET" == "copilot" ]]; then
    echo
    echo "-> GitHub Copilot"
    install_skills "$COPILOT_SKILLS" "skill"
    for f in "$GLOBAL_COPILOT_SRC"/*.instructions.md; do
        [[ -e "$f" ]] || continue
        install_file "$f" "$VSCODE_PROMPTS/$(basename "$f")" "instructions: $(basename "$f")"
    done
    if [[ -d "$GLOBAL_COPILOT_SRC/agents" ]]; then
        for f in "$GLOBAL_COPILOT_SRC/agents"/*.agent.md; do
            [[ -e "$f" ]] || continue
            install_file "$f" "$VSCODE_PROMPTS/$(basename "$f")" "agent: $(basename "$f")"
        done
    fi
fi

echo
echo "Done. Backup at $BACKUP_DIR. Restart VS Code to pick up new skills/agents."
