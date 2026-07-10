# Decided radar items

The radar-watcher reads this file FIRST each week and skips anything already listed here, so no item is
ever re-surfaced. Append one line per triaged candidate.

Format: `<slug> | <title> | accept | reject | <YYYY-MM-DD> | <one-line note>`

- radar-0703-background-subagents | Subagents background-by-default (2.1.198) | accept | 2026-07-04 | adopted as V14a: `run_in_background: false` delegation default + never advance phase before all notifications (commit f6f49d3)
- radar-0703-agent-permission-rules | Declarative `Agent(...)` permission rules | accept | 2026-07-04 | adopted as V14b: `deny: Agent(project-manager)` in both kit settings, defense-in-depth beside guard_agent_spawn (f6f49d3)
- radar-0703-matcher-audit-a1 | Hook-matcher audit / PowerShell bypass (A1) | accept | 2026-07-04 | adopted as V11: all shell gates match Bash AND PowerShell (tool check + settings matcher) + test (f6f49d3)
