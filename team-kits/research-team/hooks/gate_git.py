#!/usr/bin/env python3
"""
PreToolUse(Bash) gate — protects merge/push.

- Force-push is ALWAYS blocked (the constitution forbids it).
- `git push` / `git merge` are blocked once there is real work
  (an RQ entry exists) but NO passing QA/validation report yet.
  Empty/just-scaffolded repos are not gated.

Reads the hook JSON from stdin; exit 2 + stderr blocks. Any uncertainty -> exit 0.
"""
import sys
import os
import re
import json
import glob
import subprocess


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _root import find_repo_root
import _audit


def block(why):
    _audit.record("gate_git", why)
    sys.stderr.write("[team-kit gate] Blocked: %s\n" % why)
    sys.exit(2)


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        sys.exit(0)
    cmd = ((data.get("tool_input") or {}).get("command") or "")
    low = cmd.lower()
    if "git push" not in low and "git merge" not in low:
        sys.exit(0)

    # force-push: always forbidden (flags AND the `+refspec` form, e.g. `git push origin +main`)
    if "git push" in low and re.search(r"--force(-with-lease)?|(^|\s)-f(\s|$)|\s\+[\w./-]+(:|\s|$)", low):
        block("force-push is forbidden by the team constitution.")

    cwd = find_repo_root(data.get("cwd"))
    pm = os.path.join(cwd, "project_memory")
    if not os.path.isdir(pm):
        sys.exit(0)  # nothing to gate yet

    # is there real work? (a RQ entry exists)
    if not re.search(r"\n\s*RQ-\d", read_text(os.path.join(pm, "research_questions.yaml"))):
        sys.exit(0)

    # which RQ is being merged/pushed? (from the command, else the current branch name)
    target = None
    m = re.search(r"(RQ-\d+)", cmd, re.IGNORECASE)
    if not m:
        try:
            br = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=5).stdout
            m = re.search(r"(RQ-\d+)", br, re.IGNORECASE)
        except Exception:
            m = None
    if m:
        target = m.group(1).upper()

    # require a passing QA/validation/acceptance report — bound to THIS RQ when it is known,
    # so a stray `result: pass` from an unrelated/old report cannot lift the gate.
    passing = False
    for f in glob.glob(os.path.join(pm, "*report*.yaml")):
        txt = read_text(f)
        if not re.search(r"result:\s*pass|verdict:\s*pass", txt, re.IGNORECASE):
            continue
        if target is None or re.search(re.escape(target), txt, re.IGNORECASE):
            passing = True
            break
    if not passing:
        block("no passing QA/validation report for %s in project_memory — run the QA gate "
              "(a passing review/test/acceptance report for this RQ) before merge/push."
              % (target or "this work"))

    sys.exit(0)


if __name__ == "__main__":
    main()
