# Windows installer for agents-and-skills
# Usage:
#   .\install.ps1                 # Install for both Claude Code and Copilot
#   .\install.ps1 -Target claude  # Only Claude Code
#   .\install.ps1 -Target copilot # Only Copilot
#   .\install.ps1 -Force          # Overwrite existing files
#
# Layout installed:
#   ~/.claude/CLAUDE.md                      <- global thin gate (Claude Code)
#   ~/.claude/agents/group-leader.md         <- global entry agent (Claude Code)
#   ~/.claude/team-kits/                     <- staging: team kits + scaffold scripts
#   <vscode prompts>/COPILOT.instructions.md <- global thin gate (Copilot)
#   <vscode prompts>/group-leader.agent.md   <- global entry agent (Copilot)
#   ~/.claude/skills, ~/.copilot/skills      <- shared skills
#
# Team kits are NOT installed into a project. The group-leader copies the
# matching kit from ~/.claude/team-kits into the target repo on demand.

[CmdletBinding()]
param(
    [ValidateSet("both", "claude", "copilot")]
    [string]$Target = "both",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$skillsSrc        = Join-Path $repoRoot "skills"
$globalClaudeSrc  = Join-Path $repoRoot "global\claude"
$globalCopilotSrc = Join-Path $repoRoot "global\copilot"
$teamKitsSrc      = Join-Path $repoRoot "team-kits"

$claudeGlobal   = Join-Path $env:USERPROFILE ".claude"
$claudeSkills   = Join-Path $claudeGlobal "skills"
$claudeAgents   = Join-Path $claudeGlobal "agents"
$claudeTeamKits = Join-Path $claudeGlobal "team-kits"
$copilotSkills  = Join-Path $env:USERPROFILE ".copilot\skills"
$vscodePrompts  = Join-Path $env:APPDATA "Code\User\prompts"

function Install-Skills {
    param([string]$Destination, [string]$Label)
    if (-not (Test-Path $Destination)) { New-Item -ItemType Directory -Path $Destination -Force | Out-Null }
    Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
        $dest = Join-Path $Destination $_.Name
        if ((Test-Path $dest) -and -not $Force) {
            Write-Host "  [skip] $Label : $($_.Name)" -ForegroundColor Yellow; return
        }
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
        Write-Host "  [ok]   $Label : $($_.Name)" -ForegroundColor Green
    }
}

function Install-File {
    param([string]$Src, [string]$Dest, [string]$Label)
    if (-not (Test-Path $Src)) { Write-Host "  [warn] not found: $Src" -ForegroundColor Yellow; return }
    if ((Test-Path $Dest) -and -not $Force) {
        Write-Host "  [skip] $Label (use -Force to overwrite)" -ForegroundColor Yellow; return
    }
    $dir = Split-Path $Dest
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($Dest, (Get-Content $Src -Raw -Encoding UTF8), [System.Text.UTF8Encoding]::new($false))
    Write-Host "  [ok]   $Label" -ForegroundColor Green
}

function Install-TeamKits {
    # Stage the whole team-kits tree (kits + scaffold scripts) so the group-leader
    # can copy a kit into any repo on demand.
    if (-not (Test-Path $teamKitsSrc)) { Write-Host "  [warn] not found: $teamKitsSrc" -ForegroundColor Yellow; return }
    if ((Test-Path $claudeTeamKits) -and -not $Force) {
        Write-Host "  [skip] team-kits staging (use -Force to overwrite)" -ForegroundColor Yellow; return
    }
    if (Test-Path $claudeTeamKits) { Remove-Item $claudeTeamKits -Recurse -Force }
    Copy-Item -Path $teamKitsSrc -Destination $claudeTeamKits -Recurse -Force
    Write-Host "  [ok]   team-kits -> ~/.claude/team-kits" -ForegroundColor Green
}

Write-Host "Installing agents-and-skills..." -ForegroundColor Cyan

# Team kits are ecosystem-neutral staging used by both group-leaders.
Write-Host "`n-> Team kits (shared staging)"
Install-TeamKits

if ($Target -eq "both" -or $Target -eq "claude") {
    Write-Host "`n-> Claude Code"
    Install-Skills -Destination $claudeSkills -Label "skill"
    Install-File -Src (Join-Path $globalClaudeSrc "CLAUDE.md") -Dest (Join-Path $claudeGlobal "CLAUDE.md") -Label "CLAUDE.md -> ~/.claude/CLAUDE.md"
    $claudeAgentsSrc = Join-Path $globalClaudeSrc "agents"
    if (Test-Path $claudeAgentsSrc) {
        Get-ChildItem -Path $claudeAgentsSrc -Filter "*.md" | ForEach-Object {
            Install-File -Src $_.FullName -Dest (Join-Path $claudeAgents $_.Name) -Label "agent: $($_.Name)"
        }
    }
}

if ($Target -eq "both" -or $Target -eq "copilot") {
    Write-Host "`n-> GitHub Copilot"
    Install-Skills -Destination $copilotSkills -Label "skill"
    Get-ChildItem -Path $globalCopilotSrc -Filter "*.instructions.md" | ForEach-Object {
        Install-File -Src $_.FullName -Dest (Join-Path $vscodePrompts $_.Name) -Label "instructions: $($_.Name)"
    }
    $copilotAgentsSrc = Join-Path $globalCopilotSrc "agents"
    if (Test-Path $copilotAgentsSrc) {
        Get-ChildItem -Path $copilotAgentsSrc -Filter "*.agent.md" | ForEach-Object {
            Install-File -Src $_.FullName -Dest (Join-Path $vscodePrompts $_.Name) -Label "agent: $($_.Name)"
        }
    }
}

Write-Host "`nDone. Restart VS Code to pick up new skills/agents." -ForegroundColor Cyan