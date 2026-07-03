# Project security-review policy (read by the security-guidance plugin's LLM reviewer)

Scope guidance for this repository:

- `project_memory/**` (YAML bookkeeping: requirements, tasks, reports, decisions, progress) and all
  GENERATED artifacts (`project_memory/*.html`, `project_memory/dashboard_history/**`,
  `project_memory/reports/*.html`) are **project state, not executable code**. Do NOT deep-review them;
  the only finding worth raising there is an actual committed secret/credential.
- Focus the review effort on real code: `src/**`, `frontend/**`, `backend/**`, `scripts/**`, CI config.
- The repository additionally enforces SAST/SCA/secret scanning at the merge gate (scripts/quality.py:
  bandit, pip-audit/npm audit, gitleaks) — treat those classes as covered there; prioritise logic-level
  issues (injection sinks, unsafe deserialization, authz gaps) in application code.
