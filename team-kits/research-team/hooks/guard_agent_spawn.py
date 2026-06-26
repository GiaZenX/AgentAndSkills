#!/usr/bin/env python3
"""
PreToolUse(Agent|Task) guard — only role-based specialist spawns are allowed.

Kills the `subagent_type=None` / generic-agent spawn bug from the real test run.
The PM (main agent) MUST spawn specialists by their exact role. This hook reads the
allowed roles from the installed `./.claude/agents/*.md` basenames, so it is
kit-agnostic and always correct. Exit 2 + stderr blocks; uncertainty -> exit 0.
"""
import sys
import os
import json
import glob


def block(why):
    sys.stderr.write(
        "[team-kit guard] Agent spawn blocked: %s\n"
        "Spawn a specialist by its EXACT role as subagent_type (one of the installed "
        "./.claude/agents/). Never spawn a generic/unnamed agent.\n" % why
    )
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in ("Agent", "Task"):
        sys.exit(0)
    inp = data.get("tool_input") or {}
    sub = inp.get("subagent_type")

    cwd = data.get("cwd") or os.getcwd()
    agents_dir = os.path.join(cwd, ".claude", "agents")
    if not os.path.isdir(agents_dir):
        sys.exit(0)  # can't determine the role set -> don't block
    roles = {os.path.splitext(os.path.basename(p))[0]
             for p in glob.glob(os.path.join(agents_dir, "*.md"))}
    if not roles:
        sys.exit(0)

    if not sub or not str(sub).strip():
        block("no subagent_type given (generic agent)")
    if str(sub) not in roles:
        block("subagent_type %r is not an installed role (%s)" % (sub, ", ".join(sorted(roles))))

    sys.exit(0)


if __name__ == "__main__":
    main()
