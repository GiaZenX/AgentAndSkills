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


def _drive_upper(path):
    """Windows: uppercase a lowercase drive letter (c:\\... -> C:\\...). The session cwd often
    carries the lowercase form, and a node/vite child spawned with it as cwd breaks on rollup's
    case-sensitive module identity (verified A/B: ONLY the drive letter matters — a real gate
    blocked a push for a whole night on exactly this). Deliberately lexical, NOT realpath():
    resolving junctions would change path identity for every prefix-comparing guard."""
    if os.name == "nt" and len(path) >= 2 and path[1] == ":":
        return path[0].upper() + path[1:]
    return path


def find_repo_root(start=None):
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return _drive_upper(os.path.abspath(env))
    base = _drive_upper(os.path.abspath(start or os.getcwd()))
    d = base
    while True:
        for marker in (".claude", "project_memory", ".git"):
            if os.path.exists(os.path.join(d, marker)):
                return d
        parent = os.path.dirname(d)
        if parent == d:
            return base
        d = parent
