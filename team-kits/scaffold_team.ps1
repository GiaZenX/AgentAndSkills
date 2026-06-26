# Scaffold a team kit into the current repository (Windows).
# Usage: scaffold_team.ps1 -Team dev-team
# Copies the kit's agents into ./.claude/agents/ and its constitution into ./CLAUDE.md.
# project_memory/ is NOT created here — the PM/technical-writer creates it from the global templates.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Team
)

$ErrorActionPreference = "Stop"
$kit = Join-Path $env:USERPROFILE ".claude\team-kits\$Team"
if (-not (Test-Path $kit)) { throw "Team kit not found: $kit" }

$repo = (Get-Location).Path
Write-Host "Scaffolding team '$Team' into $repo" -ForegroundColor Cyan

$agentsSrc = Join-Path $kit "agents"
$agentsDst = Join-Path $repo ".claude\agents"
if (-not (Test-Path $agentsDst)) { New-Item -ItemType Directory -Force -Path $agentsDst | Out-Null }
Get-ChildItem -Path $agentsSrc -Filter "*.md" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $agentsDst $_.Name) -Force
    Write-Host "  [ok] agent: $($_.Name)" -ForegroundColor Green
}

$conSrc = Join-Path $kit "constitution\CLAUDE.md"
if (Test-Path $conSrc) {
    Copy-Item $conSrc (Join-Path $repo "CLAUDE.md") -Force
    Write-Host "  [ok] CLAUDE.md (local constitution)" -ForegroundColor Green
}

Write-Host "Team '$Team' installed locally. Next: work via @project-manager." -ForegroundColor Cyan
