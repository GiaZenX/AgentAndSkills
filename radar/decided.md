# Decided radar items

The radar-watcher reads this file FIRST each week and skips anything already listed here, so no item is
ever re-surfaced. Append one line per triaged candidate.

Format: `<slug> | <title> | accept | reject | <YYYY-MM-DD> | <one-line note>`

- radar-0703-background-subagents | Subagents background-by-default (2.1.198) | accept | 2026-07-04 | adopted as V14a: `run_in_background: false` delegation default + never advance phase before all notifications (commit f6f49d3)
- radar-0703-agent-permission-rules | Declarative `Agent(...)` permission rules | accept | 2026-07-04 | adopted as V14b: `deny: Agent(project-manager)` in both kit settings, defense-in-depth beside guard_agent_spawn (f6f49d3)
- radar-0703-matcher-audit-a1 | Hook-matcher audit / PowerShell bypass (A1) | accept | 2026-07-04 | adopted as V11: all shell gates match Bash AND PowerShell (tool check + settings matcher) + test (f6f49d3)
- radar-0706-subagent-reliability | Subagent/background reliability fixes (2.1.200) | reject | 2026-07-10 | no harness change — platform now fails empty subagents cleanly, matching §14a's assumption (noted in 40af990)
- radar-0706-askuserquestion-no-autocontinue | AskUserQuestion no longer auto-continues | reject | 2026-07-10 | benign — behaviour now matches the harness's user-gate intent; nothing to change
- radar-0706-notification-agent-events | Notification hook fires for background agents (2.1.198) | accept | 2026-07-10 | adopted as R1: notify_agent_events.py in both kits logs agent_completed/agent_needs_input to project_memory/.audit (40af990)
- radar-0706-permission-mode-rename | Permission mode "default" renamed "Manual" | reject | 2026-07-10 | cosmetic; kit settings set no defaultMode

