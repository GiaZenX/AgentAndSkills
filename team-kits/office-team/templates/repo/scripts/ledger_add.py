#!/usr/bin/env python3
"""
ledger_add.py — the ONLY way entries enter the ledger (append-only, validated).

An LLM editing a CSV of money data is the wrong tool: this script validates every row and refuses
bad data, so the ledger cannot silently rot. Direct Edit/Write on ledger/*.csv is hook-blocked
for every role. Corrections are explicit reversal entries (--doc-type reversal --reverses <id>),
never edits — GoBD-inspired immutability (NOT certified revision-safe archiving; the reports say
so too).

Usage (bookkeeper):
  python scripts/ledger_add.py --year 2026 --direction expense --doc-type invoice \
    --doc-date 2026-07-01 --payment-date 2026-07-03 --counterparty "Muster GmbH" \
    --invoice-no RE-2026-114 --net 100.00 --vat-rate 19 --gross 119.00 \
    --vat-treatment standard --category shipping --source "archive/finance/.../file.pdf"
  # unpaid: --open instead of --payment-date;  reversal: --doc-type reversal --reverses <id>

Exit 0 = appended. Exit 1 = refused (reason on stderr) — fix the DATA, never the ledger.
"""
import argparse
import csv
import datetime
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLUMNS = ["id", "doc_date", "payment_date", "direction", "doc_type", "counterparty",
           "invoice_no", "net", "vat_rate", "gross", "vat_treatment", "category", "source",
           "reverses", "note"]
DIRECTIONS = ("income", "expense")
DOC_TYPES = ("invoice", "credit_note", "refund", "fee", "reversal", "other")
VAT_TREATMENTS = ("standard", "reverse_charge", "kleinunternehmer", "oss", "exempt")


def refuse(msg):
    sys.stderr.write("[ledger_add] REFUSED: %s\n" % msg)
    sys.exit(1)


def parse_date(label, value, required=True):
    if not value:
        if required:
            refuse("%s is required (YYYY-MM-DD)" % label)
        return ""
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        refuse("%s %r is not a valid YYYY-MM-DD date" % (label, value))
    return value


def parse_amount(label, value):
    try:
        amount = round(float(str(value).replace(",", ".")), 2)
    except ValueError:
        refuse("%s %r is not a number" % (label, value))
    if amount < 0:
        refuse("%s must be >= 0 — direction/doc-type encode the sign (use credit_note/reversal)" % label)
    return amount


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--direction", required=True, choices=DIRECTIONS)
    ap.add_argument("--doc-type", required=True, choices=DOC_TYPES)
    ap.add_argument("--doc-date", required=True)
    ap.add_argument("--payment-date", default="")
    ap.add_argument("--open", action="store_true", help="explicitly unpaid (no payment date yet)")
    ap.add_argument("--counterparty", required=True)
    ap.add_argument("--invoice-no", default="")
    ap.add_argument("--net", required=True)
    ap.add_argument("--vat-rate", required=True, help="percent, e.g. 19, 7 or 0")
    ap.add_argument("--gross", required=True)
    ap.add_argument("--vat-treatment", required=True, choices=VAT_TREATMENTS)
    ap.add_argument("--category", required=True)
    ap.add_argument("--source", required=True, help="archive/ path of the source document")
    ap.add_argument("--reverses", default="", help="entry id a reversal cancels")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    doc_date = parse_date("--doc-date", args.doc_date)
    if args.open and args.payment_date:
        refuse("--open and --payment-date are mutually exclusive")
    if not args.open and not args.payment_date:
        refuse("give --payment-date (Zufluss/Abfluss: reports count by payment) or mark --open explicitly")
    payment_date = parse_date("--payment-date", args.payment_date, required=False)

    # year consistency: an entry whose effective date lives in another year would land in the wrong
    # CSV and silently vanish from EVERY report (year-boundary invoices are routine).
    effective = payment_date or doc_date
    if effective[:4] != str(args.year):
        refuse("--year %d does not match the entry's %s year (%s) — book it into ledger/%s.csv"
               % (args.year, "payment" if payment_date else "document", effective, effective[:4]))

    net = parse_amount("--net", args.net)
    gross = parse_amount("--gross", args.gross)
    try:
        vat_rate = round(float(str(args.vat_rate).replace(",", ".")), 2)
    except ValueError:
        refuse("--vat-rate %r is not a number" % args.vat_rate)

    # arithmetic check: catches extraction/OCR errors before they reach the books.
    if args.vat_treatment == "standard":
        expected = round(net * (1 + vat_rate / 100.0), 2)
        if abs(expected - gross) > 0.011:
            refuse("net %.2f * (1 + %.2f%%) = %.2f != gross %.2f — re-read the document; a value "
                   "you cannot read is UNCLEAR, never guessed" % (net, vat_rate, expected, gross))
    elif args.vat_treatment in ("reverse_charge", "kleinunternehmer", "exempt"):
        if vat_rate not in (0, 0.0):
            refuse("vat-rate must be 0 for %s (the treatment field carries the tax logic)"
                   % args.vat_treatment)
        if abs(net - gross) > 0.011:
            refuse("net must equal gross for %s entries (no VAT in the amount)" % args.vat_treatment)

    if args.doc_type == "reversal" and not args.reverses:
        refuse("a reversal entry needs --reverses <entry id>")
    if args.reverses and args.doc_type != "reversal":
        refuse("--reverses is only valid with --doc-type reversal")

    ledger_dir = os.path.join(ROOT, "ledger")
    os.makedirs(ledger_dir, exist_ok=True)
    path = os.path.join(ledger_dir, "%d.csv" % args.year)

    rows = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != COLUMNS:
                refuse("%s header does not match the schema — the ledger is script-owned; do not "
                       "edit it by hand" % path)
            rows = list(reader)

    # duplicate check: same counterparty + invoice number + gross (unless it IS a reversal).
    # Rows already cancelled by a reversal do NOT count as duplicates — otherwise the sanctioned
    # correction flow (book -> reversal -> re-book corrected) dead-ends on its own rule.
    if args.invoice_no and args.doc_type != "reversal":
        cancelled = {r.get("reverses") for r in rows
                     if r.get("doc_type") == "reversal" and r.get("reverses")}
        for r in rows:
            if (r.get("invoice_no") == args.invoice_no
                    and r.get("counterparty") == args.counterparty
                    and abs(float(r.get("gross") or 0) - gross) < 0.011
                    and r.get("doc_type") != "reversal"
                    and r.get("id") not in cancelled):
                refuse("duplicate: %s / %s / %.2f already booked as %s — if this is a correction, "
                       "book a reversal first" % (args.counterparty, args.invoice_no, gross, r.get("id")))
    if args.reverses and not any(r.get("id") == args.reverses for r in rows):
        refuse("--reverses %s: no such entry in %s" % (args.reverses, path))

    entry_id = "L%d-%04d" % (args.year, len(rows) + 1)
    row = {
        "id": entry_id, "doc_date": doc_date, "payment_date": payment_date,
        "direction": args.direction, "doc_type": args.doc_type,
        "counterparty": args.counterparty, "invoice_no": args.invoice_no,
        "net": "%.2f" % net, "vat_rate": "%.2f" % vat_rate, "gross": "%.2f" % gross,
        "vat_treatment": args.vat_treatment, "category": args.category,
        "source": args.source.replace("\\", "/"), "reverses": args.reverses, "note": args.note,
    }

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    if not rows and not os.path.isfile(path):
        writer.writeheader()
    writer.writerow(row)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())

    print("[ledger_add] appended %s: %s %s %.2f EUR gross (%s, %s)"
          % (entry_id, args.direction, args.counterparty, gross,
             payment_date or "OPEN/unpaid", args.category))


if __name__ == "__main__":
    main()
