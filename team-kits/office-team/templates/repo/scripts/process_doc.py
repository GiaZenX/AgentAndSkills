#!/usr/bin/env python3
"""
process_doc.py — render the Verfahrensdokumentation DRAFT from the PROC definitions.

The GoBD expect a Verfahrensdokumentation (how documents are received, processed, stored). The
office kit gets one nearly for free: every approved PROC already IS a documented procedure. This
renders docs/verfahrensdokumentation.md deterministically — a DRAFT for the Steuerberater to
review, clearly labelled as such.

Usage: python scripts/process_doc.py
"""
import datetime
import os

import yaml  # type: ignore[import-untyped]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pm = os.path.join(ROOT, "project_memory")
    procs = (yaml.safe_load(open(os.path.join(pm, "process_definitions.yaml"),
                                 encoding="utf-8").read()) or {}).get("processes") or {}
    plan_path = os.path.join(pm, "filing_plan.yaml")
    plan = yaml.safe_load(open(plan_path, encoding="utf-8").read()) or {} if os.path.isfile(plan_path) else {}

    lines = ["# Verfahrensdokumentation (ENTWURF — generiert aus den Prozessdefinitionen)", "",
             "> Entwurf zur Prüfung durch die Steuerberatung — keine Steuer- oder Rechtsberatung.",
             "> Generiert: %s · Quelle: project_memory/process_definitions.yaml" % datetime.date.today().isoformat(),
             "", "## Ablage (Aktenplan)", "",
             "Namensregel: `%s`" % (plan.get("naming_rule") or "—"), ""]
    for node in (plan.get("tree") or []):
        if isinstance(node, dict):
            lines.append("- `%s` — Belegarten: %s — Aufbewahrung: %s"
                         % (node.get("path"), ", ".join(node.get("doc_types") or []),
                            node.get("retention") or "—"))
    lines += ["", "## Prozesse", ""]
    for pid in sorted(procs):
        body = procs.get(pid) or {}
        lines += ["### %s — %s (%s)" % (pid, body.get("title") or "", body.get("status") or "?"), "",
                  "- Auslöser: %s" % (body.get("trigger") or "—"),
                  "- Ausführende Rolle: %s" % (body.get("owner") or "—"),
                  "- Schritte:"]
        for step in (body.get("steps") or []):
            lines.append("  1. %s" % step)
        lines += ["- Ergebnisse: %s" % ", ".join(str(o) for o in (body.get("outputs") or [])),
                  "- Rückfragepunkte: %s" % ", ".join(str(a) for a in (body.get("approval_points") or [])),
                  ""]
    out_dir = os.path.join(ROOT, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "verfahrensdokumentation.md")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print("[process_doc] %s written (%d processes)" % (out, len(procs)))


if __name__ == "__main__":
    main()
