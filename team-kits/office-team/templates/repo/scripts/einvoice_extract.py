#!/usr/bin/env python3
"""
einvoice_extract.py — structured invoice data from e-invoices (XRechnung XML / ZUGFeRD PDF).

E-invoice FIRST: since 2025 German B2B invoices arrive as structured XML (XRechnung, or embedded
in a ZUGFeRD/Factur-X PDF). Parsing XML is deterministic — no OCR guessing, no hallucinated
amounts. Supports the common fields of both CII (CrossIndustryInvoice) and UBL syntaxes,
best-effort: anything not found prints as MISSING (the bookkeeper treats it as UNCLEAR, never
invents it).

Usage: python scripts/einvoice_extract.py <file.xml|file.pdf>
Output: key: value lines (seller, invoice_no, issue_date, currency, net, tax, gross).
Exit 0 = something extracted; exit 1 = no structured data found (fall back to careful reading +
the arithmetic check in ledger_add.py).
"""
import os
import re
import sys

try:
    # supplier XML is UNTRUSTED input: defusedxml neutralizes XXE/billion-laughs, which the
    # stdlib parser does not fully — no silent fallback to an unsafe parser.
    import defusedxml.ElementTree as ET  # type: ignore[import-untyped]
    from xml.etree.ElementTree import ParseError
except ImportError:
    ET = None
    ParseError = Exception


def _txt(root, *local_names):
    """First text content of an element whose LOCAL name matches (namespace-agnostic)."""
    want = set(local_names)
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] in want and (el.text or "").strip():
            return el.text.strip()
    return ""


def _cii_invoice_no(root):
    """CII: the invoice number is ExchangedDocument's DIRECT child ID. A naive first-ID-in-document
    search returns the guideline URN (GuidelineSpecifiedDocumentContextParameter/ID precedes it) —
    a confidently WRONG value that would poison the ledger's duplicate detection."""
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] == "ExchangedDocument":
            for child in el:
                if child.tag.rsplit("}", 1)[-1] == "ID" and (child.text or "").strip():
                    return child.text.strip()
    return ""


def parse_xml(data):
    if ET is None:
        sys.stderr.write("[einvoice] defusedxml not installed (pip install -r "
                         "requirements-office.txt) — refusing to parse untrusted supplier XML "
                         "with an XXE-vulnerable parser\n")
        return None
    try:
        root = ET.fromstring(data)
    except (ParseError, ValueError) as e:
        sys.stderr.write("[einvoice] XML parse error: %s\n" % e)
        return None
    tag = root.tag.rsplit("}", 1)[-1]
    out = {"syntax": tag}
    if tag == "CrossIndustryInvoice":            # CII (ZUGFeRD/XRechnung-CII)
        out["invoice_no"] = _cii_invoice_no(root)
        out["issue_date"] = _txt(root, "DateTimeString")
        out["seller"] = _txt(root, "Name")
        out["currency"] = _txt(root, "InvoiceCurrencyCode")
        out["net"] = _txt(root, "TaxBasisTotalAmount", "LineTotalAmount")
        out["tax"] = _txt(root, "TaxTotalAmount")
        out["gross"] = _txt(root, "GrandTotalAmount")
    elif tag in ("Invoice", "CreditNote"):        # UBL (XRechnung-UBL)
        out["invoice_no"] = _txt(root, "ID")
        out["issue_date"] = _txt(root, "IssueDate")
        out["seller"] = _txt(root, "RegistrationName", "Name")
        out["currency"] = _txt(root, "DocumentCurrencyCode")
        out["net"] = _txt(root, "TaxExclusiveAmount", "LineExtensionAmount")
        out["tax"] = _txt(root, "TaxAmount")
        out["gross"] = _txt(root, "TaxInclusiveAmount", "PayableAmount")
    else:
        sys.stderr.write("[einvoice] unknown root element <%s> — not a known e-invoice syntax\n" % tag)
        return None
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", out.get("issue_date") or "")
    if m:
        out["issue_date"] = "%s-%s-%s" % m.groups()   # CII format 102 -> ISO
    return out


def extract_pdf_xml(path):
    """Embedded XML from a ZUGFeRD/Factur-X PDF via pypdf (optional dependency)."""
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError:
        sys.stderr.write("[einvoice] pypdf not installed (pip install pypdf) — cannot check the "
                         "PDF for embedded e-invoice XML\n")
        return None
    try:
        reader = PdfReader(path)
        for name, f in (reader.attachments or {}).items():
            if name.lower().endswith(".xml"):
                data = f[0] if isinstance(f, list) else f
                return bytes(data)
    except Exception as e:
        sys.stderr.write("[einvoice] PDF attachment read failed: %s\n" % e)
    return None


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: einvoice_extract.py <file.xml|file.pdf>\n")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.isfile(path):
        sys.stderr.write("[einvoice] not found: %s\n" % path)
        sys.exit(1)
    if path.lower().endswith(".xml"):
        data = open(path, "rb").read()
    elif path.lower().endswith(".pdf"):
        data = extract_pdf_xml(path)
        if data is None:
            sys.stderr.write("[einvoice] no embedded XML — plain PDF: read carefully; UNCLEAR "
                             "fields stay UNCLEAR (ledger_add's arithmetic check is the net)\n")
            sys.exit(1)
    else:
        sys.stderr.write("[einvoice] unsupported extension (xml/pdf)\n")
        sys.exit(1)

    out = parse_xml(data)
    if not out:
        sys.exit(1)
    for key in ("syntax", "seller", "invoice_no", "issue_date", "currency", "net", "tax", "gross"):
        print("%s: %s" % (key, out.get(key) or "MISSING"))


if __name__ == "__main__":
    main()
