#!/usr/bin/env python3
"""
agents-and-skills status line.

Claude Code pipes session JSON to this script on stdin; whatever it prints to stdout
becomes the status line. Shows: model, a context-usage bar + %, session cost, git branch,
and the 5-hour rate-limit usage (Pro/Max). Robust to missing/null fields. Runs locally,
consumes no API tokens.
"""
import sys
import os
import json
import subprocess


def main():
    # Force UTF-8 stdout so the bar/glyphs render regardless of the OS code page (Windows cp1252).
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        data = json.load(sys.stdin)
    except Exception:
        print("")
        return

    model = (data.get("model") or {}).get("display_name") or "?"

    cw = data.get("context_window") or {}
    pct = cw.get("used_percentage")
    pct = int(pct) if isinstance(pct, (int, float)) else 0
    filled = max(0, min(10, pct * 10 // 100))
    bar = "▓" * filled + "░" * (10 - filled)

    cost = (data.get("cost") or {}).get("total_cost_usd")
    cost = cost if isinstance(cost, (int, float)) else 0.0

    parts = ["[%s]" % model, "%s %d%%" % (bar, pct), "$%.2f" % cost]

    branch = git_branch(data)
    if branch:
        parts.append("\U0001f33f %s" % branch)

    rl = ((data.get("rate_limits") or {}).get("five_hour") or {}).get("used_percentage")
    if isinstance(rl, (int, float)):
        parts.append("5h %d%%" % round(rl))

    print("  ·  ".join(parts))


def git_branch(data):
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    try:
        out = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=cwd, stderr=subprocess.DEVNULL, text=True, timeout=2,
        ).strip()
        return out or None
    except Exception:
        return None


if __name__ == "__main__":
    main()
