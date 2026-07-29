#!/usr/bin/env python3
"""Convert a raw CIBIL XML response into the two raw extracts the bureau pipeline
consumes: ``scrub.csv`` (one row per tradeline) + ``enq.csv`` (one row per enquiry).

These feed ``bureau_data_report_creation.py`` (via ``tools/bureau_data_generator.py``),
which derives ``payhist_1..36`` / ``dt1..36`` / ``max_dpd*`` / ``scrub_date`` itself —
so we only emit the raw columns it reads. Per-pull constants (``crn``, ``report_month``,
``reference_date``, ``tu_score``) come from the XML ``header`` / ``scoreList``.

Usage: python bureau_data_xml_converter.py <xml_file> [output_dir=data]
"""
import csv
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ── accountType code → loan_type_new text ────────────────────────────────────
# Standard CIBIL account-type code → loan_type_new. Label text is aligned to the
# project's canonical taxonomy in schemas/loan_type.py, which is deliberately worded
# so it (a) exact-matches LOAN_TYPE_NORMALIZATION_MAP (Python) and (b) uppercases to
# the CASE labels in bureau_data_report_creation.py:18-90 (SQL account_type_cd). Keep
# both in sync. Codes not listed → "" → account_type_cd 0 / LoanType.OTHER downstream.
LOAN_TYPE_CODE_MAP: dict[str, str] = {
    "00": "Other",
    "01": "Auto Loan (Personal)",
    "02": "Housing Loan",
    "03": "Property Loan",
    "04": "Loan Against Shares/Securities",
    "05": "Personal Loan",
    "06": "Consumer Loan",
    "07": "Gold Loan",
    "08": "Education Loan",
    "09": "Loan to Professional",
    "10": "Credit Card",
    "11": "Leasing",
    "12": "Overdraft",
    "13": "Two-wheeler Loan",
    "14": "Non-Funded Credit Facility",
    "15": "Loan Against Bank Deposits",
    "16": "Fleet Card",
    "17": "Commercial Vehicle Loan",
    "18": "Telco - Wireless",
    "19": "Telco - Broadband",
    "20": "Telco - Landline",
    "21": "Seller Financing",
    "23": "GECL Loan Secured",
    "24": "GECL Loan Unsecured",
    "31": "Secured Credit Card",
    "32": "Used Car Loan",
    "33": "Construction Equipment Loan",
    "34": "Tractor Loan",
    "35": "Corporate Credit Card",
    "36": "Kisan Credit Card",
    "37": "Loan on Credit Card",
    "38": "Prime Minister Jaan Dhan Yojana - Overdraft",
    "39": "Mudra Loans - Shishu / Kishor / Tarun",
    "40": "Microfinance - Business Loan",
    "41": "Microfinance - Personal Loan",
    "42": "Microfinance - Housing Loan",
    "43": "Microfinance - Other",
    "44": "Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS",
    "45": "P2P Personal Loan",
    "46": "P2P Auto Loan",
    "47": "P2P Education Loan",
    "50": "Business Loan - Secured",
    "51": "Business Loan - General",
    "52": "Business Loan - Priority Sector - Small Business",
    "53": "Business Loan - Priority Sector - Agriculture",
    "54": "Business Loan - Priority Sector - Others",
    "55": "Business Non-Funded Credit Facility - General",
    "56": "Business Non-Funded Credit Facility - Priority Sector - Small Business",
    "57": "Business Non-Funded Credit Facility - Priority Sector - Agriculture",
    "58": "Business Non-Funded Credit Facility - Priority Sector-Others",
    "59": "Business Loan Against Bank Deposits",
    "61": "Business Loan - Unsecured",
    "69": "Short Term Personal Loan",
    "70": "Priority Sector - Gold Loan",
    "71": "Temporary Overdraft",
    "98": "Secured (Account Group For Portfolio Review Response)",
}

# Output column order (raw inputs the report-creation script reads).
SCRUB_COLUMNS = [
    "crn", "report_month", "reference_date", "loan_type_new", "loan_status",
    "loan_classification", "ownership_type", "sector", "sanction_amount",
    "high_credit_amount", "creditlimit", "out_standing_balance", "over_due_amount",
    "emi", "tu_score", "date_opened", "date_closed", "datereported_trades",
    "last_payment_date", "pay_hist_start_date", "pay_hist_end_date", "dpd_string",
    # `base` is an inert pass-through the report-creation SQL selects but never uses
    # (dropped before final output) — required only so its binder resolves; emitted
    # empty. `CV_RN` is a computed dedup discriminator (see build_scrub_rows): the
    # feature-creator's GROUP BY keeps rows with distinct CV_RN separate. Also dropped
    # before the canonical dpd_data.csv.
    "base", "CV_RN",
]
ENQ_COLUMNS = [
    "crn", "report_month", "reference_date", "DateOfEnquiry",
    "EnquiringMemberShortName", "ENQUIRYPURPOSE_NEW", "enquiryamount",
]

# Date formats seen in the XML: DD-Mon-YYYY, DDMMYYYY, DD-Mon-YY.
_DATE_FORMATS = ("%d-%b-%Y", "%d%m%Y", "%d-%b-%y")


def load_root(xml_file):
    """Parse the XML, tolerating the trailing non-breaking space / BOM the raw
    CIBIL responses carry (which makes a plain ET.parse() fail)."""
    text = Path(xml_file).read_text(encoding="utf-8", errors="replace")
    text = text.replace("\xa0", "").lstrip("﻿").strip()
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)


def to_iso(raw):
    """Normalise a bureau date string to ISO YYYY-MM-DD; '' for blank/unparseable."""
    raw = (raw or "").strip()
    if not raw or raw.upper() == "NULL":
        return ""
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _pull_constants(root):
    """crn / report_month / reference_date / tu_score — one value per XML pull."""
    header = root.find(".//header")
    crn = header.findtext("enquiryControlNumber", "") if header is not None else ""
    # Normalise to the canonical integer form the whole pipeline uses to key on crn
    # (run_bureau casts to int, extractor uses _safe_int, string-match sites compare
    # str(crn)). enquiryControlNumber carries a leading zero (010472013940) — keeping
    # it would break every crn match. Strip it here so all sites agree.
    crn = str(int(crn)) if crn.strip().isdigit() else crn.strip()
    proc_iso = to_iso(header.findtext("dateProceed", "")) if header is not None else ""
    # report_month = latest reported month + 1, so scrub_date (= last day of the month
    # before report_month) lands on the END of the latest reported month — matching the
    # pipeline convention (committed sample: pay_hist_start 2026-01-01 → report_month
    # 202602). Anchor on the newest paymentHistoryStartDate; fall back to the processing
    # date only when no payment-history dates are present.
    ph = [d for d in (to_iso(a.findtext("paymentHistoryStartDate", ""))
                      for a in root.findall(".//accountList")) if d]
    anchor = max(ph) if ph else proc_iso
    if anchor:
        y, m = int(anchor[:4]), int(anchor[5:7])
        report_month = f"{y + m // 12}{m % 12 + 1:02d}"  # YYYYMM, one month after anchor
    else:
        report_month = ""
    tu_score = root.findtext(".//scoreList/cibilScore", "") or ""
    return {
        "crn": crn,
        "report_month": report_month,
        "reference_date": proc_iso,
        "tu_score": tu_score,
    }


def _sanction_num(a):
    """Numeric sanctionAmount for CV_RN ordering; blank / non-numeric → 0.0."""
    try:
        return float((a.findtext("sanctionAmount", "") or "").strip())
    except ValueError:
        return 0.0


def build_scrub_rows(root, const):
    accounts = root.findall(".//accountList")

    # CV_RN — dedup discriminator inside the feature-creator's GROUP BY. To honour the
    # "keep every tradeline" requirement, give EVERY account a distinct row number
    # (ROW_NUMBER() OVER(ORDER BY sanction_amount) — the source's CV-only rule extended
    # to all loan types), so genuinely-distinct-but-alike loans are never collapsed:
    # CV/CE fleet loans reported without an accountNumber AND other types (e.g. two
    # Business Loans with distinct account numbers but otherwise identical fields).
    # One XML = one customer, so the rank spans all accounts (no PARTITION); a stable
    # sort by sanction_amount keeps XML order for ties → deterministic ranks.
    rank_by_id = {}
    for rn, a in enumerate(sorted(accounts, key=_sanction_num), start=1):
        rank_by_id[id(a)] = rn

    rows = []
    for a in accounts:
        code = a.findtext("accountTypeCode", "") or a.findtext("accountType", "")
        date_closed = to_iso(a.findtext("dateClosed", ""))
        rows.append({
            "crn": const["crn"],
            "report_month": const["report_month"],
            "reference_date": const["reference_date"],
            "loan_type_new": LOAN_TYPE_CODE_MAP.get(code.strip(), ""),
            "loan_status": "Closed" if date_closed else "Live",
            "loan_classification": "",
            "ownership_type": a.findtext("accountRelation", ""),
            "sector": a.findtext("reportingMemberShortName", ""),
            "sanction_amount": a.findtext("sanctionAmount", ""),
            "high_credit_amount": a.findtext("highCreditOrSanctionedAmount", ""),
            "creditlimit": a.findtext("creditLimit", ""),
            "out_standing_balance": a.findtext("currentBalance", ""),
            "over_due_amount": a.findtext("overdueAmount", ""),
            "emi": a.findtext("emiAmount", ""),
            "tu_score": const["tu_score"],
            "date_opened": to_iso(a.findtext("dateOpenedOrDisbursed", "")),
            "date_closed": date_closed,
            "datereported_trades": to_iso(a.findtext("dateReportedAndCertified", "")),
            "last_payment_date": to_iso(a.findtext("dateOfLastPayment", "")),
            "pay_hist_start_date": to_iso(a.findtext("paymentHistoryStartDate", "")),
            "pay_hist_end_date": to_iso(a.findtext("paymentHistoryEndDate", "")),
            "dpd_string": (a.findtext("paymentHistory1", "") or "")
                          + (a.findtext("paymentHistory2", "") or ""),
            "base": "",
            # Distinct rank per tradeline → no row is ever collapsed in the GROUP BY.
            "CV_RN": str(rank_by_id[id(a)]),
        })
    return rows


def build_enq_rows(root, const):
    rows = []
    for e in root.findall(".//enquiryList"):
        rows.append({
            "crn": const["crn"],
            "report_month": const["report_month"],
            "reference_date": const["reference_date"],
            "DateOfEnquiry": to_iso(e.findtext("enquiryDate", "")),
            "EnquiringMemberShortName": e.findtext("reportingMemberShortName", ""),
            "ENQUIRYPURPOSE_NEW": e.findtext("enquiryPurpose", ""),
            "enquiryamount": e.findtext("enquiryAmount", ""),
        })
    return rows


def write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written {len(rows)} rows to {path}")


def convert(xml_file, scrub_path, enq_path):
    """Parse a raw CIBIL XML and write the two extracts the pipeline consumes.

    ``scrub_path`` / ``enq_path`` are the exact destinations (callers pass
    ``config.settings.SCRUB_FILE`` / ``ENQ_FILE`` so output lands where
    ``ensure_data()`` reads). Returns the per-pull constants dict
    (``crn``, ``report_month``, ``reference_date``, ``tu_score``) so the caller
    can derive the CRN without re-parsing.
    """
    root = load_root(xml_file)
    const = _pull_constants(root)
    for p in (scrub_path, enq_path):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    write_csv(scrub_path, SCRUB_COLUMNS, build_scrub_rows(root, const))
    write_csv(enq_path, ENQ_COLUMNS, build_enq_rows(root, const))
    return const


def main():
    if len(sys.argv) < 2:
        print("Usage: python bureau_data_xml_converter.py <xml_file> [output_dir=data]")
        sys.exit(1)

    xml_file = sys.argv[1]
    output_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "data")
    if not Path(xml_file).exists():
        print(f"Error: File not found: {xml_file}", file=sys.stderr)
        sys.exit(1)

    const = convert(xml_file, output_dir / "scrub.csv", output_dir / "enq.csv")
    print(f"Pull constants: {const}")
    if not LOAN_TYPE_CODE_MAP:
        print("WARNING: LOAN_TYPE_CODE_MAP is empty — loan_type_new emitted blank.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
