# Radar — weekly harness intelligence

A scheduled **radar-watcher** agent (`.claude/agents/radar-watcher.md`) runs once a week and writes a dated
report here (`radar/YYYY-MM-DD.md`). Each report does two things:

1. **Repo health** — runs `tools/validate.py`, `pytest tools/`, `ruff check .` and notes any drift.
2. **External scan** — what's new at **Anthropic / Claude Code** (changelog, docs, new hooks/tools/models/SDK)
   and in the **agent community** (orchestration, eval, prompting), filtered for **relevance to THIS harness**.
   Every item carries a **source URL + the date it was seen** — no source, no item.

The agent **never changes code** — it only writes reports here. You and the assistant then **triage** each
item (accept → becomes a hardening change, or reject) and record the verdict in `decided.md`, which the
watcher reads first each week so nothing is ever re-surfaced.

## Report shape (per candidate)
- **Title** · source URL · date seen
- **What it is** (1–2 lines)
- **Why it could help this repo** (concrete: which gate / skill / flow / artifact it improves)
- **Recommendation**: adopt / watch / ignore · rough effort
- **Status**: NEW (until triaged)

## Triage
Read the latest report, decide per item, and append the decision to `decided.md`
(`<slug> | <title> | accept|reject | <date> | <note>`). Accepted items become normal harness changes
(committed); rejected items stay in `decided.md` so the watcher skips them next week.
