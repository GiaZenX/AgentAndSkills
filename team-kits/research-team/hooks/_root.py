#!/usr/bin/env python3
"""
Shared helper: resolve the repo/project root independent of the current working
directory. A real test run had an agent's cwd slip into a subfolder (frontend/),
which broke every hook that trusted cwd. This makes root resolution cwd-proof.

Resolution order:
  1) $CLAUDE_PROJECT_DIR — Claude Code sets this to the session's project root and
     keeps it stable even if the agent `cd`s elsewhere.
  2) Walk UP from the hook JSON's `cwd` (or os.getcwd()) until a repo marker is found
     (.claude/ | project_memory/ | .git).
  3) Fallback to the original cwd.
"""
import os


def find_repo_root(start=None):
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    base = os.path.abspath(start or os.getcwd())
    d = base
    while True:
        for marker in (".claude", "project_memory", ".git"):
            if os.path.exists(os.path.join(d, marker)):
                return d
        parent = os.path.dirname(d)
        if parent == d:
            return base
        d = parent
