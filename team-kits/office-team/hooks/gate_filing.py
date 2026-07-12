#!/usr/bin/env python3
"""
PostToolUse(Edit|Write) on filing_log.yaml — a filing claim is verified, not trusted.

Every `filed:` entry must point at a file that actually EXISTS under archive/ — "inbox processed"
with a phantom target is exactly the self-reported-success class this harness exists to kill.
Blocks with the missing entries listed. Uncertainty -> exit 0.
"""
import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _root import find_repo_root
import _audit


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    path = ((data.get("tool_input") or {}).get("file_path")
            or (data.get("tool_input") or {}).get("path") or "")
    if os.path.basename(path.replace("\\", "/")) != "filing_log.yaml":
        sys.exit(0)
    if not os.path.isfile(path):
        sys.exit(0)
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        sys.exit(0)
    try:
        doc = yaml.safe_load(open(path, encoding="utf-8", errors="ignore").read()) or {}
    except Exception:
        sys.exit(0)  # guard_yaml_valid owns broken YAML

    root = find_repo_root(data.get("cwd"))
    problems = []
    for entry in (doc.get("filed") or []):
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target") or "").replace("\\", "/")
        if not target:
            problems.append("entry without target: %r" % entry.get("source"))
            continue
        if not target.startswith("archive/"):
            problems.append("%s -> %s (targets must live under archive/)" % (entry.get("source"), target))
            continue
        if not os.path.isfile(os.path.join(root, target)):
            problems.append("%s -> %s (file does NOT exist)" % (entry.get("source"), target))
    if problems:
        _audit.record("gate_filing", "; ".join(problems[:3]))
        sys.stderr.write(
            "[team-kit gate] filing_log.yaml claims filings that are not real:\n%s\n"
            "Move the file(s) under archive/ FIRST, then log — a log entry is a verified fact, "
            "not an intention.\n" % "\n".join("  - " + p for p in problems[:8])
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
