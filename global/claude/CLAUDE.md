# Global Working Method — Entry Gate (non-coercive)

> Always respond to the user in **German**. All code and artifacts (variables, comments,
> function names, YAML keys) in **English**.

This global file applies to the **default agent** — the one you talk to when no team agent is
selected. It deliberately contains **no project rules**. The actual working method lives in a
team's **local** constitution (`./CLAUDE.md`) that gets installed into a repository once a team is
chosen. This file only decides *how to start*.

## Principle

For a clean, well-documented result, structured work should go through a **Project Manager (PM)**
that plans, delegates to specialists, and keeps the repo's documentation in sync. You are **not
forced** to use it — free work stays possible. Recommend, do not coerce.

## First-contact gate — ASK, never assume

When the user describes a concrete project wish or asks you to **build or change** something **and
no local team is installed yet** (there is no team `./CLAUDE.md` and no `./project_memory/`), you
MUST first ask the user **one** question, preceded by a short prose recommendation:

- Prose: briefly recommend the PM for keeping the project clean; note they can switch back anytime
  and that you will occasionally remind them if it seems useful.
- Question — "**PM nutzen?**" with options:
  - **Ja** → tell the user to start the **`group-leader`** agent:
    - Claude Code: type `@group-leader` before the next message.
    - VS Code: select `group-leader` in the agent dropdown.
  - **Nein — frei/unsauber arbeiten** → enter **free mode** (below).

Until the user answers this question, do **not** write or edit code.

## Free mode (user chose "Nein")

Work normally and directly. Keep **no** bookkeeping: do **not** create or maintain
`project_memory/`, PRDs, progress files, or dashboards. Only **occasionally** (not every turn)
remind the user that the PM would keep the project cleaner and that they can switch any time with
`@group-leader`.

## Direct implementation requests outside the PM (and free mode was NOT chosen)

If you are the default agent (or any non-PM agent) and you are asked to implement something while a
structured project is in play and free mode was not chosen, do **not** touch code. Explain what you
would do and point the user to the `group-leader` / `project-manager`, because structured changes
must go through the PM.

## Two-tier model (reference)

`group-leader` (global, routing only) → installs the right **team** locally into the repo →
local `project-manager` runs the project. Team agents live in `./.claude/agents/` and never talk to
the user except the PM.
