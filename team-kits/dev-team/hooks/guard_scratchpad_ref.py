#!/usr/bin/env python3
"""
PostToolUse(Edit|Write) — block repo source files that reference session-scratchpad paths.

A real run committed a fonts.css saying "Regenerate via scratchpad/vendor_fonts.py" — the tool
lived in the subagent's session scratchpad and is gone forever; the font pipeline stopped being
reproducible and no guard noticed. Scratchpads are session-ephemeral: any tool a repo file depends
on belongs in the repo (scripts/). Scope: source/tooling areas only (src, frontend, scripts, tests,
static, public + repo-root files) so docs/notes can still legitimately mention the word. Exit 2
feeds the writer the fix; uncertainty -> exit 0.
"""
import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _root import find_repo_root
import _audit


MARKERS = ("scratchpad/", "scratchpad\\", "Temp/claude", "Temp\\claude")
AREAS = ("src", "frontend", "scripts", "tests", "static", "public")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    path = ((data.get("tool_input") or {}).get("file_path")
            or (data.get("tool_input") or {}).get("path") or "")
    if not path or not os.path.isfile(path):
        sys.exit(0)

    root = find_repo_root(data.get("cwd"))
    try:
        rel = os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        sys.exit(0)  # different drive etc.
    if rel.startswith(".."):
        sys.exit(0)  # outside the repo (e.g. the scratchpad itself)
    parts = rel.split("/")
    in_scope = parts[0] in AREAS or (len(parts) == 1 and not parts[0].startswith("."))
    if not in_scope:
        sys.exit(0)

    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except Exception:
        sys.exit(0)
    hits = [m for m in MARKERS if m in text]
    if not hits:
        sys.exit(0)

    _audit.record("guard_scratchpad_ref", rel)
    sys.stderr.write(
        "[team-kit guard] %s references a session scratchpad path (%s). Scratchpads are EPHEMERAL — "
        "the referenced tool/asset will be gone next session and the pipeline stops being "
        "reproducible (a real fonts.css pointed at a vanished scratchpad/vendor_fonts.py). Put the "
        "tool into the repo (scripts/) and reference it there, then remove the scratchpad "
        "mention.\n" % (rel, ", ".join(hits))
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
