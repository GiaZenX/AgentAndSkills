#!/usr/bin/env python3
"""
PreToolUse(Edit|Write) — the ledger is append-only and script-written; direct edits are blocked
for EVERY role (including the manager).

An LLM editing a CSV of money data is the wrong tool: entries go through
`python scripts/ledger_add.py`, which validates each row (schema, date formats,
net*(1+vat)≈gross, duplicate invoice detection) and refuses bad data; corrections are explicit
reversal entries. Uncertainty -> exit 0.
"""
import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
    norm = path.replace("\\", "/").lower()   # case-insensitive: Ledger/2026.CSV is the same file on Windows
    parts = norm.split("/")
    if "ledger" in parts and norm.endswith(".csv"):
        _audit.record("guard_ledger_direct", norm)
        sys.stderr.write(
            "[team-kit guard] Direct ledger edits are BLOCKED (append-only, script-validated). "
            "Add entries via `python scripts/ledger_add.py …` (it validates arithmetic, dates and "
            "duplicates); correct mistakes with a reversal entry (`--doc-type reversal "
            "--reverses <id>`), never by editing history.\n"
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
