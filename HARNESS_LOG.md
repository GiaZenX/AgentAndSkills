# Harness log

One dated entry per hardening round: WHAT changed and WHY — the tool-neutral entry point into this
repo's history for any agent CLI (Claude Code, Codex, Copilot) and for humans. Full rationale lives
in the referenced commit messages; project conventions live in the kits themselves. Newest first.
Append an entry with every shipped round (same commit).

## 2026-07-14 — Multi-CLI parity + forensics defect round (kits 2026.07.14-4)
The same harness now runs on Claude Code, Codex CLI (BETA) and GitHub Copilot (generated,
live-unverified) — one kit source, generated provider artifacts (AGENTS.md as the AAIF-standard
constitution + a verified CLAUDE.md `@AGENTS.md` import shim, `.codex/`/`.github/` registrations
via gen_provider_artifacts.py, shared Python hooks behind the `_compat.py` payload adapter),
tier-based model maps (model_tiers.yaml: lead/worker/light → Opus/Sol, Sonnet/Terra, …), a
provider-neutral git-level second line of defense (kit_checks enforcement-diff, incl. trunk
workflows), a claude-watcher/codex-watcher duo, and the eight defects (D1–D8) found by forensics
on the first 2026.07.14-2 production day — incl. two guard_harness_selfmod bypass holes reported
by the project's own security reviews, plus new selfmod protection for the constitution files
themselves. Fable diff-audit: 0 blockers, 5 findings (M1–M5), all incorporated; 129 tests green.

## 2026-07-14 — Research-grounded hardening (`bb8b869`, kits 2026.07.14-2)
Constitution diet to <=220 lines (research: bloated rule files get ignored; subagents inherit them,
so the diet pays on every spawn), opus defaults for judgment roles (architect/designer/QA,
methodologist/reviewer), agent memory scoped to craft roles with a curation cap, mandatory work-order
spawns, SubagentStop output contract, guard_harness_selfmod (no agent edits the enforcement layer),
entry-level QA-verdict binding in gate_git, project-auditor role in all kits, kit-version
announcements at session start. Fresh-eyes Fable audit: 12 objections, all incorporated.

## 2026-07-12 — V1–V7 + file budget + mechanical presets + office-team kit (`3f8ecc6`)
Presets became MECHANICAL (scaffold installs only the confirmed preset's roles), hard 800-line file
budget with architect-owned exemptions (a real App.tsx hit 8,966 lines), kit-owned kit_checks.py that
updates force-overwrite (a project's quality.py fork had silently never run kit checks), and the
third kit (office-team: bookkeeping/filing with append-only ledger scripts and fs tripwires).

## 2026-07-12 — Restamp resync gap + shell bypass (`331a125`)
External restamps now re-stamp model/effort frontmatter from the user-confirmed maps (a project ran
its approved-opus frontend on sonnet for two days), and the progress.yaml contract is enforced at
pipeline time too (a shell heredoc had bypassed the write-time guard).

## 2026-07-10 — Speed + precision round from synaipse forensics (`40af990`)
Fast-iteration path (--frontend-only) so small UI fixes stop paying the full merge gate, plus
precision fixes P1–P7 from real-run friction; radar triage process for external feature watch.

## 2026-07-04 — Design-fidelity chain + enforcement holes (`f6f49d3`)
15 audited fixes: mockup-as-base design chain (frontend builds literally on the designer's
deliverable), cost discipline, and closure of enforcement bypasses found in real runs.

## 2026-07-03 — Kit versioning + guided updates (`20128f8`, `e70045c`, `f140957`)
VERSION stamps per kit (content hash), session-start update detection, guided safe updates with
[kept]-line visibility for diverged files — the foundation the pending-file contract builds on.

## 2026-07-03 — Synaipse forensics round (`75040b5`)
Write-time YAML guard, masterplan-as-log flow, dead-end honesty rule, handover honesty, architect
opus recommendation — the first round fully driven by transcript forensics of a real project.

## 2026-06-30 — Design ambition + a11y (`7175457`, `b4faba9`)
Design-ambition fork (basic consistency vs. final polish), deterministic a11y/contrast gate seed,
security guidance anchored as advisory shift-left in QA/DevOps skills.
