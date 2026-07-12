# Scaffold a team kit into the current repository (Windows).
# Usage: scaffold_team.ps1 -Team dev-team
# Copies the kit's agents into ./.claude/agents/ and its constitution into ./CLAUDE.md,
# plus enforcement hooks into ./.claude/. project_memory/ is NOT created here -- the entry gate
# creates it deterministically via init_project_memory.ps1 BEFORE scaffolding (the PM startup
# backfills it the same way if missing). This script never touches project_memory/.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Team,
    [string]$Preset = ""
)

$ErrorActionPreference = "Stop"
$kit = Join-Path $env:USERPROFILE ".claude\team-kits\$Team"
if (-not (Test-Path $kit)) { throw "Team kit not found: $kit" }

$repo = (Get-Location).Path
Write-Host "Scaffolding team '$Team' into $repo" -ForegroundColor Cyan

# Presets are MECHANICAL (a preset that is only a config comment enforces nothing — the real kits
# shipped years of inert solo/duo/team values): with -Preset only that preset's roles (+ the lead)
# are installed; spawning any other role then fails natively (missing agent file) and via
# guard_agent_spawn. Upgrading = re-run with the larger preset (additive) + session restart.
# No -Preset argument? Take the RECORDED, user-confirmed preset from project_config.yaml — else
# the first kit UPDATE would silently install the full roster and the "mechanical preset"
# guarantee evaporates (the exact inert-preset failure mode this design kills).
$presetSource = "argument"
if (-not $Preset) {
    $cfgPeek = Join-Path $repo "project_memory\project_config.yaml"
    if ((Test-Path $cfgPeek) -and (Test-Path (Join-Path $kit "presets.yaml"))) {
        $m = [regex]::Match((Get-Content $cfgPeek -Raw), '(?m)^\s*preset:\s*([A-Za-z0-9_-]+)')
        if ($m.Success) { $Preset = $m.Groups[1].Value; $presetSource = "project_config.yaml" }
    }
}
$presetRoles = $null
if ($Preset) {
    $pf = Join-Path $kit "presets.yaml"
    if (-not (Test-Path $pf)) { throw "Kit '$Team' ships no presets.yaml but -Preset was given" }
    $line = Get-Content $pf | Where-Object { $_ -match "^$Preset\s*:" } | Select-Object -First 1
    if (-not $line) {
        $avail = (Get-Content $pf | Where-Object { $_ -match '^[A-Za-z0-9_-]+\s*:' } |
                  ForEach-Object { ($_ -split ':')[0].Trim() }) -join ', '
        if ($presetSource -eq "project_config.yaml") {
            Write-Host "  [warn] recorded preset '$Preset' is not in the kit's presets.yaml (available: $avail) -- installing the full roster" -ForegroundColor Yellow
            $Preset = ""
        } else {
            throw "Unknown preset '$Preset' for kit '$Team'. Available: $avail"
        }
    } else {
        $val = ($line -split ':', 2)[1].Trim()
        if ($val -ne 'all') { $presetRoles = @($val -split '\s+' | Where-Object { $_ }) }
        Write-Host "  [preset $Preset, from $presetSource] specialist roles: $(if ($presetRoles) { $presetRoles -join ', ' } else { 'ALL' })" -ForegroundColor Cyan
    }
}
$lead = "project-manager"
$kitSettings = Join-Path $kit "settings\settings.json"
if (Test-Path $kitSettings) {
    try { $lead = (Get-Content $kitSettings -Raw | ConvertFrom-Json).agent } catch {}
}

# Back up any existing local team files before overwriting (project_memory is left untouched).
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$bdir = Join-Path $repo ".claude\backups\$stamp"
function Backup-Local {
    param([string]$p)
    if (Test-Path $p) {
        if (-not (Test-Path $bdir)) { New-Item -ItemType Directory -Force -Path $bdir | Out-Null }
        Copy-Item $p (Join-Path $bdir (Split-Path $p -Leaf)) -Recurse -Force
    }
}
Backup-Local (Join-Path $repo "CLAUDE.md")
Backup-Local (Join-Path $repo ".claude\settings.json")
Backup-Local (Join-Path $repo ".claude\agents")
if (Test-Path $bdir) { Write-Host "  [ok] backed up existing team files -> .claude/backups/$stamp" -ForegroundColor Green }

$agentsSrc = Join-Path $kit "agents"
$agentsDst = Join-Path $repo ".claude\agents"
if (-not (Test-Path $agentsDst)) { New-Item -ItemType Directory -Force -Path $agentsDst | Out-Null }
Get-ChildItem -Path $agentsSrc -Filter "*.md" | ForEach-Object {
    if ($presetRoles -and $_.BaseName -ne $lead -and $presetRoles -notcontains $_.BaseName) { return }
    Copy-Item $_.FullName (Join-Path $agentsDst $_.Name) -Force
    Write-Host "  [ok] agent: $($_.Name)" -ForegroundColor Green
}

# §11 map sync (the scaffold resets agent frontmatter to kit defaults — when the project already
# carries user-confirmed model_map/effort_map, stamp them back DETERMINISTICALLY instead of leaving
# an out-of-sync nag for the PM: a real update regressed a user-approved opus role to sonnet and
# nothing fixed it for two days).
$cfg = Join-Path $repo "project_memory\project_config.yaml"
if (Test-Path $cfg) {
    $synced = 0
    $inMap = ""
    foreach ($ln in ((Get-Content $cfg -Raw) -split "`r?`n")) {
        if ($ln -match '^(model_map|effort_map)\s*:\s*(#.*)?$') { $inMap = $Matches[1]; continue }
        if ($inMap) {
            if ($ln -match '^\S') { $inMap = ""; continue }
            if ($ln -match '^\s+([A-Za-z0-9_-]+)\s*:\s*([A-Za-z0-9_-]+)') {
                $role = $Matches[1]; $val = $Matches[2]
                $field = if ($inMap -eq "model_map") { "model" } else { "effort" }
                $ap = Join-Path $agentsDst ($role + ".md")
                if (Test-Path $ap) {
                    $raw = [IO.File]::ReadAllText($ap)
                    $re = [regex]('(?m)^' + $field + ':[^\r\n]*')
                    $new = $re.Replace($raw, ($field + ": " + $val), 1)
                    if ($new -ne $raw) { [IO.File]::WriteAllText($ap, $new); $synced++ }
                }
            }
        }
    }
    if ($synced -gt 0) { Write-Host "  [ok] re-synced $synced model:/effort: line(s) from project_config.yaml (user-confirmed maps win over kit defaults)" -ForegroundColor Green }
}

$conSrc = Join-Path $kit "constitution\CLAUDE.md"
if (Test-Path $conSrc) {
    Copy-Item $conSrc (Join-Path $repo "CLAUDE.md") -Force
    Write-Host "  [ok] CLAUDE.md (local constitution)" -ForegroundColor Green
}

# Enforcement layer: hooks + settings.json travel with the team.
$hooksSrc = Join-Path $kit "hooks"
if (Test-Path $hooksSrc) {
    $hooksDst = Join-Path $repo ".claude\hooks"
    if (-not (Test-Path $hooksDst)) { New-Item -ItemType Directory -Force -Path $hooksDst | Out-Null }
    Get-ChildItem -Path $hooksSrc -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $hooksDst $_.Name) -Force
        Write-Host "  [ok] hook: $($_.Name)" -ForegroundColor Green
    }
}
# Role skills travel with the team (preloaded into the agents via their `skills:` frontmatter).
$skillsSrc = Join-Path $kit "skills"
if (Test-Path $skillsSrc) {
    $skillsDst = Join-Path $repo ".claude\skills"
    if (-not (Test-Path $skillsDst)) { New-Item -ItemType Directory -Force -Path $skillsDst | Out-Null }
    Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
        if ($presetRoles -and $_.Name -ne $lead -and $presetRoles -notcontains $_.Name) { return }
        $d = Join-Path $skillsDst $_.Name
        if (Test-Path $d) { Remove-Item $d -Recurse -Force }
        Copy-Item $_.FullName $d -Recurse -Force
        Write-Host "  [ok] skill: $($_.Name)" -ForegroundColor Green
    }
}
$settingsSrc = Join-Path $kit "settings\settings.json"
if (Test-Path $settingsSrc) {
    Copy-Item $settingsSrc (Join-Path $repo ".claude\settings.json") -Force
    Write-Host "  [ok] .claude/settings.json (session agent + enforcement hooks)" -ForegroundColor Green
}
# Stamp the installed kit version (session_status compares it with the staged kit to flag updates).
$verSrc = Join-Path $kit "VERSION"
if (Test-Path $verSrc) {
    Copy-Item $verSrc (Join-Path $repo ".claude\kit_version") -Force
    Write-Host "  [ok] .claude/kit_version ($((Get-Content $verSrc -TotalCount 1)))" -ForegroundColor Green
}

# Repo-level quality templates (scripts/quality.py, CI, pre-commit, requirements-dev) -- copy-if-absent
# so DevOps can customise them without a re-scaffold clobbering changes. The merge gate runs quality.py.
# Diverged files additionally land in .claude/kit_update_pending.repo: printed [kept] lines were shown
# but never acted on in a real project (kit fixes silently never arrived) -- session_status now reminds
# the PM until every line is merged or consciously skipped and the file is DELETED.
$keptList = @()
$repoTplSrc = Join-Path $kit "templates\repo"
if (Test-Path $repoTplSrc) {
    Get-ChildItem -Path $repoTplSrc -Recurse -File -Force | Where-Object { $_.FullName -notmatch '__pycache__|\.ruff_cache|\.mypy_cache|\.pytest_cache' } | ForEach-Object {
        $rel = $_.FullName.Substring($repoTplSrc.Length).TrimStart('\', '/')
        $dst = Join-Path $repo $rel
        # scripts/kit_checks.py is KIT-OWNED: always overwritten (like the hooks), never pending —
        # so kit-level check fixes reach even projects whose quality.py runner is a heavy fork.
        if (($rel -replace '\\', '/') -eq 'scripts/kit_checks.py') {
            $dstDir = Split-Path $dst
            if ($dstDir -and -not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
            Copy-Item $_.FullName $dst -Force
            Write-Host "  [ok] repo (kit-owned, always updated): $rel" -ForegroundColor Green
            return
        }
        if (-not (Test-Path $dst)) {
            $dstDir = Split-Path $dst
            if ($dstDir -and -not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
            Copy-Item $_.FullName $dst -Force
            Write-Host "  [ok] repo: $rel" -ForegroundColor Green
        } elseif ((Get-FileHash $dst -Algorithm SHA256).Hash -ne (Get-FileHash $_.FullName -Algorithm SHA256).Hash) {
            # copy-if-absent keeps the project's version — but say so, or a kit fix (e.g. quality.py)
            # silently never reaches existing projects while the update reads as "applied".
            Write-Host "  [kept] repo: $rel (differs from the kit template - review/merge manually)" -ForegroundColor Yellow
            $keptList += ($rel -replace '\\', '/')
        }
    }
}
$pendFile = Join-Path $repo ".claude\kit_update_pending.repo"
$stateFile = Join-Path $repo ".claude\kit_update_pending.state"
if ($keptList.Count -gt 0) {
    $lines = @("# Repo templates that DIFFER from kit $Team $((Get-Content (Join-Path $kit 'VERSION') -TotalCount 1 -ErrorAction SilentlyContinue)) -- the PM reviews each against the kit template, merges the kit's fixes (or documents a conscious skip in progress.yaml log:), then DELETES this file. session_status reminds every session until it is gone.")
    $lines += ($keptList | ForEach-Object { "- $_" })
    Set-Content -Path $pendFile -Value $lines -Encoding utf8
    if (Test-Path $stateFile) { Remove-Item $stateFile -Force }   # fresh update -> fresh nag counter
    Write-Host "  [!] $($keptList.Count) diverged repo file(s) -> .claude/kit_update_pending.repo (merge or consciously skip, then delete it)" -ForegroundColor Yellow
} elseif (Test-Path $pendFile) {
    Remove-Item $pendFile -Force
}

Write-Host "Team '$Team' installed locally. RESTART the session (close/reopen, or start a new session in this folder) -- the new agents and the 'agent: $lead' setting only load at session start. After the restart, type anything (e.g. 'weiter') -- nothing is auto-sent, YOU stay in control of the first message; the '$lead' lead then greets you with a one-line status and picks up any draft plan in project_memory/." -ForegroundColor Cyan
