# Create ./project_memory/ from a team kit's templates -- deterministic, copy-if-absent (Windows).
# Usage: init_project_memory.ps1 -Team dev-team
# Run by the entry gate BEFORE scaffolding (and as the PM startup backfill) so the project_memory
# bootstrap is a SCRIPT step, not ~20 files copied by hand. Never overwrites a file that already
# exists, so it is safe to re-run and never clobbers a draft/filled artifact.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Team
)

$ErrorActionPreference = "Stop"
$src = Join-Path $env:USERPROFILE ".claude\team-kits\$Team\templates\project_memory"
if (-not (Test-Path $src)) { throw "Templates not found: $src" }

$repo = (Get-Location).Path
$dst = Join-Path $repo "project_memory"
if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Force -Path $dst | Out-Null }

$copied = 0; $kept = 0
Get-ChildItem -Path $src -Recurse -File -Force | Where-Object { $_.FullName -notmatch '__pycache__' } | ForEach-Object {
    $rel = $_.FullName.Substring($src.Length).TrimStart('\', '/')
    $target = Join-Path $dst $rel
    if (Test-Path $target) { $kept++; return }   # copy-if-absent: never clobber existing content
    $tdir = Split-Path $target
    if ($tdir -and -not (Test-Path $tdir)) { New-Item -ItemType Directory -Force -Path $tdir | Out-Null }
    Copy-Item $_.FullName $target -Force
    $copied++
}
Write-Host "[ok] project_memory/ ready ($copied created, $kept already present) from kit '$Team'." -ForegroundColor Green
