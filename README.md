# Agent Skills

Userwide installierbare Skills und Custom Agents für **GitHub Copilot** und **Claude Code** in VS Code.

Basiert auf [mattpocock/skills](https://github.com/mattpocock/skills) plus eigenem `engineer`-Agent.

---

## Quickstart

### Windows (PowerShell)

```powershell
git clone https://github.com/<DEIN-USER>/agent-skills.git
cd agent-skills
.\install.ps1
```

### macOS / Linux

```bash
git clone https://github.com/<DEIN-USER>/agent-skills.git
cd agent-skills
chmod +x install.sh
./install.sh
```

VS Code anschließend neu starten.

### Optionen

| Option | Beschreibung |
|---|---|
| `-Target both` (default) | Installiert für Claude Code **und** Copilot |
| `-Target claude` | Nur Claude Code (`~/.claude/skills/`) |
| `-Target copilot` | Nur Copilot (`~/.copilot/skills/` + VS Code Agents) |
| `-Force` | Überschreibt bereits installierte Skills/Agents |

Linux/Mac entsprechend `--target` und `--force`.

---

## Installationspfade

| Komponente | Pfad |
|---|---|
| Claude Code Skills | `~/.claude/skills/<skill>/` |
| Copilot Skills | `~/.copilot/skills/<skill>/` |
| Custom Agents (VS Code) | Windows: `%APPDATA%\Code\User\prompts\` <br> macOS: `~/Library/Application Support/Code/User/prompts/` <br> Linux: `~/.config/Code/User/prompts/` |

---

## Custom Agent: `engineer`

**Aufruf:** `@engineer <dein Prompt>` im Copilot Chat (oder Agent-Dropdown → engineer wählen).

Ein professioneller Full-Stack-Engineer mit folgenden Eigenschaften:

- **Repo-Management:** Legt fehlendes Repo automatisch an (`git init`, `.gitignore`, `README.md`, `src/`, `ProjectRequirements.md`)
- **Requirement-Tracking:** Liest und pflegt `ProjectRequirements.md` bei jedem Prompt. Status: `ACTIVE`, `DONE`, `REJECTED`, `TO BE NOTED`
- **Git-Workflow:** Committet automatisch lokal. Pusht **nur** wenn du explizit "push" sagst
- **Clean Code:** Selbstdokumentierender Code, keine Kommentare, klare Namen (z.B. `kapitalAmount` statt `K`)
- **Dead-Code-Removal:** Löscht obsoleten Code sofort und dokumentiert ihn im `Removed Code Log`
- **Modular & effizient:** Eine Verantwortung pro Funktion/Modul, optimiert auf Rechenzeit
- **Token-effizient:** Genau eine strukturierte Ausgabe am Ende (Changes, Requirements Update, Removed Code, Git Status)
- **Domain-Expertise:** Robotik, Trading, Maschinenbau, UI-Design, Systems Programming, Data Engineering

---

## Skills

Skills werden im Chat per `/<skill-name>` aufgerufen oder vom Agent automatisch geladen, wenn die Beschreibung passt.

### Engineering

| Skill | Aufruf | Was es macht |
|---|---|---|
| **diagnose** | `/diagnose` oder "debug this" | Disziplinierte Bug-Diagnose: Reproduzieren → Minimieren → Hypothese → Instrumentieren → Fixen → Regressionstest |
| **tdd** | `/tdd` | Test-Driven Development mit Red-Green-Refactor-Loop |
| **grill-with-docs** | `/grill-with-docs` | Stresstest deines Plans gegen die Domain-Sprache; aktualisiert `CONTEXT.md` und ADRs inline |
| **improve-codebase-architecture** | `/improve-codebase-architecture` | Findet Refactoring-Chancen; konsolidiert eng gekoppelte Module |
| **to-prd** | `/to-prd` | Wandelt aktuellen Konversationskontext in ein PRD und legt Issue an |
| **to-issues** | `/to-issues` | Zerlegt Plan/PRD in unabhängige GitHub-Issues (Vertical Slices) |
| **triage** | `/triage` | Issue-Triage durch Rollen-State-Machine |
| **zoom-out** | `/zoom-out` | Agent erklärt Code im Kontext des Gesamtsystems |
| **setup-matt-pocock-skills** | `/setup-matt-pocock-skills` | **Einmal pro Repo:** konfiguriert Issue-Tracker, Triage-Labels, Domain-Doc-Layout |

### Productivity

| Skill | Aufruf | Was es macht |
|---|---|---|
| **grill-me** | `/grill-me` | Interviewt dich gnadenlos zu Plan/Design bis alle Entscheidungen geklärt sind |
| **caveman** | `/caveman` | Ultra-komprimierter Kommunikationsmodus, spart ~75% Tokens |
| **write-a-skill** | `/write-a-skill` | Hilft dir, eigene neue Skills zu erstellen |

### Misc

| Skill | Aufruf | Was es macht |
|---|---|---|
| **setup-pre-commit** | `/setup-pre-commit` | Husky Pre-Commit-Hooks mit Prettier, Type-Checking, Tests |
| **git-guardrails-claude-code** | `/git-guardrails-claude-code` | Nur Claude Code: blockiert gefährliche Git-Befehle (`push`, `reset --hard`, etc.) |

---

## Empfohlener Workflow

1. **Pro Repo einmal:** `/setup-matt-pocock-skills`
2. **Vor jeder Änderung:** `/grill-me` oder `/grill-with-docs`
3. **Implementierung:** `@engineer <task>` oder `/tdd`
4. **Bei Bugs:** `/diagnose`
5. **Regelmäßig:** `/improve-codebase-architecture`

---

## Eigenes Fork / Anpassungen

So überträgst du das Repo auf einen anderen GitHub-Account:

```bash
# 1. Eigenes leeres Repo auf GitHub erstellen (z.B. github.com/dein-account/agent-skills)

# 2. Remote umstellen
cd agent-skills
git remote set-url origin https://github.com/dein-account/agent-skills.git
git push -u origin main
```

Auf neuen Rechnern dann einfach klonen und `install.ps1` / `install.sh` ausführen.

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

## Deinstallation

Ordner manuell löschen:
- `~/.claude/skills/`
- `~/.copilot/skills/`
- VS Code prompts-Ordner (siehe Pfad-Tabelle oben), nur die `*.agent.md` Dateien

---

## Lizenz

Skills von [mattpocock/skills](https://github.com/mattpocock/skills): MIT
Eigene Ergänzungen (`engineer.agent.md`, Installer): MIT
