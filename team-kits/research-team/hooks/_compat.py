#!/usr/bin/env python3
"""
Shared helper: provider payload adapter — ONE place that normalizes hook payloads.

Claude Code and Codex CLI send NEAR-identical hook JSON (same snake_case fields `tool_name`/
`tool_input`/`cwd`/`hook_event_name`, same exit-2 + stderr blocking contract — verified against
the official Codex hooks docs, 2026-07). The differences this shim absorbs:

  * Codex file edits arrive as tool_name "apply_patch" with the patch envelope in
    tool_input.command (no file_path). load() normalizes that to tool_name "Edit" and extracts
    EVERY touched file from the `*** Add|Update|Delete File:` headers; path guards iterate
    file_paths() so a multi-file patch cannot smuggle a blocked path past a single-path check.
  * Copilot hooks use camelCase (toolName/toolArgs/sessionId) — bridged to the snake_case names.
    NOTE: Copilot's documented DENY contract is a stdout JSON (`permissionDecision`), not exit 2;
    that emit is deliberately NOT implemented until it can be live-verified — the parity matrix
    lists Copilot hook blocking as UNVERIFIED, and gates there are backstopped by CI.

Uncertainty -> return the payload unchanged; a guard that cannot parse stays fail-open (exit 0),
same philosophy as every other hook.
"""
import json
import os
import re
import sys

try:
    from _root import find_repo_root
except Exception:  # standalone import (tests) — same fallback _audit uses
    def find_repo_root(start=None):
        return os.environ.get("CLAUDE_PROJECT_DIR") or start or os.getcwd()


_PATCH_FILE_RX = re.compile(r"(?m)^\*{3} (?:Add|Update|Delete) File: (.+?)\s*$")
_CAMEL = (("toolName", "tool_name"), ("toolArgs", "tool_input"),
          ("hookEventName", "hook_event_name"), ("sessionId", "session_id"))
# providers use different tool vocabularies (Copilot's camelCase surface uses lowercase names) —
# normalize the KNOWN aliases to the Claude names every guard filters on; unknown names pass
# through untouched (guards then fail open, by design).
_TOOL_ALIASES = {"edit": "Edit", "write": "Write", "bash": "Bash", "powershell": "PowerShell",
                 "str_replace": "Edit", "create_file": "Write", "shell": "Bash"}


def load(stream=None):
    """Read + normalize the hook payload from stdin. Never raises; returns {} on garbage."""
    try:
        data = json.load(stream or sys.stdin)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    for camel, snake in _CAMEL:  # Copilot bridge — snake_case always wins if both present
        if camel in data and snake not in data:
            data[snake] = data[camel]
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        ti = {}
        data["tool_input"] = ti
    tn = str(data.get("tool_name") or "")
    if tn in _TOOL_ALIASES:
        data["tool_name"] = _TOOL_ALIASES[tn]
    if data.get("tool_name") == "apply_patch":
        raw_paths = _PATCH_FILE_RX.findall(str(ti.get("command") or ti.get("input") or ""))
        # patch paths are CWD-relative (Codex applies the patch against the session cwd). Join
        # against cwd for the file the edit REALLY touches, and ADDITIONALLY against the repo
        # root when the two differ: block-guards then catch either interpretation (fail-closed
        # against cwd drift — the failure class _root.py exists for), while isfile-based checks
        # simply skip the nonexistent candidate. (Audit finding: cwd in a subdir made a
        # repo-root-looking patch path miss every prefix check.)
        base = str(data.get("cwd") or "")
        root = find_repo_root(base or None)
        paths = []
        for q in raw_paths:
            p = q.replace("\\", "/")
            if os.path.isabs(p):
                paths.append(p)
                continue
            paths.append(os.path.join(base, p) if base else p)
            if root and os.path.abspath(root) != os.path.abspath(base or root):
                cand = os.path.join(root, p)
                if cand not in paths:
                    paths.append(cand)
        data["tool_name"] = "Edit"
        data["_file_paths"] = paths
        if paths and not ti.get("file_path"):
            ti["file_path"] = paths[0]
    return data


def file_paths(data):
    """Every file this tool call touches (list of str; may be empty). Path guards MUST iterate
    this instead of reading tool_input.file_path once — a Codex multi-file patch is one call."""
    if isinstance(data.get("_file_paths"), list) and data["_file_paths"]:
        return [str(p) for p in data["_file_paths"]]
    ti = data.get("tool_input") or {}
    p = ti.get("file_path") or ti.get("path") or ""
    return [str(p)] if p else []
