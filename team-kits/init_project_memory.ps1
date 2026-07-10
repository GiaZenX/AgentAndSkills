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
$keptTooling = @()
Get-ChildItem -Path $src -Recurse -File -Force | Where-Object { $_.FullName -notmatch '__pycache__' } | ForEach-Object {
    $rel = $_.FullName.Substring($src.Length).TrimStart('\', '/')
    $target = Join-Path $dst $rel
    if (Test-Path $target) {
        $kept++
        # TOOLING files (generator/templates/assets — NOT the user's filled YAML state) may lag behind a
        # newer kit: make that visible so the PM can propose the delta. Filled YAMLs always differ — silent.
        if ($rel -match '\.py$|\.template\.|\.tex$|^reports[\\/]assets[\\/]') {
            if ((Get-FileHash $target -Algorithm SHA256).Hash -ne (Get-FileHash $_.FullName -Algorithm SHA256).Hash) {
                Write-Host "  [kept] $rel (tooling differs from the kit template - review/merge manually)" -ForegroundColor Yellow
                $keptTooling += ($rel -replace '\\', '/')
            }
        }
        return
    }   # copy-if-absent: never clobber existing content
    $tdir = Split-Path $target
    if ($tdir -and -not (Test-Path $tdir)) { New-Item -ItemType Directory -Force -Path $tdir | Out-Null }
    Copy-Item $_.FullName $target -Force
    $copied++
}
# Diverged project_memory TOOLING lands in .claude/kit_update_pending.memory (same contract as the
# scaffold's .repo file): printed [kept] lines were shown but never acted on in a real project --
# session_status reminds the PM until every line is merged or consciously skipped and the file is DELETED.
$pendFile = Join-Path $repo ".claude\kit_update_pending.memory"
if ($keptTooling.Count -gt 0) {
    if (-not (Test-Path (Join-Path $repo ".claude"))) { New-Item -ItemType Directory -Force -Path (Join-Path $repo ".claude") | Out-Null }
    $lines = @("# project_memory TOOLING that DIFFERS from kit '$Team' (templates lag behind the kit) -- the PM reviews each against the kit template, merges the kit's fixes (or documents a conscious skip in progress.yaml log:), then DELETES this file. session_status reminds every session until it is gone. Filled YAML state is NOT listed here and is never overwritten.")
    $lines += ($keptTooling | ForEach-Object { "- $_" })
    Set-Content -Path $pendFile -Value $lines -Encoding utf8
    Write-Host "  [!] $($keptTooling.Count) diverged tooling file(s) -> .claude/kit_update_pending.memory (merge or consciously skip, then delete it)" -ForegroundColor Yellow
} elseif (Test-Path $pendFile) {
    Remove-Item $pendFile -Force
}
Write-Host "[ok] project_memory/ ready ($copied created, $kept already present) from kit '$Team'." -ForegroundColor Green
