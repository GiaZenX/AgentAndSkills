---
applyTo: "**"
---
# PFLICHT: Project Memory System

> Diese Anweisungen sind VERBINDLICH und müssen bei JEDER Anfrage ausgeführt werden – ohne Ausnahme.

## SCHRITT 1 – VOR jeder Antwort (MANDATORY)

Ist ein Workspace offen?
- **JA** → Rufe `list_dir` auf dem Workspace-Root auf. Prüfe ob `project_memory/` in der Ausgabe vorkommt.
  - Existiert NICHT → Erstelle SOFORT mit `create_file` diese Dateien (direkt erstellen, nicht nur planen):
    - `project_memory/requirements_workflow.md` mit Inhalt `## Arbeitsweise & Code Standards`
    - `project_memory/requirements_system.md` mit Inhalt `## System Features & Parameter`
    - `project_memory/tasks.md` mit Inhalt `## Features, Bugs, Known Issues`
    - `project_memory/changelog.md` mit Inhalt `## Changelog`
    - `project_memory/architecture.md` mit Inhalt `## Struktur, Module, Design Decisions`
    - `project_memory/progress.md` mit Inhalt `## Metriken & Überblick`
  - Existiert → Lese alle Dateien mit `read_file`. Nutze den Inhalt als Kontext.
- **NEIN** → Weiter ohne Memory.

## SCHRITT 2 – NACH Code-Änderungen (MANDATORY)

Wurde Code erstellt, geändert oder gelöscht? → Aktualisiere **sofort** mit `replace_string_in_file`:
- `changelog.md`: `[DONE] YYYY-MM-DD | Was wurde gemacht`
- `tasks.md`: Tasks auf aktuellen Status setzen
- `requirements_system.md`: Neue/geänderte Anforderungen
- `architecture.md`: Struktur- oder Design-Entscheidungen

Bei reinen Fragen/Erklärungen ohne Code-Änderung: kein Update nötig.

## Status-Definitionen

### Requirement Status
| Status | Bedeutung |
|--------|-----------|
| `OPEN` | Ziel noch nicht erreicht |
| `DONE` | User hat bestätigt dass das Ziel erreicht ist |
| `REJECTED` | User hat das Requirement verworfen – NICHT neu vorschlagen |

### Task Status
| Status | Bedeutung |
|--------|-----------|
| `PROPOSED` | Vorgeschlagen, wartet auf User-Bestätigung |
| `VALIDATED` | Bestätigt, noch nicht gestartet |
| `IN PROGRESS` | Wird gerade umgesetzt |
| `DONE` | Technisch fertig, wartet auf Validierung |
| `DONE-VALIDATED` | Fertig + vom User abgenommen |
| `DONE-NOT VALIDATED` | Fertig aber User noch nicht befragt |
| `REJECTED` | Wird nicht umgesetzt |

## Regeln

- NIEMALS Memory ignorieren
- NIEMALS Einträge löschen (als `REJECTED` markieren)
- Datum immer im Format `YYYY-MM-DD`
