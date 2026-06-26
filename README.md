# Agent Skills

Userwide-installable skills, a global **constitution**, and a **multi-agent role model** for
**GitHub Copilot** and **Claude Code** in VS Code.

Instead of a single assistant, this repo simulates a small software team: you are the **customer**,
a **Project Manager (PM)** is your only point of contact, and below it specialized dev roles
(Architect, Backend, Frontend, QA, DevOps, Technical Writer) work as subagents. No matter which tool
you code with, the AI behaves identically.

**Two-tier entry.** A user-wide **global gate** (`CLAUDE.md` / `COPILOT.instructions.md`) drives the
default agent: on your first build/change wish it asks *structured or free*, classifies the effort via
the **team registry**, **installs the matching team kit locally into the repository** (`./.claude/agents/`
+ a local `./CLAUDE.md`), and routes all further work through that repo's `project-manager`. A persistent
guard re-routes to the PM on every later session, so a forgotten agent selection can't lead to
unstructured edits. An optional **`group-leader`** agent does the same routing explicitly if you prefer to
invoke it. Because the team lives in the repo, each project can run its own models (per-project `model:`
frontmatter) without touching anything global. If you don't want the process, you choose *free* and work
without bookkeeping.

Two kits ship today: **`dev-team`** (software/product engineering) and **`research-team`** (research +
experiments with an FZulG R&D-tax-credit documentation layer). The registry maps your intent to the right
one.

Based on [mattpocock/skills](https://github.com/mattpocock/skills) plus a custom role model and a
global workflow standard.

---

## Quickstart

### Windows (PowerShell)

```powershell
git clone https://github.com/GiaZenX/AgentAndSkills.git agent-skills
cd agent-skills
.\install.ps1
```

### macOS / Linux

```bash
git clone https://github.com/GiaZenX/AgentAndSkills.git agent-skills
cd agent-skills
chmod +x install.sh
./install.sh
```

Restart VS Code afterwards.

### Options

| Option | Description |
|---|---|
| `-Target both` (default) | Installs for Claude Code **and** Copilot |
| `-Target claude` | Claude Code only (`~/.claude/skills/` + `~/.claude/CLAUDE.md`) |
| `-Target copilot` | Copilot only (`~/.copilot/skills/` + VS Code agents + instructions) |
| `-Force` | Overwrites already-installed files |

On Linux/Mac use `--target` and `--force` accordingly.

---

## Parity: Claude Code ↔ Copilot

Both tools are configured identically. The whole workflow lives in the **global instructions** and
therefore applies to **every** agent / default mode — no matter what you code with, the AI behaves the
same:

| Component | Claude Code | Copilot |
|---|---|---|
| Global gate | `~/.claude/CLAUDE.md` | `prompts/COPILOT.instructions.md` (`applyTo: **`) |
| Global entry agent | `~/.claude/agents/group-leader.md` | `prompts/group-leader.agent.md` |
| Team kit staging | `~/.claude/team-kits/<team>/` | `~/.claude/team-kits/<team>/` (shared) |
| Local team (per repo) | `./.claude/agents/*.md` + `./CLAUDE.md` | same `./.claude/agents/*.md` + `./CLAUDE.md` |
| Tool syntax | `AskUserQuestions` | `#tool:vscode_askQuestions` |
| Subagent call | Task tool | `runSubagent` |
| Templates | `~/.claude/team-kits/<team>/templates/project_memory/` | same (shared staging) |
| Skills | `~/.claude/skills/` | `~/.copilot/skills/` |

The local team is installed in **Claude format** (`./.claude/agents/*.md` + root `./CLAUDE.md`), which
**both** VS Code Copilot and Claude Code read — one copy serves both ecosystems.

---

## Install paths

| Component | Path |
|---|---|
| Global gate (Claude Code) | `~/.claude/CLAUDE.md` |
| Global gate (Copilot, VS Code) | `<vscode prompts>/COPILOT.instructions.md` (`applyTo: "**"`) |
| Global entry agent (Claude Code) | `~/.claude/agents/group-leader.md` |
| Global entry agent (Copilot, VS Code) | `<vscode prompts>/group-leader.agent.md` |
| Team kit staging (shared) | `~/.claude/team-kits/<team>/` (agents, constitution, templates) + scaffold scripts |
| Local team (per repo, created on demand) | `./.claude/agents/*.md` + `./CLAUDE.md` |
| Claude Code skills | `~/.claude/skills/<skill>/` |
| Copilot skills | `~/.copilot/skills/<skill>/` |
| VS Code prompts folder | Windows: `%APPDATA%\Code\User\prompts\` <br> macOS: `~/Library/Application Support/Code/User/prompts/` <br> Linux: `~/.config/Code/User/prompts/` |

---

## Repo structure

```
agents-and-skills/
├── skills/                              ← shared skills (Claude + Copilot)
├── global/
│   ├── claude/
│   │   ├── CLAUDE.md                    ← global thin gate (Claude Code)
│   │   └── agents/group-leader.md       ← global entry agent (Claude Code)
│   └── copilot/
│       ├── COPILOT.instructions.md      ← global thin gate (applyTo: **)
│       └── agents/group-leader.agent.md ← global entry agent (Copilot)
├── team-kits/
│   ├── registry.yaml                    ← intent → kit routing (single source of truth)
│   ├── scaffold_team.ps1 / .sh          ← installs a kit into the current repo
│   ├── dev-team/
│   │   ├── agents/                      ← 7 roles (project-manager, architect, …)
│   │   ├── constitution/CLAUDE.md       ← local constitution copied to ./CLAUDE.md
│   │   └── templates/project_memory/    ← YAML artifact templates
│   └── research-team/
│       ├── agents/                      ← 8 roles (project-manager, methodologist, …, report-writer)
│       ├── constitution/CLAUDE.md       ← local research constitution
│       └── templates/project_memory/    ← research artifacts + report template + bundled KaTeX
├── install.ps1                          ← Windows installer
└── install.sh                           ← macOS/Linux installer
```

---

## How it starts (two-tier flow)

1. **Global gate asks** (non-coercive): on your first build/change wish the global `CLAUDE.md` /
   `COPILOT.instructions.md` asks *structured (PM) or free?*. Choose *free* and you work without
   bookkeeping.
2. **Auto-init:** on *structured*, the default agent classifies your intent via `team-kits/registry.yaml`
   and runs the scaffold script itself — no agent to remember. (You may instead invoke the optional
   `group-leader` agent explicitly.)
3. **Local install:** the kit's agents are copied to `./.claude/agents/` and its constitution to
   `./CLAUDE.md`. Both VS Code and Claude Code read these. `project_memory/` is **not** created yet.
4. **Route to the local `project-manager`.** On Copilot you pick `project-manager` in the dropdown (it
   stays active); on Claude Code the default agent delegates structured requests to the `project-manager`
   subagent (discovery questions are relayed). The PM then runs its **startup gate** (creates
   `project_memory/` from the kit templates, proposes team preset + per-role models, you confirm, models
   are synced into the local agents' frontmatter) and only then begins the phase model.

---

## Multi-agent role model

The workflow lives in each kit's **constitution** (`CLAUDE.md` / `COPILOT.instructions.md`) and is
executed by role agents. The PM is the entry point and the only interface to the user; the other roles
work as subagents and return YAML. The roles below are the **`dev-team`** (7 roles); the
**`research-team`** mirrors the same machinery with 8 research roles (see below).

### Roles (dev-team)

| Role | File | Job | Talks to user |
|---|---|---|---|
| **Project Manager** | `project-manager` | Requirements (PRD/CR), delegation, merge, user acceptance | **Yes (only one)** |
| **Software Architect** | `software-architect` | System requirements, architecture, ADRs, coding guidelines | No |
| **Backend Developer** | `backend-developer` | Server-side tasks, tests, commits | No |
| **Frontend Developer** | `frontend-developer` | UI tasks, tests, commits | No |
| **Quality Engineer** | `quality-engineer` | Review, tests, Definition of Done, merge gate | No |
| **DevOps Engineer** | `devops-engineer` | CI/CD, pipelines, environments, release | No |
| **Technical Writer** | `technical-writer` | PRDs/CRs, progress, changelog, docs, dashboard (on the PM's instruction) | No |

### Roles (research-team)

Same two-tier machinery, research-flavored. Hierarchy: **Research Question (RQ) → Hypothesis (HYP) +
Experiment Design (EXP) → Tasks**; changes go through **Protocol Amendments (PA)**. The PM (lead) is again
the only customer-facing role.

| Role | File | Job |
|---|---|---|
| **Research Lead** | `project-manager` | RQs/PAs, delegation, merge, user acceptance (only one talking to the user) |
| **Methodologist** | `methodologist` | Hypotheses, experiment designs, MDRs, research guidelines, FZulG criteria |
| **Researcher** | `researcher` | Runs experiments, collects raw data, analysis code |
| **Data Analyst** | `data-analyst` | Statistics, effect sizes, visualization, interpretation |
| **Reviewer** | `reviewer` | Reproducibility + validity gate, peer review, merge gate |
| **Research Engineer** | `research-engineer` | Data pipelines, environments, dataset versioning |
| **Report Writer** | `report-writer` | Per-experiment HTML reports with offline LaTeX (KaTeX), fixed template |
| **Technical Writer** | `technical-writer` | RQs/PAs, progress, changelog, **FZulG documentation**, dashboard |

### Phase model

`0 READ → 0.5 ASSESSMENT (existing repos only) → 1 PM_DISCOVERY → 2 PM_PROPOSAL →
3 USER_APPROVAL → 4 SYSTEM_PLANNING → 5 IMPLEMENTATION → 6 REVIEW → 7 TEST → 8 QA →
9 INTERNAL_ACCEPTANCE + MERGE → 10 USER_ACCEPTANCE`

- **Two-level acceptance:** PM/QA accept internally per branch/task; the **user only accepts per PRD**
  (on `main`, after the internal merge).
- **ASSESSMENT** runs only for existing repos: PM + Architect + QA produce a **gap report** (missing
  tests, guideline gaps, refactoring candidates, tech debt, security) — the user chooses what becomes
  a PRD/CR.

### Artifacts (`project_memory/`)

Structured YAML files in the repo. Each role writes only its own area (no overwriting). The Technical
Writer creates `project_memory/` on the first run from the globally installed templates (on the PM's
instruction).

A user-facing **dashboard** (`progress.dashboard.html`) is generated, never hand-edited: the Technical
Writer (on the PM's instruction) runs
`generate_dashboard.py`, which reads the PRD/task/CR YAML files, rebuilds the dashboard from a static
shell, archives the previous version under `dashboard_history/`, and lists what changed since the last
run. Bars expand to reveal the items behind each status (id, title, owner, origin, start/end dates).
Running the generator needs PyYAML (`pip install pyyaml`); the generated HTML is dependency-free and
opens by double-click.

### Git, presets & models

- **Branch per PRD** (`feat/PRD-xxx-…`), merge after internal QA, **push only on user confirmation**,
  no force-push, no work on a dirty tree.
- **Team preset** (`solo` | `duo` | `team`) chosen once per project; escalation is user-gated only.
- **Models** start on `haiku`; controlled per repo via `project_config.yaml`. Upgrades only after a
  user OK (triggers: 2× QA fail or dissatisfaction). The agent files themselves are model-neutral —
  nothing global is ever rewritten.

### Behavior

- **Anti-sycophancy:** never agree silently, justify decisions, push back on the user when needed.
- **The PM speaks plain language** (no jargon); between agents communication is fully technical.

---

## Skills

Skills are invoked in chat via `/<skill-name>` or loaded automatically by the agent when the
description matches.

### Engineering

| Skill | Invoke | What it does |
|---|---|---|
| **debug** | `/debug` | Disciplined bug diagnosis: reproduce → minimize → hypothesize → instrument → fix → regression test |
| **tdd** | `/tdd` | Test-driven development with the red-green-refactor loop |
| **review-plan** | `/review-plan` | Stress-tests your plan against the domain language; updates CONTEXT.md and ADRs |
| **refactor** | `/refactor` | Finds refactoring opportunities; consolidates tightly coupled modules |
| **plan-to-prd** | `/plan-to-prd` | Turns the current conversation context into a PRD |
| **plan-to-issues** | `/plan-to-issues` | Breaks a plan/PRD into independent GitHub issues (vertical slices) |
| **triage** | `/triage` | Issue triage via a role state machine |
| **explain** | `/explain` | Explains code in the context of the whole system |
| **setup-repo** | `/setup-repo` | Once per repo: configures issue tracker, triage labels, domain doc layout |

### Productivity

| Skill | Invoke | What it does |
|---|---|---|
| **interview** | `/interview` | Interviews you intensively about a plan/design with polls — until every decision is resolved |
| **brief-mode** | `/brief-mode` | Ultra-compressed communication mode, saves ~75% tokens |
| **new-skill** | `/new-skill` | Helps you create your own new skills |

### Misc

| Skill | Invoke | What it does |
|---|---|---|
| **pre-commit** | `/pre-commit` | Husky pre-commit hooks with Prettier, type checking, tests |
| **git-safety** | `/git-safety` | Claude Code only: blocks dangerous git commands (`push`, `reset --hard`, etc.) |

---

## Recommended workflow

1. **Once per repo:** `/setup-repo`
2. **Before any change:** `/interview` or `/review-plan`
3. **Implementation:** `/tdd` or directly in chat (the workflow applies automatically)
4. **On bugs:** `/debug`
5. **Regularly:** `/refactor`

---

## Your own fork / customization

To move the repo to a different GitHub account:

```bash
# 1. Create your own empty repo on GitHub (e.g. github.com/your-account/agent-skills)

# 2. Re-point the remote
cd agent-skills
git remote set-url origin https://github.com/your-account/agent-skills.git
git push -u origin main
```

On new machines just clone and run `install.ps1` / `install.sh`.

---

## Update

```powershell
cd ~\agent-skills
git pull
.\install.ps1 -Force
```

```bash
cd ~/agent-skills
git pull
./install.sh --force
```

---

## Uninstall

Delete the folders manually:
- `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/team-kits/`, `~/.claude/CLAUDE.md`
- `~/.copilot/skills/`
- VS Code prompts folder (see the path table above): the files `group-leader.agent.md` and `COPILOT.instructions.md`
- In each project: the local `./.claude/agents/` and `./CLAUDE.md` (only if you want to remove the team there)

---

## License

Skills from [mattpocock/skills](https://github.com/mattpocock/skills): MIT
Custom additions (workflow docs, installer): MIT
