"""
Excel exporter for Bureau Analyser report data.

Usage (single customer):
    row = build_excel_row(customer_id, bureau_report, report_path, exposure_summary)
    export_row_to_excel(row, "reports/excel/100070028.xlsx")

Usage (batch merge):
    merge_excel_reports("reports/excel/", "reports/batch_output.xlsx")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

if TYPE_CHECKING:
    from schemas.bureau_report import BureauReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bureau-only template column order
# ---------------------------------------------------------------------------
TEMPLATE_COLUMNS = [
    "CRN",
    "Bureau Brief",
    "Bureau Segment",
    "Max DPD & Product",
    "CC Util",
    "Enquiries",
    "Payments Missed in l 18M",
    "Foir",
    "Exposure Commentary",
    "TU Score",
    "Bureau Income",
    "Stamp Loan",
    "Sustained EMI",
    "Aff EMI",
    "EMI Unsec",
    "Aff EMI Topup",
    "EMI Unsec Topup",
    "Current EMI",
    "Concerns",
    "Intelligent Report",
]


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def build_excel_row(
    customer_id: int,
    bureau_report: Optional[BureauReport],
    report_path: Optional[str],
    exposure_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Map available bureau report data onto the template columns.

    Columns that have no corresponding data field are set to None so the
    template column still appears in the output file.

    Args:
        customer_id:      Customer CRN
        bureau_report:    Populated BureauReport (credit-bureau side), may be None
        report_path:      Filesystem path to the generated report HTML/PDF
        exposure_summary: Deterministic exposure-timeline commentary

    Returns:
        Dict keyed by TEMPLATE_COLUMNS values, ready to be written as one row.
    """
    row: Dict[str, Any] = {col: None for col in TEMPLATE_COLUMNS}

    # ── CRN ──────────────────────────────────────────────────────────────────
    row["CRN"] = customer_id

    # ── Bureau Brief ──────────────────────────────────────────────────────────
    row["Bureau Brief"] = (bureau_report.narrative if bureau_report else None)

    # ── Bureau Segment ───────────────────────────────────────────────────────
    # tradeline_features.customer_segment (e.g. "Thick", "Thin")
    if bureau_report and bureau_report.tradeline_features:
        row["Bureau Segment"] = bureau_report.tradeline_features.customer_segment
    else:
        row["Bureau Segment"] = None

    # ── Max DPD & Product ─────────────────────────────────────────────────────
    # From bureau executive_inputs (portfolio-level max DPD)
    if bureau_report and bureau_report.executive_inputs:
        ei = bureau_report.executive_inputs
        max_dpd = ei.max_dpd
        loan_type = ei.max_dpd_loan_type
        months_ago = ei.max_dpd_months_ago
        if max_dpd is not None:
            parts = [f"{max_dpd}d DPD"]
            if loan_type:
                parts.append(loan_type)
            if months_ago is not None:
                parts.append(f"{months_ago}M ago")
            row["Max DPD & Product"] = " / ".join(parts)
        else:
            row["Max DPD & Product"] = None
    else:
        row["Max DPD & Product"] = None

    # ── CC Util ───────────────────────────────────────────────────────────────
    if bureau_report and bureau_report.tradeline_features:
        util = bureau_report.tradeline_features.cc_balance_utilization_pct
        row["CC Util"] = round(util, 2) if util is not None else None
    else:
        row["CC Util"] = None

    # ── Enquiries ─────────────────────────────────────────────────────────────
    if bureau_report and bureau_report.tradeline_features:
        row["Enquiries"] = bureau_report.tradeline_features.unsecured_enquiries_12m
    else:
        row["Enquiries"] = None

    # ── Payments Missed in l 18M ──────────────────────────────────────────────
    if bureau_report and bureau_report.tradeline_features:
        missed = bureau_report.tradeline_features.pct_missed_payments_18m
        row["Payments Missed in l 18M"] = round(missed, 2) if missed is not None else None
    else:
        row["Payments Missed in l 18M"] = None

    # ── FOIR (Bureau — from tradeline_features) ───────────────────────────────
    # Uses pre-computed bureau FOIR: aff_emi / affluence_amt × 100
    if bureau_report and bureau_report.tradeline_features:
        _tf = bureau_report.tradeline_features
        _foir_parts = []
        if _tf.foir is not None:
            _foir_parts.append(f"{_tf.foir:.1f}%")
        if _tf.foir_unsec is not None:
            _foir_parts.append(f"Unsec: {_tf.foir_unsec:.1f}%")
        row["Foir"] = " / ".join(_foir_parts) if _foir_parts else None
    else:
        row["Foir"] = None

    # ── Exposure Commentary ───────────────────────────────────────────────────
    row["Exposure Commentary"] = exposure_summary or None

    # ── TU Score (TransUnion CIBIL score) ─────────────────────────────────────
    if bureau_report and bureau_report.executive_inputs:
        row["TU Score"] = getattr(bureau_report.executive_inputs, "tu_score", None)
    else:
        row["TU Score"] = None

    # ── Bureau Income (deterministic affluence calc) + Stamp Loan ────────────
    _bi = getattr(bureau_report, "bureau_income", None) if bureau_report else None
    if _bi and _bi.get("bureau_income"):
        row["Bureau Income"] = round(_bi["bureau_income"], 2)
        row["Stamp Loan"] = _bi.get("stamp_loan")
    else:
        row["Bureau Income"] = None
        row["Stamp Loan"] = None

    # ── Sustained EMI (deterministic rolling-window EMI calc) ─────────────────
    _se = getattr(bureau_report, "sustained_emi", None) if bureau_report else None
    row["Sustained EMI"] = (round(_se["sustained_emi"], 2)
                            if _se and _se.get("sustained_emi") is not None else None)

    # ── Bureau Obligation (deterministic EMI-obligation calc) ─────────────────
    _ob = getattr(bureau_report, "obligation", None) if bureau_report else None
    for _col, _key in (("Aff EMI", "aff_emi"), ("EMI Unsec", "emi_unsec"),
                       ("Aff EMI Topup", "aff_emi_topup"),
                       ("EMI Unsec Topup", "emi_unsec_topup"),
                       ("Current EMI", "current_emi")):
        row[_col] = (round(_ob[_key], 2)
                     if _ob and _ob.get(_key) is not None else None)

    # ── Concerns ─────────────────────────────────────────────────────────────
    # High/moderate risk key findings from bureau report
    if bureau_report and bureau_report.key_findings:
        concern_findings = [
            f.finding
            for f in bureau_report.key_findings
            if f.severity in ("high_risk", "moderate_risk")
        ]
        row["Concerns"] = " | ".join(concern_findings) if concern_findings else None
    else:
        row["Concerns"] = None

    # ── Intelligent Report (HTML link) ───────────────────────────────────────
    html_path = report_path.replace(".pdf", ".html") if report_path else None
    row["Intelligent Report"] = html_path

    return row


# ---------------------------------------------------------------------------
# Single-customer Excel writer
# ---------------------------------------------------------------------------

def export_row_to_excel(row: Dict[str, Any], output_path: str) -> str:
    """
    Write a single customer row to an Excel file.

    The file is always created fresh (one row per customer file).
    Use merge_excel_reports() afterwards to combine into one master file.

    Args:
        row:         Dict from build_excel_row()
        output_path: Destination .xlsx path

    Returns:
        Absolute path to the written file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row], columns=TEMPLATE_COLUMNS)
    df.to_excel(output_path, index=False)
    logger.info("Excel row written → %s", output_path)
    return os.path.abspath(output_path)


# ---------------------------------------------------------------------------
# Batch merge
# ---------------------------------------------------------------------------

def merge_excel_reports(
    excel_dir: str,
    output_path: str,
    pattern: str = "*.xlsx",
) -> str:
    """
    Merge all per-customer Excel files in excel_dir into one master file.

    Args:
        excel_dir:   Directory containing per-customer .xlsx files
        output_path: Destination for the merged file
        pattern:     Glob pattern for source files (default: *.xlsx)

    Returns:
        Absolute path to the merged file
    """
    source_files = sorted(Path(excel_dir).glob(pattern))
    if not source_files:
        raise FileNotFoundError(f"No Excel files matching '{pattern}' in {excel_dir}")

    frames = [pd.read_excel(f) for f in source_files]
    merged = pd.concat(frames, ignore_index=True)

    # Enforce template column order (add missing cols as empty, drop extras)
    for col in TEMPLATE_COLUMNS:
        if col not in merged.columns:
            merged[col] = None
    merged = merged[TEMPLATE_COLUMNS]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    merged.to_excel(output_path, index=False)
    logger.info(
        "Merged %d customer rows → %s", len(merged), output_path
    )
    return os.path.abspath(output_path)
