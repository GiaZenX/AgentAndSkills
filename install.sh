#!/usr/bin/env bash
# Linux/macOS installer for agents-and-skills
# Usage:
#   ./install.sh                  # Install for both Claude Code and Copilot
#   ./install.sh --target claude  # Only Claude Code
#   ./install.sh --target copilot # Only Copilot
#   ./install.sh --force          # Overwrite existing files
#
# Team kits are NOT installed into a project. The group-leader copies the
# matching kit from ~/.claude/team-kits into the target repo on demand.

set -euo pipefail

TARGET="both"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --force) FORCE=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
GLOBAL_CLAUDE_SRC="$REPO_ROOT/global/claude"
GLOBAL_COPILOT_SRC="$REPO_ROOT/global/copilot"
TEAM_KITS_SRC="$REPO_ROOT/team-kits"

CLAUDE_GLOBAL="$HOME/.claude"
CLAUDE_SKILLS="$HOME/.claude/skills"
CLAUDE_AGENTS="$HOME/.claude/agents"
CLAUDE_TEAM_KITS="$HOME/.claude/team-kits"
COPILOT_SKILLS="$HOME/.copilot/skills"

# VS Code user prompts location differs per OS
case "$(uname -s)" in
    Darwin) VSCODE_PROMPTS="$HOME/Library/Application Support/Code/User/prompts" ;;
    Linux)  VSCODE_PROMPTS="$HOME/.config/Code/User/prompts" ;;
    *)      VSCODE_PROMPTS="$HOME/.config/Code/User/prompts" ;;
esac

install_skills() {
    local dest="$1"
    local label="$2"
    mkdir -p "$dest"
    for skill in "$SKILLS_SRC"/*/; do
        name="$(basename "$skill")"
        target_dir="$dest/$name"
        if [[ -e "$target_dir" && $FORCE -eq 0 ]]; then
            echo "  [skip] $label : $name"; continue
        fi
        rm -rf "$target_dir"
        cp -R "$skill" "$target_dir"
        echo "  [ok]   $label : $name"
    done
}

install_file() {
    local src="$1"
    local dest="$2"
    local label="$3"
    if [[ ! -e "$src" ]]; then echo "  [warn] not found: $src"; return; fi
    if [[ -e "$dest" && $FORCE -eq 0 ]]; then
        echo "  [skip] $label (use --force to overwrite)"; return
    fi
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    echo "  [ok]   $label"
}

install_team_kits() {
    # Stage the whole team-kits tree (kits + scaffold scripts).
    [[ -d "$TEAM_KITS_SRC" ]] || { echo "  [warn] not found: $TEAM_KITS_SRC"; return; }
    if [[ -e "$CLAUDE_TEAM_KITS" && $FORCE -eq 0 ]]; then
        echo "  [skip] team-kits staging (use --force to overwrite)"; return
    fi
    rm -rf "$CLAUDE_TEAM_KITS"
    mkdir -p "$CLAUDE_TEAM_KITS"
    cp -R "$TEAM_KITS_SRC/." "$CLAUDE_TEAM_KITS/"
    echo "  [ok]   team-kits -> ~/.claude/team-kits"
}

echo "Installing agents-and-skills..."

# Team kits are ecosystem-neutral staging used by both group-leaders.
echo
echo "-> Team kits (shared staging)"
install_team_kits

if [[ "$TARGET" == "both" || "$TARGET" == "claude" ]]; then
    echo
    echo "-> Claude Code"
    install_skills "$CLAUDE_SKILLS" "skill"
    install_file "$GLOBAL_CLAUDE_SRC/CLAUDE.md" "$CLAUDE_GLOBAL/CLAUDE.md" "CLAUDE.md -> ~/.claude/CLAUDE.md"
    if [[ -d "$GLOBAL_CLAUDE_SRC/agents" ]]; then
        for f in "$GLOBAL_CLAUDE_SRC/agents"/*.md; do
            [[ -e "$f" ]] || continue
            name="$(basename "$f")"
            install_file "$f" "$CLAUDE_AGENTS/$name" "agent: $name"
        done
    fi
fi

if [[ "$TARGET" == "both" || "$TARGET" == "copilot" ]]; then
    echo
    echo "-> GitHub Copilot"
    install_skills "$COPILOT_SKILLS" "skill"
    for f in "$GLOBAL_COPILOT_SRC"/*.instructions.md; do
        [[ -e "$f" ]] || continue
        name="$(basename "$f")"
        install_file "$f" "$VSCODE_PROMPTS/$name" "instructions: $name"
    done
    if [[ -d "$GLOBAL_COPILOT_SRC/agents" ]]; then
        for f in "$GLOBAL_COPILOT_SRC/agents"/*.agent.md; do
            [[ -e "$f" ]] || continue
            name="$(basename "$f")"
            install_file "$f" "$VSCODE_PROMPTS/$name" "agent: $name"
        done
    fi
fi

echo
echo "Done. Restart VS Code to pick up new skills/agents."
