"""Bureau Analyser report renderer - renders BureauReport into a rich PDF/HTML.

Reuses ReportPDF base class and rendering helpers from the bureau renderer.
NO LLM calls - NO data manipulation - just rendering.

The bureau_report may be None when bureau data is unavailable.
"""

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from fpdf import FPDF

import numpy as np
import config.thresholds as T

from schemas.bureau_report import BureauReport
from schemas.loan_type import get_loan_type_display_name
from .pdf_renderer import ReportPDF, _sanitize_text
from .bureau_pdf_renderer import (
    _render_key_finding, _render_group_header, _render_feature_pair,
    _compute_html_chart_data,
)
from ..reports.key_findings import findings_to_dicts
from utils.helpers import mask_customer_id, format_inr, format_inr_units, strip_segment_prefix


class CombinedReportPDF(ReportPDF):
    """Custom PDF class for the Bureau Analyser report — overrides header only."""

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "Bureau Analyser Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)


def _render_absence_note(pdf: FPDF, source_name: str) -> None:
    """Render a styled note indicating a data source is unavailable."""
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(180, 60, 60)
    pdf.cell(
        0, 8,
        f"  {source_name} data is not available for this customer.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)


def _build_combined_pdf(
    bureau_report: Optional[BureauReport],
) -> FPDF:
    """Build a single PDF document from the bureau report."""
    pdf = CombinedReportPDF()
    pdf.add_page()

    # =====================================================================
    # META / REPORT INFORMATION
    # =====================================================================
    pdf.section_title("Report Information")
    if bureau_report:
        pdf.key_value("Customer ID", mask_customer_id(bureau_report.meta.customer_id))
        if bureau_report.meta.generated_at:
            pdf.key_value("Generated", bureau_report.meta.generated_at[:10])
        pdf.key_value("Tradelines", str(bureau_report.executive_inputs.total_tradelines))
    pdf.ln(5)

    # =====================================================================
    # BUREAU REPORT
    # =====================================================================

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, "  Bureau Tradeline Analysis", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    if bureau_report:
        ei = bureau_report.executive_inputs

        # Portfolio Summary
        pdf.section_title("Portfolio Summary")
        pdf.key_value("Live Tradelines", str(ei.live_tradelines))
        pdf.key_value("Total Sanction Amount", f"INR {format_inr(ei.total_sanctioned)}")
        pdf.key_value("Total Outstanding", f"INR {format_inr(ei.total_outstanding)}")
        pdf.key_value("Unsecured Sanction Amount", f"INR {format_inr(ei.unsecured_sanctioned)}")
        # Unsecured outstanding %
        if ei.total_outstanding > 0:
            unsec_os_pct = ei.unsecured_outstanding / ei.total_outstanding * 100
            pdf.key_value("Unsecured Outstanding", f"{unsec_os_pct:.0f}% of total outstanding")
        else:
            pdf.key_value("Unsecured Outstanding", "N/A")
        # Max DPD with timing
        dpd_str = str(ei.max_dpd) if ei.max_dpd is not None else "N/A"
        if ei.max_dpd is not None:
            details = []
            if ei.max_dpd_months_ago is not None:
                details.append(f"{ei.max_dpd_months_ago} months ago")
            if ei.max_dpd_loan_type:
                details.append(ei.max_dpd_loan_type)
            if details:
                dpd_str += f" ({', '.join(details)})"
        pdf.key_value("Max DPD", dpd_str)

        # Largest Single Loan
        if ei.max_single_sanction_amount > 0:
            max_loan_str = f"INR {format_inr(ei.max_single_sanction_amount)}"
            if ei.max_single_sanction_loan_type:
                max_loan_str += f" ({ei.max_single_sanction_loan_type})"
            pdf.key_value("Largest Single Loan", max_loan_str)

        # Joint Loans
        if ei.total_joint_count > 0:
            joint_str = f"{ei.total_joint_count} tradeline(s) — {', '.join(ei.joint_product_types)}"
            pdf.key_value("Joint Loans", joint_str)

        # Kotak (On-Us) sub-section
        if ei.on_us_total_tradelines > 0:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 6, "Kotak Relationship (On-Us)", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.key_value("On-Us Tradelines", f"{ei.on_us_total_tradelines} ({ei.on_us_live_tradelines} live)")
            pdf.key_value("Products", ", ".join(ei.on_us_product_types))
            pdf.key_value("Sanctioned", f"INR {format_inr(ei.on_us_total_sanctioned)}")
            pdf.key_value("Outstanding", f"INR {format_inr(ei.on_us_total_outstanding)}")
            if ei.on_us_max_dpd is not None and ei.on_us_max_dpd > 0:
                pdf.key_value("On-Us Max DPD", str(ei.on_us_max_dpd))

        pdf.ln(5)

        # Defaulted / Delinquent Loan Types table
        if ei.defaulted_loan_summaries:
            pdf.section_title("Defaulted / Delinquent Loan Types")
            d_headers = ["Loan Type", "Sanctioned", "Outstanding", "Max DPD", "Kotak"]
            d_widths = [40, 40, 40, 25, 20]
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(220, 220, 220)
            for header, width in zip(d_headers, d_widths):
                pdf.cell(width, 7, header, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 7)
            for d in ei.defaulted_loan_summaries:
                vals = [
                    d["type"],
                    format_inr(d["sanction"]),
                    format_inr(d["outstanding"]),
                    str(d["dpd"]) if d["dpd"] is not None else "-",
                    "Yes" if d["on_us"] else "No",
                ]
                for val, width in zip(vals, d_widths):
                    pdf.cell(width, 6, val, border=1, align="C")
                pdf.ln()
            pdf.ln(3)

        # Bureau Narrative
        if bureau_report.narrative:
            pdf.section_title("Bureau Executive Summary")
            pdf.section_text(bureau_report.narrative)
            pdf.ln(3)

        # Key Findings
        if bureau_report.key_findings:
            pdf.add_page()
            pdf.section_title("Key Findings & Inferences")
            pdf.ln(2)
            for finding in bureau_report.key_findings:
                _render_key_finding(pdf, finding)

        # Product-wise Table
        pdf.add_page()
        pdf.section_title("Product-wise Breakdown")
        headers = [
            "Type", "Sec", "Count", "Live", "Closed",
            "Sanctioned", "Outstanding", "Max DPD", "Util%", "On-Us"
        ]
        widths = [30, 12, 16, 14, 16, 30, 30, 18, 14, 16]
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(220, 220, 220)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, header, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for loan_type, vec in bureau_report.feature_vectors.items():
            secured = "Y" if vec.secured else "N"
            util = f"{vec.utilization_ratio * 100:.0f}" if vec.utilization_ratio is not None else "-"
            max_dpd = str(vec.max_dpd) if vec.max_dpd is not None else "-"
            values = [
                get_loan_type_display_name(loan_type)[:14],
                secured,
                str(vec.loan_count),
                str(vec.live_count),
                str(vec.closed_count),
                format_inr(vec.total_sanctioned_amount),
                format_inr(vec.total_outstanding_amount),
                max_dpd, util,
                str(vec.on_us_count),
            ]
            for val, width in zip(values, widths):
                pdf.cell(width, 6, str(val)[:14], border=1, align="C")
            pdf.ln()

        # Totals row
        pdf.set_font("Helvetica", "B", 7)
        totals = [
            "TOTAL", "",
            str(ei.total_tradelines),
            str(ei.live_tradelines),
            str(ei.closed_tradelines),
            format_inr(ei.total_sanctioned),
            format_inr(ei.total_outstanding),
            str(ei.max_dpd) if ei.max_dpd is not None else "-",
            "", ""
        ]
        for val, width in zip(totals, widths):
            pdf.cell(width, 6, val, border=1, align="C")
        pdf.ln()

        # Behavioral & Risk Features
        if bureau_report.tradeline_features is not None:
            pdf.add_page()
            pdf.section_title("Behavioral & Risk Features")
            tf = bureau_report.tradeline_features

            _render_group_header(pdf, "Loan Activity")
            _render_feature_pair(pdf, "Months Since Last PL Trade Opened", tf.months_since_last_trade_pl)
            _render_feature_pair(pdf, "Months Since Last Unsecured Trade Opened", tf.months_since_last_trade_uns)
            _render_feature_pair(pdf, "New PL Trades in Last 6 Months", tf.new_trades_6m_pl)
            pdf.ln(3)

            _render_group_header(pdf, "DPD & Delinquency")
            _render_feature_pair(pdf, "Max DPD Last 6M (CC)", tf.max_dpd_6m_cc)
            _render_feature_pair(pdf, "Max DPD Last 6M (PL)", tf.max_dpd_6m_pl)
            _render_feature_pair(pdf, "Max DPD Last 9M (CC)", tf.max_dpd_9m_cc)
            _render_feature_pair(pdf, "Months Since Last 0+ DPD (Unsecured)", tf.months_since_last_0p_uns)
            _render_feature_pair(pdf, "Months Since Last 0+ DPD (PL)", tf.months_since_last_0p_pl)
            pdf.ln(3)

            _render_group_header(pdf, "Payment Behavior")
            _render_feature_pair(pdf, "% Trades with 0+ DPD in 24M (All)", tf.pct_0plus_24m_all)
            _render_feature_pair(pdf, "% Trades with 0+ DPD in 24M (PL)", tf.pct_0plus_24m_pl)
            _render_feature_pair(pdf, "% Missed Payments Last 18M", tf.pct_missed_payments_18m)
            _render_feature_pair(pdf, "% Trades with 0+ DPD in 12M (All)", tf.pct_trades_0plus_12m)
            _render_feature_pair(pdf, "Ratio Good Closed Loans (PL) %",
                                tf.ratio_good_closed_pl * 100 if tf.ratio_good_closed_pl is not None else None)
            pdf.ln(3)

            _render_group_header(pdf, "Utilization")
            _render_feature_pair(pdf, "CC Balance Utilization %", tf.cc_balance_utilization_pct)
            _render_feature_pair(pdf, "PL Outstanding %", tf.pl_balance_remaining_pct)
            pdf.ln(3)

            _render_group_header(pdf, "Enquiry Behavior")
            _render_feature_pair(pdf, "Unsecured Enquiries Last 12M", tf.unsecured_enquiries_12m)
            _render_feature_pair(pdf, "Trade-to-Enquiry Ratio (Unsec 24M)", tf.trade_to_enquiry_ratio_uns_24m)
            pdf.ln(3)

            _render_group_header(pdf, "Loan Acquisition Velocity")
            _render_feature_pair(pdf, "Avg Interpurchase Time 12M (PL/BL)", tf.interpurchase_time_12m_plbl)
            _render_feature_pair(pdf, "Avg Interpurchase Time 6M (PL/BL)", tf.interpurchase_time_6m_plbl)
            _render_feature_pair(pdf, "Avg Interpurchase Time 24M (All)", tf.interpurchase_time_24m_all)
            _render_feature_pair(pdf, "Avg Interpurchase Time 9M (HL/LAP)", tf.interpurchase_time_9m_hl_lap)
            _render_feature_pair(pdf, "Avg Interpurchase Time 24M (HL/LAP)", tf.interpurchase_time_24m_hl_lap)
            _render_feature_pair(pdf, "Avg Interpurchase Time 24M (TWL)", tf.interpurchase_time_24m_twl)
            _render_feature_pair(pdf, "Avg Interpurchase Time 12M (Consumer Loan)", tf.interpurchase_time_12m_cl)
    else:
        _render_absence_note(pdf, "Bureau tradeline")

    return pdf


def render_combined_report(
    bureau_report: Optional[BureauReport],
    output_path: Optional[str] = None,
    theme: str = "v2",
    save_pdf: bool = True,
) -> str:
    """Render the Bureau Analyser PDF + HTML from the bureau report.

    Args:
        bureau_report: Fully populated BureauReport, or None if unavailable.
        output_path: Desired output file path (.pdf).
                      Defaults to reports/bureau_analyser_{customer_id}_report.pdf.
        save_pdf: When False, skip PDF generation — only save HTML.

    Returns:
        Path where the output was saved (PDF path if save_pdf, else HTML path).
    """
    if output_path is None:
        cid = bureau_report.meta.customer_id if bureau_report else "unknown"
        output_path = f"reports/bureau_analyser_{cid}_report.pdf"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Build and save PDF (optional)
    if save_pdf:
        pdf = _build_combined_pdf(bureau_report)
        pdf.output(str(output_file))

    # Save HTML version alongside the PDF
    html_path = str(output_file).replace(".pdf", ".html")
    html_content = render_combined_report_html(bureau_report, theme=theme)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Also copy HTML to dedicated bureau_analyser_html_version folder
    html_version_dir = output_file.parent / "bureau_analyser_html_version"
    html_version_dir.mkdir(parents=True, exist_ok=True)
    html_version_path = html_version_dir / Path(html_path).name
    with open(str(html_version_path), "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(output_file) if save_pdf else html_path


_ADVERSE_FLAGS = {"WRF", "SET", "SMA", "SUB", "DBT", "LSS", "WOF"}
_BETTING_CATS = {"Digital_Betting_Gaming", "Betting_Gaming", "Betting", "Gaming"}


def compute_checklist(
    bureau_report: Optional[BureauReport],
) -> list:
    """Compute yes/no bureau checklist items from existing report data.

    Returns a list of dicts: {label, checked, severity, detail}.
    """
    bureau_items: list = []

    # ── BUREAU CHECKLIST ──────────────────────────────────────────

    # B1. Max DPD occurred
    has_dpd = False
    dpd_detail = None
    if bureau_report:
        ei = bureau_report.executive_inputs
        if ei.max_dpd is not None and ei.max_dpd > 0:
            has_dpd = True
            parts = [f"{ei.max_dpd} days"]
            if ei.max_dpd_loan_type:
                parts.append(ei.max_dpd_loan_type)
            if ei.max_dpd_months_ago is not None:
                parts.append(f"{ei.max_dpd_months_ago}M ago")
            dpd_detail = " — ".join(parts)
    bureau_items.append({
        "label": "MAX DPD occurred",
        "checked": has_dpd,
        "severity": "high" if has_dpd else "positive",
        "detail": dpd_detail,
    })

    # B2. Adverse events (write-off / settlement)
    adverse_flags = []
    if bureau_report:
        for vec in bureau_report.feature_vectors.values():
            for f in (vec.forced_event_flags or []):
                if f in _ADVERSE_FLAGS:
                    adverse_flags.append(f)
    has_adverse = bool(adverse_flags)
    bureau_items.append({
        "label": "Adverse events (write-off / settlement)",
        "checked": has_adverse,
        "severity": "high" if has_adverse else "positive",
        "detail": f"Flags: {', '.join(sorted(set(adverse_flags)))}" if has_adverse else None,
    })

    # B3. High FOIR (>50%)
    foir_val = None
    if bureau_report and bureau_report.tradeline_features:
        foir_val = bureau_report.tradeline_features.foir
    has_high_foir = foir_val is not None and foir_val > 50
    bureau_items.append({
        "label": "High FOIR (> 50%)",
        "checked": has_high_foir,
        "severity": "high" if (foir_val and foir_val > 65) else ("medium" if has_high_foir else "neutral"),
        "detail": f"Bureau FOIR: {foir_val:.1f}%" if foir_val is not None else None,
    })

    # B4. CC utilization elevated (>=30%)
    cc_util = None
    if bureau_report:
        from schemas.loan_type import LoanType
        cc_vec = bureau_report.feature_vectors.get(LoanType.CC)
        if cc_vec and cc_vec.utilization_ratio is not None:
            cc_util = cc_vec.utilization_ratio * 100  # convert fraction to percentage
    bureau_items.append({
        "label": "CC utilization elevated (\u226530%)",
        "checked": cc_util is not None and cc_util >= 30,
        "severity": "high" if (cc_util is not None and cc_util >= 75) else (
            "medium" if (cc_util is not None and cc_util >= 30) else "positive"
        ),
        "detail": f"CC utilization: {cc_util:.1f}%" if cc_util is not None else None,
    })

    # B5. Kotak loan presence
    kotak_total = 0
    kotak_type_dist: list = []
    if bureau_report:
        from schemas.loan_type import LoanType
        for lt, vec in bureau_report.feature_vectors.items():
            if vec.on_us_count > 0:
                kotak_total += vec.on_us_count
                kotak_type_dist.append(f"{lt.value}({vec.on_us_count})")
    kotak_detail = None
    if kotak_total > 0:
        kotak_detail = f"{kotak_total} Kotak loan(s): {', '.join(kotak_type_dist)}"
    bureau_items.append({
        "label": "Customer has Kotak loan",
        "checked": kotak_total > 0,
        "severity": "neutral" if kotak_total > 0 else "neutral",
        "detail": kotak_detail,
    })

    # B6. Kotak loan default (live loans only) — query raw bureau data
    kotak_defaults: list = []
    try:
        if bureau_report:
            from pipeline.extractors.bureau_feature_extractor import _load_bureau_data
            from schemas.loan_type import ON_US_SECTORS, normalize_loan_type
            cust_id = bureau_report.meta.customer_id
            if cust_id is not None:
                _CLOSED = {"closed", "written off", "written-off", "settled", "npa", "loss", "doubtful", "write-off"}
                raw_rows = _load_bureau_data()
                cust_str = str(cust_id)
                for row in raw_rows:
                    if str(row.get("crn", "")).strip() != cust_str:
                        continue
                    sector = str(row.get("sector", "")).strip().upper()
                    if sector not in ON_US_SECTORS:
                        continue
                    status = str(row.get("loan_status", "")).strip().lower()
                    if status in _CLOSED:
                        continue
                    # Live Kotak tradeline — check for default
                    raw_dpd = 0
                    try:
                        raw_dpd = int(float(row.get("max_dpd", 0) or 0))
                    except (ValueError, TypeError):
                        pass
                    dpd_str = str(row.get("dpd_string", "")).upper()
                    has_adverse_flag = any(f in dpd_str for f in _ADVERSE_FLAGS)
                    if raw_dpd > 0 or has_adverse_flag:
                        lt_raw = str(row.get("loan_type_new", "")).strip()
                        lt_canonical = normalize_loan_type(lt_raw)
                        parts = [lt_canonical.value]
                        if raw_dpd > 0:
                            parts.append(f"DPD {raw_dpd}")
                        if has_adverse_flag:
                            flags = [f for f in _ADVERSE_FLAGS if f in dpd_str]
                            parts.append(f"Flags: {','.join(flags)}")
                        kotak_defaults.append(" — ".join(parts))
    except Exception:
        pass  # fail-soft
    has_kotak_default = bool(kotak_defaults)
    bureau_items.append({
        "label": "Kotak loan default (live)",
        "checked": has_kotak_default,
        "severity": "high" if has_kotak_default else ("positive" if kotak_total > 0 else "neutral"),
        "detail": "; ".join(kotak_defaults[:5]) if has_kotak_default else None,
    })

    # B7. Live Home Loan detected
    hl_live = False
    hl_detail = None
    if bureau_report:
        from schemas.loan_type import LoanType
        hl_vec = bureau_report.feature_vectors.get(LoanType.HL)
        if hl_vec and hl_vec.live_count > 0:
            hl_live = True
            sanc = hl_vec.total_sanctioned_amount
            on_us = hl_vec.on_us_count
            off_us = hl_vec.off_us_count
            hl_detail = f"Sanctioned: ₹{sanc:,.0f} | On-Us: {on_us}, Off-Us: {off_us}"
    bureau_items.append({
        "label": "Live Home Loan detected",
        "checked": hl_live,
        "severity": "neutral" if hl_live else "neutral",
        "detail": hl_detail,
    })

    # B8. Bureau thickness
    bu_grp_val = None
    if bureau_report and bureau_report.tradeline_features:
        bu_grp_val = bureau_report.tradeline_features.bu_grp
    bu_thick = bu_grp_val is not None and "thick" in bu_grp_val.lower()
    bureau_items.append({
        "label": "Bureau thick",
        "checked": bu_thick,
        "severity": "positive" if bu_thick else "medium",
        "detail": None if bu_thick else (bu_grp_val if bu_grp_val else "Data unavailable"),
    })

    # B9. Banking thickness
    bank_grp_val = None
    if bureau_report and bureau_report.tradeline_features:
        bank_grp_val = bureau_report.tradeline_features.bank_grp
    bank_thick = bank_grp_val is not None and "thick" in bank_grp_val.lower()
    bureau_items.append({
        "label": "Banking thick",
        "checked": bank_thick,
        "severity": "positive" if bank_thick else "medium",
        "detail": None if bank_thick else (bank_grp_val if bank_grp_val else "Data unavailable"),
    })

    # B10. Exposure trend elevated
    exposure_elevated = False
    exposure_detail = None
    exposure_rag = "neutral"
    if bureau_report:
        from tools.scorecard import _exposure_signals
        signals = _exposure_signals(getattr(bureau_report, "monthly_exposure", None))
        if signals:
            chip = signals[0]
            exposure_rag = chip.get("rag", "neutral")
            exposure_elevated = exposure_rag in ("amber", "red")
            exposure_detail = f"{chip.get('label', 'Exposure')}: {chip.get('value', '')}"
    bureau_items.append({
        "label": "Exposure elevated",
        "checked": exposure_elevated,
        "severity": "high" if exposure_rag == "red" else (
            "medium" if exposure_elevated else ("positive" if exposure_rag == "green" else "neutral")
        ),
        "detail": exposure_detail,
    })

    return bureau_items


# ---------------------------------------------------------------------------
# Persona classification — raw loan type sets
# ---------------------------------------------------------------------------
_MF_BL = {"Microfinance - Business Loan"}
_MF_HL = {"Microfinance - Housing Loan"}
_MF_PL = {"Microfinance - Personal Loan"}
_TRACTOR = {"Tractor Loan"}
_CE = {"Construction Equipment Loan"}
_CV = {"Commercial Vehicle Loan"}
_FLEET_CARD = {"Fleet Card"}
_GECL = {"GECL Loan Secured", "GECL Loan Unsecured"}
_EDUCATION = {"Education Loan", "P2P Education Loan"}
_LAS = {"Loan_against_securities", "Loan Against Shares/Securities"}
_NON_FUNDED = {
    "Non-Funded Credit Facility",
    "Business Non-Funded Credit Facility - General",
    "Business Non-Funded Credit Facility - Priority Sector-Others",
    "Business Non-Funded Credit Facility - Priority Sector - Agriculture",
    "Business Non-Funded Credit Facility - Priority Sector - Small Business",
}
_LOAN_TO_PROF = {"Loan to Professional"}
_CORP_CC = {"Corporate Credit Card"}
_SHORT_TERM_PL = {"Short Term Personal Loan"}
_TEMP_OD = {"Temporary Overdraft"}
_OD = {"Overdraft", "Prime Minister Jaan Dhan Yojana - Overdraft"}
_BL_ALL = {
    "Business Loan - General", "Business Loan - Secured", "Business Loan - Unsecured",
    "Business Loan - Priority Sector - Agriculture", "Business Loan - Priority Sector - Others",
    "Business Loan - Priority Sector - Small Business", "Business Loan Against Bank Deposits",
    "Mudra Loans - Shishu / Kishor / Tarun",
}
_BL_AGRI = {
    "Business Loan - Priority Sector - Agriculture",
    "Business Non-Funded Credit Facility - Priority Sector - Agriculture",
}
_HL_ALL = {"Housing Loan", "Home Loan", "Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS"}
_CC_ALL = {"Credit Card", "Secured Credit Card"}
_PL_PLAIN = {"Personal Loan"}
_AL_ALL = {"Auto Loan (Personal)", "Auto Loan", "Used Car Loan"}
_GL_ALL = {"Gold Loan", "Priority Sector - Gold Loan"}
_LAD_ALL = {"Loan Against Bank Deposits"}
_GENERIC_SINGLE = {"Personal Loan", "Credit Card", "Consumer Loan", "Short Term Personal Loan", "Secured Credit Card"}


def _count_raw(raw_counts: dict, type_set: set) -> int:
    """Sum counts for all raw types matching a set."""
    return sum(raw_counts.get(t, 0) for t in type_set)


def _sum_sanctioned(raw_sanctioned: dict, type_set: set) -> float:
    """Sum sanctioned amounts for all raw types matching a set."""
    return sum(raw_sanctioned.get(t, 0.0) for t in type_set)


def _fmt_inr_short(amount: float) -> str:
    """Format amount as short INR string (e.g. '15L', '2.5Cr')."""
    if amount >= 1_00_00_000:
        return f"{amount / 1_00_00_000:.1f}Cr"
    elif amount >= 1_00_000:
        return f"{amount / 1_00_000:.0f}L"
    elif amount >= 1_000:
        return f"{amount / 1_000:.0f}K"
    return f"{amount:.0f}"


def compute_probable_persona(bureau_report: Optional[BureauReport]) -> dict:
    """Compute probable customer persona from bureau tradeline data.

    Evaluates all persona rules in waterfall priority order, collects all
    matches, and returns the top 2-3 by priority. Stress overlays are
    evaluated independently.

    Returns:
        {
            "profiles": [{"label": str, "track": str, "detail": str|None}, ...],
            "stress_flags": [{"label": str, "severity": str, "detail": str|None}, ...],
            "summary": "Probable profile of customer is X, Y"
        }
    """
    empty = {"profiles": [], "stress_flags": [], "summary": ""}

    if bureau_report is None or bureau_report.raw_loan_profile is None:
        empty["profiles"] = [{"label": "Insufficient Data", "track": "Thin File", "detail": "No bureau data available"}]
        empty["summary"] = "Probable profile of customer is Insufficient Data"
        return empty

    raw = bureau_report.raw_loan_profile
    rc = raw.get("raw_counts", {})
    rs = raw.get("raw_sanctioned", {})
    rl = raw.get("raw_live_counts", {})
    total_tl = raw.get("total_tradelines", 0)

    # Edge: no tradelines
    if total_tl == 0:
        return {
            "profiles": [{"label": "New to Credit", "track": "NTC", "detail": "Zero bureau tradelines"}],
            "stress_flags": [],
            "summary": "Probable profile of customer is New to Credit",
        }

    # Edge: single generic product
    if total_tl == 1:
        single_type = next(iter(rc), "")
        if single_type in _GENERIC_SINGLE:
            return {
                "profiles": [{"label": "Insufficient Data", "track": "Thin File", "detail": f"Single {single_type}"}],
                "stress_flags": [],
                "summary": "Probable profile of customer is Insufficient Data (thin file)",
            }

    matches = []  # list of {"label", "track", "priority", "detail"}

    # --- MF Track (priority=10) ---
    mf_bl = _count_raw(rc, _MF_BL)
    mf_hl = _count_raw(rc, _MF_HL)
    mf_pl = _count_raw(rc, _MF_PL)
    if mf_bl > 0:
        matches.append({"label": "MF Entrepreneur", "track": "Microfinance", "priority": 10,
                         "detail": f"{mf_bl} MF Business Loan(s)"})
    elif mf_hl > 0:
        matches.append({"label": "MF Asset Builder", "track": "Microfinance", "priority": 11,
                         "detail": f"{mf_hl} MF Housing Loan(s)"})
    elif mf_pl > 0:
        matches.append({"label": "MF Consumer", "track": "Microfinance", "priority": 12,
                         "detail": f"{mf_pl} MF Personal Loan(s)"})

    # --- Business Track (priority=20) ---
    bl_count = _count_raw(rc, _BL_ALL) + _count_raw(rc, _GECL)
    bl_sanction = _sum_sanctioned(rs, _BL_ALL) + _sum_sanctioned(rs, _GECL)
    nf_count = _count_raw(rc, _NON_FUNDED)
    od_count = _count_raw(rc, _OD)
    od_sanction = _sum_sanctioned(rs, _OD)
    bl_agri_count = _count_raw(rc, _BL_AGRI)

    if bl_count >= T.PERSONA_BL_LARGE_MIN_COUNT and bl_count > 0 and (bl_sanction / bl_count) > T.PERSONA_BL_LARGE_AVG_SANCTION:
        detail = f"{bl_count} BL, avg {_fmt_inr_short(bl_sanction / bl_count)}"
        if nf_count > 0:
            detail += " + Non-Funded CF (trade/export)"
        matches.append({"label": "Large Business", "track": "Business", "priority": 20, "detail": detail})
    elif (bl_count > 0 and od_sanction > T.PERSONA_OD_SALARY_MAX) or nf_count > 0:
        total_biz = bl_sanction + od_sanction
        if T.PERSONA_BL_SME_MIN_SANCTION <= total_biz <= T.PERSONA_BL_LARGE_AVG_SANCTION * 2:
            matches.append({"label": "SME / Growing Business", "track": "Business", "priority": 21,
                             "detail": f"{bl_count} BL + OD {_fmt_inr_short(od_sanction)}, total {_fmt_inr_short(total_biz)}"})
    if 1 <= bl_count <= 2 and bl_sanction <= T.PERSONA_BL_LARGE_AVG_SANCTION:
        sub = "micro/shopkeeper" if bl_count > 0 and (bl_sanction / bl_count) < T.PERSONA_BL_MICRO_MAX else None
        detail = f"{bl_count} BL, {_fmt_inr_short(bl_sanction)}"
        if sub:
            detail += f" ({sub})"
        matches.append({"label": "Small Business Owner", "track": "Business", "priority": 22, "detail": detail})

    if bl_agri_count > 0:
        tractor_count = _count_raw(rc, _TRACTOR)
        label = "Agri Entrepreneur" if tractor_count > 0 else "Agri Priority Business"
        matches.append({"label": label, "track": "Business", "priority": 23,
                         "detail": f"{bl_agri_count} Agri BL" + (f" + {tractor_count} Tractor" if tractor_count > 0 else "")})

    # --- Transport Track (priority=30) ---
    cv_count = _count_raw(rc, _CV)
    fleet_count = _count_raw(rc, _FLEET_CARD)
    ce_count = _count_raw(rc, _CE)
    al_count = _count_raw(rc, _AL_ALL)
    al_sanction = _sum_sanctioned(rs, _AL_ALL)

    if cv_count >= T.PERSONA_CV_FLEET_MIN_COUNT or (cv_count >= 2 and fleet_count > 0):
        matches.append({"label": "Fleet Owner", "track": "Transport", "priority": 30,
                         "detail": f"{cv_count} CV" + (f" + Fleet Card" if fleet_count > 0 else "")})
    elif cv_count >= 1:
        matches.append({"label": "Transport Operator", "track": "Transport", "priority": 31,
                         "detail": f"{cv_count} CV (LCV/HCV)"})

    if al_count >= T.PERSONA_AL_CLUSTER_MIN and al_count > 0 and (al_sanction / al_count) <= T.PERSONA_PL_ENTRY_MAX:
        matches.append({"label": "Transport Operator (Cab/Taxi)", "track": "Transport", "priority": 32,
                         "detail": f"{al_count} AL cluster, avg {_fmt_inr_short(al_sanction / al_count)}"})

    if ce_count >= 1:
        label = "Established Contractor" if ce_count >= 2 else "Contractor"
        matches.append({"label": label, "track": "Transport", "priority": 33,
                         "detail": f"{ce_count} CE Loan(s)"})

    # --- Agriculture Track (priority=40) ---
    tractor_count = _count_raw(rc, _TRACTOR)
    if tractor_count > 0 or bl_agri_count > 0:
        if tractor_count > 0 and bl_agri_count > 0:
            label = "Agri Entrepreneur"
            detail = f"{tractor_count} Tractor + {bl_agri_count} Agri BL"
        elif tractor_count > 0:
            label = "Farmer / Agriculture"
            detail = f"{tractor_count} Tractor Loan(s)"
        else:
            label = "Farmer / Agriculture"
            detail = f"{bl_agri_count} Agri BL"
        matches.append({"label": label, "track": "Agriculture", "priority": 40, "detail": detail})

    # --- Salaried Track (priority=50) ---
    hl_count = _count_raw(rc, _HL_ALL)
    hl_sanction = _sum_sanctioned(rs, _HL_ALL)
    cc_count = _count_raw(rc, _CC_ALL)
    pl_count = _count_raw(rc, _PL_PLAIN)
    pl_sanction = _sum_sanctioned(rs, _PL_PLAIN)
    edu_count = _count_raw(rc, _EDUCATION)
    corp_cc = _count_raw(rc, _CORP_CC)

    if hl_count > 0 and hl_sanction > T.PERSONA_HL_MATURE_SANCTION and (cc_count > 0 or al_count > 0):
        detail = f"HL {_fmt_inr_short(hl_sanction)}"
        if hl_sanction > T.PERSONA_HL_METRO_SANCTION:
            detail += " (Metro Senior)"
        matches.append({"label": "Mature Salaried", "track": "Salaried", "priority": 50, "detail": detail})
    elif hl_count > 0 and (cc_count > 0 or pl_count > 0):
        detail = f"HL {_fmt_inr_short(hl_sanction)}"
        if hl_sanction <= T.PERSONA_HL_AFFORDABLE_MAX:
            detail += " (Affordable housing)"
        matches.append({"label": "Established Salaried", "track": "Salaried", "priority": 51, "detail": detail})
    elif pl_count > 0 and pl_sanction <= T.PERSONA_PL_ENTRY_MAX and cc_count > 0:
        detail = f"PL {_fmt_inr_short(pl_sanction)} + CC"
        if edu_count > 0:
            detail += " + Education (Young Professional)"
        matches.append({"label": "Entry Salaried", "track": "Salaried", "priority": 52, "detail": detail})

    if corp_cc > 0:
        las_count = _count_raw(rc, _LAS)
        label = "HNI Executive" if las_count > 0 else "Corporate Professional"
        matches.append({"label": label, "track": "Salaried", "priority": 53,
                         "detail": f"Corporate CC" + (f" + LAS" if las_count > 0 else "")})

    # --- Professional Track (priority=60) ---
    ltp_count = _count_raw(rc, _LOAN_TO_PROF)
    if ltp_count > 0:
        matches.append({"label": "Self-Employed Professional", "track": "Professional", "priority": 60,
                         "detail": f"{ltp_count} Loan to Professional"})

    # --- Asset Track (priority=70) ---
    las_count = _count_raw(rc, _LAS)
    gl_count = _count_raw(rc, _GL_ALL)
    gl_sanction = _sum_sanctioned(rs, _GL_ALL)
    lad_count = _count_raw(rc, _LAD_ALL)

    if las_count > 0:
        detail = f"{las_count} LAS"
        if hl_count > 0 and hl_sanction > T.PERSONA_HL_MATURE_SANCTION:
            detail += " + large HL (Senior Professional)"
        matches.append({"label": "HNI / Investor", "track": "Asset", "priority": 70, "detail": detail})

    # HL alone (no BL, no PL, no CC)
    if hl_count > 0 and bl_count == 0 and pl_count == 0 and cc_count == 0:
        matches.append({"label": "Asset Holder", "track": "Asset", "priority": 71,
                         "detail": f"HL alone {_fmt_inr_short(hl_sanction)}"})

    # Gold alone or LAD alone
    non_gl_lad = total_tl - gl_count - lad_count
    if gl_count > 0 and gl_sanction > T.PERSONA_GOLD_STRESS_MIN and non_gl_lad == 0:
        matches.append({"label": "Asset Stress", "track": "Asset", "priority": 72,
                         "detail": f"Gold Loan alone {_fmt_inr_short(gl_sanction)}"})
    if lad_count > 0 and non_gl_lad == 0:
        matches.append({"label": "Asset Stress", "track": "Asset", "priority": 73,
                         "detail": "LAD alone — pledging deposits"})

    # OD alone checks
    if od_count > 0 and total_tl == od_count:
        if od_sanction <= T.PERSONA_OD_SALARY_MAX:
            matches.append({"label": "Salaried (Salary OD)", "track": "Salaried", "priority": 54,
                             "detail": f"OD alone {_fmt_inr_short(od_sanction)}"})
        else:
            matches.append({"label": "Business / Self-Employed", "track": "Business", "priority": 24,
                             "detail": f"OD alone {_fmt_inr_short(od_sanction)} (>5L)"})

    # --- Stressed Track (priority=80) ---
    spl_count = _count_raw(rc, _SHORT_TERM_PL)
    tod_count = _count_raw(rc, _TEMP_OD)

    if spl_count > 0 and tod_count > 0:
        detail = [f"{spl_count} Short PL", f"{tod_count} Temp OD"]
        combo = " + ".join(detail)
        if gl_count > 0 and gl_sanction > T.PERSONA_GOLD_STRESS_MIN:
            combo += f" + Gold {_fmt_inr_short(gl_sanction)} — possible debt trap"
        matches.append({"label": "Stressed Borrower", "track": "Stressed", "priority": 80,
                         "detail": combo})

    # --- Stress Overlay (independent, always evaluated) ---
    stress_flags = []
    if gl_count > 0 and gl_sanction > T.PERSONA_GOLD_STRESS_MIN:
        if gl_sanction > T.PERSONA_GOLD_HIGH_STRESS:
            stress_flags.append({"label": "High Asset Stress", "severity": "high",
                                  "detail": f"Gold Loan {_fmt_inr_short(gl_sanction)}"})
        elif non_gl_lad < total_tl:  # has other products too
            stress_flags.append({"label": "Asset Stress", "severity": "moderate",
                                  "detail": f"Gold Loan {_fmt_inr_short(gl_sanction)} alongside other products"})
    if spl_count > 0:
        stress_flags.append({"label": "Soft Stress", "severity": "low",
                              "detail": f"{spl_count} Short Term PL"})
    if tod_count > 0:
        stress_flags.append({"label": "Cash Flow Stress", "severity": "moderate",
                              "detail": f"{tod_count} Temporary OD"})

    # --- Select top 2-3 by priority ---
    # Deduplicate by label (keep highest priority)
    seen_labels = set()
    unique_matches = []
    for m in sorted(matches, key=lambda x: x["priority"]):
        if m["label"] not in seen_labels:
            seen_labels.add(m["label"])
            unique_matches.append(m)

    top = unique_matches[:3]

    if not top:
        top = [{"label": "Unclassified", "track": "Unknown", "priority": 99, "detail": f"{total_tl} tradeline(s), no clear profile match"}]

    profiles = [{"label": m["label"], "track": m["track"], "detail": m.get("detail")} for m in top]
    labels = ", ".join(p["label"] for p in profiles)
    summary = f"Probable profile of customer is {labels}"

    return {"profiles": profiles, "stress_flags": stress_flags, "summary": summary}


# ---------------------------------------------------------------------------
# v2 theme helpers — extra pre-computed context for combined_report_v2.html
# ---------------------------------------------------------------------------

# DPD heatmap intensity levels (cell colors live in the template)
#   0 = clean · 1 = 1-29 DPD · 2 = 30-59 · 3 = 60-89 · 4 = 90+ / adverse code
def _dpd_level(dpd: Optional[int], flag: Optional[str]) -> int:
    if flag:
        return 4
    if dpd is None or dpd <= 0:
        return 0
    if dpd < 30:
        return 1
    if dpd < 60:
        return 2
    if dpd < 90:
        return 3
    return 4


def _compute_dpd_grid(customer_id) -> Optional[dict]:
    """Build a months × product DPD grid from raw payhist_1..36 / dt1..36.

    Returns {"months": [...], "rows": [{"product", "cells": [{"v", "level"}]}],
    "has_events": bool} over the trailing 24 reported months, or None if the
    raw data is unavailable. Fail-soft like checklist B6.
    """
    try:
        from pipeline.extractors.bureau_feature_extractor import _load_bureau_data
        from schemas.loan_type import normalize_loan_type, get_loan_type_display_name as _disp

        cust_str = str(customer_id)
        rows = [r for r in _load_bureau_data() if str(r.get("crn", "")).strip() == cust_str]
        if not rows:
            return None

        _CLEAN_CODES = {"STD", "XXX", "ASSET", "0", "000"}
        per: dict = {}     # (product, (year, month)) -> {"dpd": int|None, "flag": str|None}
        latest = None
        for row in rows:
            lt_raw = str(row.get("loan_type_new", "")).strip()
            product = _disp(normalize_loan_type(lt_raw))
            for i in range(1, 37):
                dt_raw = str(row.get(f"dt{i}") or "").strip()
                ph = str(row.get(f"payhist_{i}") or "").strip().upper()
                if not dt_raw or not ph or ph == "NULL":
                    continue
                try:
                    d = datetime.strptime(dt_raw[:10], "%Y-%m-%d")
                except ValueError:
                    continue
                dpd, flag = None, None
                if ph in _CLEAN_CODES:
                    dpd = 0
                elif ph.isdigit():
                    dpd = int(ph)
                elif ph in _ADVERSE_FLAGS:
                    flag = ph
                else:
                    continue
                ym = (d.year, d.month)
                if latest is None or ym > latest:
                    latest = ym
                cur = per.setdefault((product, ym), {"dpd": None, "flag": None})
                if dpd is not None and (cur["dpd"] is None or dpd > cur["dpd"]):
                    cur["dpd"] = dpd
                if flag and not cur["flag"]:
                    cur["flag"] = flag

        if latest is None:
            return None

        # Trailing 24 calendar months ending at the latest reported month
        import calendar
        months = []
        for back in range(23, -1, -1):
            m = (latest[1] - 1 - back) % 12 + 1
            y = latest[0] + (latest[1] - 1 - back) // 12
            months.append((y, m))
        month_labels = [f"{calendar.month_abbr[m]} {y}" for (y, m) in months]

        products = sorted({p for (p, _ym) in per})
        grid_rows = []
        has_events = False
        for product in products:
            cells = []
            for ym in months:
                cell = per.get((product, ym))
                if cell is None:
                    cells.append({"v": None, "level": 0})
                    continue
                level = _dpd_level(cell["dpd"], cell["flag"])
                if level > 0:
                    has_events = True
                cells.append({"v": cell["flag"] or cell["dpd"], "level": level})
            grid_rows.append({"product": product, "cells": cells})

        return {"months": month_labels, "rows": grid_rows, "has_events": has_events}
    except Exception:
        return None  # fail-soft


def _dpd_acct_inr(x) -> Optional[str]:
    if x in (None, "NULL", ""):
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if x >= 1e7:
        return f"₹{x / 1e7:.1f}Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.1f}L"
    if x >= 1e3:
        return f"₹{x / 1e3:.0f}K"
    return f"₹{x:.0f}"


def _compute_dpd_accounts(customer_id) -> Optional[dict]:
    """Per-account DPD swimlanes over the trailing 36 reported months.

    Returns one lane per tradeline (cells = monthly DPD level/state), an
    aggregate portfolio worst-DPD overview row, and clean/event counts so the
    template can surface delinquent accounts first and collapse the clean bulk.
    Fail-soft (→ None), same pattern as `_compute_dpd_grid`.
    """
    try:
        from pipeline.extractors.bureau_feature_extractor import _load_bureau_data
        from schemas.loan_type import normalize_loan_type, get_loan_type_display_name as _disp

        cust_str = str(customer_id)
        raw = [r for r in _load_bureau_data() if str(r.get("crn", "")).strip() == cust_str]
        if not raw:
            return None

        _CLEAN = {"STD", "ASSET", "0", "000"}
        latest = None
        parsed = []
        for row in raw:
            product = _disp(normalize_loan_type(str(row.get("loan_type_new", "")).strip()))
            cells_by_ym: dict = {}
            for i in range(1, 37):
                dt_raw = str(row.get(f"dt{i}") or "").strip()
                ph = str(row.get(f"payhist_{i}") or "").strip().upper()
                if not dt_raw or not ph or ph == "NULL":
                    continue
                try:
                    d = datetime.strptime(dt_raw[:10], "%Y-%m-%d")
                except ValueError:
                    continue
                if ph == "XXX":
                    cell = {"lvl": 0, "v": "·", "state": "gap"}
                elif ph in _CLEAN or (ph.isdigit() and int(ph) == 0):
                    cell = {"lvl": 0, "v": 0, "state": "ok"}
                elif ph.isdigit():
                    cell = {"lvl": _dpd_level(int(ph), None), "v": int(ph), "state": "dpd"}
                elif ph in _ADVERSE_FLAGS:
                    cell = {"lvl": 4, "v": ph, "state": "dpd"}
                else:
                    continue
                ym = (d.year, d.month)
                cells_by_ym[ym] = cell
                if latest is None or ym > latest:
                    latest = ym
            parsed.append({"row": row, "product": product, "cells": cells_by_ym})

        if latest is None:
            return None

        import calendar
        N = 36
        months = []
        for back in range(N - 1, -1, -1):
            m = (latest[1] - 1 - back) % 12 + 1
            y = latest[0] + (latest[1] - 1 - back) // 12
            months.append((y, m))
        month_labels = [f"{calendar.month_abbr[m]} {str(y)[2:]}" for (y, m) in months]

        def _year(s):
            try:
                return datetime.strptime(str(s)[:10], "%Y-%m-%d").year
            except (ValueError, TypeError):
                return None

        accounts = []
        overview = [{"delinquent": 0, "worst": 0} for _ in months]
        for pa in parsed:
            row, cby = pa["row"], pa["cells"]
            cells, worst, has_event, reported = [], 0, False, False
            for idx, ym in enumerate(months):
                c = cby.get(ym)
                if c is None:
                    cells.append({"lvl": 0, "v": None, "state": "none"})
                    continue
                reported = True
                cells.append(c)
                if c["state"] == "dpd" and c["lvl"] > 0:
                    worst = max(worst, c["lvl"])
                    has_event = True
                    overview[idx]["delinquent"] += 1
                    overview[idx]["worst"] = max(overview[idx]["worst"], c["lvl"])
            if not reported:
                continue
            oy = _year(row.get("date_opened"))
            accounts.append({
                "product": pa["product"],
                "opened_year": oy,
                "sanction_disp": _dpd_acct_inr(row.get("sanction_amount")),
                "status": str(row.get("loan_status", "")).strip(),
                "on_us": str(row.get("sector", "")).strip().upper() == "KOTAK BANK",
                "worst_level": worst,
                "has_event": has_event,
                "cells": cells,
            })

        accounts.sort(key=lambda a: (
            0 if a["has_event"] else 1,
            -a["worst_level"],
            -(a["opened_year"] or 0),
        ))
        n_event = sum(1 for a in accounts if a["has_event"])
        return {
            "months": month_labels,
            "n_months": N,
            "default_window": 24,
            "accounts": accounts,
            "overview": overview,
            "n_total": len(accounts),
            "n_event": n_event,
            "n_clean": len(accounts) - n_event,
            "all_clean": n_event == 0,
        }
    except Exception:
        return None  # fail-soft


def _parse_month_str(value: Optional[str]) -> Optional[date]:
    """Parse a '%b %Y' string like 'Dec 2019' into a date (day=1)."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%b %Y").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Behavioral & Risk Features — threshold-aware metric model
# (drives the bullet-bar / radar / table views in combined_report_v2.html)
# Thresholds mirror the per-metric rules previously encoded in the template.
# ---------------------------------------------------------------------------
_BF_GROUPS = [
    "Loan Activity", "DPD & Delinquency", "Payment Behavior",
    "Utilization", "Enquiry", "Acquisition Velocity",
]

# (field, plain_label, group, fmt, direction, params)
#   direction: low | high | band | cleanNone | presentNone | neutral
#   fmt:       f2 | int | pct100
#   params.unit (optional): "%" | " months" | " days" — used in plain-English
#     hints; "%" is also appended to the displayed value.
_BF_SPECS = [
    ("months_since_last_trade_pl",   "Months since last personal loan",         "Loan Activity",        "f2",  "band",        {"lo": 3.17, "hi": 15.99, "axis": 24, "unit": " months"}),
    ("months_since_last_trade_uns",  "Months since last unsecured loan",        "Loan Activity",        "f2",  "low",         {"green_max": 32.18, "axis": 48, "unit": " months"}),
    ("new_trades_6m_pl",             "New personal loans (last 6M)",            "Loan Activity",        "int", "presentNone", {}),
    ("max_dpd_6m_cc",                "Worst card delinquency (6M)",             "DPD & Delinquency",    "int", "low",         {"green_max": 3.5, "axis": 12, "unit": " days"}),
    ("max_dpd_6m_pl",                "Worst personal-loan delinquency (6M)",    "DPD & Delinquency",    "int", "neutral",     {}),
    ("max_dpd_9m_cc",                "Worst card delinquency (9M)",             "DPD & Delinquency",    "int", "low",         {"green_max": 3.5, "axis": 12, "unit": " days"}),
    ("months_since_last_0p_uns",     "Months since last unsecured 0+ DPD",      "DPD & Delinquency",    "f2",  "cleanNone",   {}),
    ("months_since_last_0p_pl",      "Months since last PL 0+ DPD",             "DPD & Delinquency",    "f2",  "high",        {"green_min": 19.44, "axis": 36, "unit": " months"}),
    ("pct_0plus_24m_all",            "% time 0+ DPD, 24M (all loans)",          "Payment Behavior",     "f2",  "low",         {"green_max": 1.15, "amber_max": 2.35, "axis": 5, "unit": "%"}),
    ("pct_0plus_24m_pl",             "% time 0+ DPD, 24M (personal loans)",     "Payment Behavior",     "f2",  "low",         {"green_max": 1.71, "axis": 5, "unit": "%"}),
    ("pct_missed_payments_18m",      "% missed payments (18M)",                 "Payment Behavior",     "f2",  "neutral",     {"unit": "%"}),
    ("pct_trades_0plus_12m",         "% tradelines hitting 0+ DPD (12M)",       "Payment Behavior",     "f2",  "cleanNone",   {"unit": "%"}),
    ("ratio_good_closed_pl",         "Share of PLs closed in good standing",    "Payment Behavior",     "pct100", "neutral",  {}),
    ("cc_balance_utilization_pct",   "Credit-card utilisation",                 "Utilization",          "f2",  "low",         {"green_max": 83.20, "axis": 100, "unit": "%"}),
    ("pl_balance_remaining_pct",     "Personal-loan balance remaining",         "Utilization",          "f2",  "low",         {"green_max": 87.06, "axis": 100, "unit": "%"}),
    ("unsecured_enquiries_12m",      "Unsecured enquiries (12M)",               "Enquiry",              "int", "neutral",     {}),
    ("trade_to_enquiry_ratio_uns_24m", "Loans opened per enquiry (unsec, 24M)", "Enquiry",             "f2",  "high",        {"green_min": 13.74, "axis": 30}),
    ("interpurchase_time_12m_plbl",  "Gap between PL/BL loans (12M)",           "Acquisition Velocity", "f2",  "presentNone", {}),
    ("interpurchase_time_6m_plbl",   "Gap between PL/BL loans (6M)",            "Acquisition Velocity", "f2",  "high",        {"green_min": 0.62, "axis": 6, "unit": " months"}),
    ("interpurchase_time_24m_all",   "Gap between any loans (24M)",             "Acquisition Velocity", "f2",  "high",        {"green_min": 2.54, "axis": 8, "unit": " months"}),
    ("interpurchase_time_9m_hl_lap", "Gap between home/LAP loans (9M)",         "Acquisition Velocity", "f2",  "presentNone", {}),
    ("interpurchase_time_24m_hl_lap","Gap between home/LAP loans (24M)",        "Acquisition Velocity", "f2",  "presentNone", {}),
    ("interpurchase_time_24m_twl",   "Gap between two-wheeler loans (24M)",     "Acquisition Velocity", "f2",  "neutral",     {}),
    ("interpurchase_time_12m_cl",    "Gap between consumer-durable loans (12M)","Acquisition Velocity", "f2",  "high",        {"green_min": 0.81, "axis": 6, "unit": " months"}),
]

# Plain-English one-liners per group when everything assessable is healthy,
# and when the group has no assessable data at all. Deterministic.
_BF_POSITIVE = {
    "Loan Activity":        "Recent borrowing activity sits within a normal range.",
    "DPD & Delinquency":    "No recent delinquency — repayment history is clean.",
    "Payment Behavior":     "Clean repayment record with no recent missed payments.",
    "Utilization":          "Balances are comfortably within available limits.",
    "Enquiry":              "Credit-seeking behaviour looks measured.",
    "Acquisition Velocity": "No signs of rapid, stacked loan acquisition.",
}
_BF_NODATA = {
    "Loan Activity":        "No recent loan activity reported.",
    "DPD & Delinquency":    "No delinquency history reported.",
    "Payment Behavior":     "No payment-behaviour data reported.",
    "Utilization":          "No utilisation data reported.",
    "Enquiry":              "No recent enquiry data reported.",
    "Acquisition Velocity": "No recent multi-loan activity reported.",
}


def _bf_num(x: float, unit: str) -> str:
    """Round a threshold to a clean number string (no unit)."""
    if unit in (" months", " days"):
        v = round(x, 1) if x < 2 else round(x)
    else:  # "%" or bare ratio / count
        v = round(x) if x >= 10 else round(x, 1)
    return f"{v:g}"


def _bf_round(x: float, unit: str) -> str:
    """Round a threshold to a plain-English string with its unit appended."""
    return f"{_bf_num(x, unit)}{unit}"


def _bf_display(value, fmt: str, unit: str = "") -> str:
    if value is None:
        return "No data"
    if fmt == "int":
        s = str(int(value))
    elif fmt == "pct100":
        return f"{value * 100:.0f}%"
    else:
        s = f"{value:.2f}"
    return s + (unit if unit == "%" else "")


def _bf_hint(direction: str, p: dict) -> str:
    u = p.get("unit", "")
    if direction == "low":
        if p.get("amber_max") is not None:
            return f"healthy below {_bf_round(p['green_max'], u)}, watch to {_bf_round(p['amber_max'], u)}"
        return f"healthy below {_bf_round(p['green_max'], u)}"
    if direction == "high":
        return f"healthy above {_bf_round(p['green_min'], u)}"
    if direction == "band":
        return f"expected {_bf_num(p['lo'], u)}–{_bf_round(p['hi'], u)}"
    return ""


def _bf_segments(axis: float, bands: list) -> list:
    """Bands: ordered [(end_value, rag), ...] spanning 0..axis. Returns
    width-% segments for the bar."""
    segs, prev = [], 0.0
    for end, rag in bands:
        end = max(prev, min(float(end), axis))
        w = (end - prev) / axis * 100.0
        if w > 0.01:
            segs.append({"rag": rag, "w": round(w, 2)})
        prev = end
    return segs


def _bf_metric(field, label, group, fmt, direction, p, tl) -> dict:
    v = tl.get(field) if tl else None
    unit = p.get("unit", "")
    m = {
        "field": field, "label": label, "group": group,
        "display": _bf_display(v, fmt, unit),
        "value": (float(v) if v is not None else None),
    }

    if direction == "neutral":
        m.update(kind="strip", status="neutral", hint="reference only", strip_label="REFERENCE")
        return m
    if direction == "cleanNone":
        # Missing here is GOOD news (no 0+ DPD event on record) — not absent data.
        clean = v is None
        m.update(kind="strip", status=("safe" if clean else "risk"),
                 display=("Clean" if clean else m["display"]),
                 strip_label=("CLEAN" if clean else "ATTENTION"),
                 hint=("no 0+ DPD event on record" if clean else "0+ DPD event on record"))
        return m
    if direction == "presentNone":
        present = v is not None
        m.update(kind="strip", status=("safe" if present else "neutral"),
                 display=(m["display"] if present else "No data"),
                 strip_label=("REPORTED" if present else "NO DATA"),
                 hint=("reported" if present else "not reported"))
        return m

    # numeric bar directions (low / high / band)
    axis = float(p["axis"])
    hint = _bf_hint(direction, p)
    if v is None:
        # Missing measurement → neutral "No data" (never a red risk).
        m.update(kind="strip", status="neutral", display="No data",
                 strip_label="NO DATA", hint=hint)
        return m

    fv = float(v)
    if direction == "low":
        gmax, amax = p["green_max"], p.get("amber_max")
        status = "safe" if fv <= gmax else ("warn" if (amax is not None and fv <= amax) else "risk")
        bands = [(gmax, "green")] + ([(amax, "amber")] if amax is not None else []) + [(axis, "red")]
    elif direction == "high":
        gmin, amin = p["green_min"], p.get("amber_min")
        status = "safe" if fv >= gmin else ("warn" if (amin is not None and fv >= amin) else "risk")
        red_end = amin if amin is not None else gmin
        bands = [(red_end, "red")] + ([(gmin, "amber")] if amin is not None else []) + [(axis, "green")]
    else:  # band
        lo, hi = p["lo"], p["hi"]
        status = "safe" if (lo <= fv < hi) else "risk"
        bands = [(lo, "red"), (hi, "green"), (axis, "red")]

    m.update(
        kind="bar", status=status,
        segments=_bf_segments(axis, bands),
        marker=round(max(0.0, min(fv, axis)) / axis * 100.0, 2),
        hint=hint,
    )
    return m


def _bf_takeaway(group: str, ok: int, warn: int, risk: int, assessable: int,
                 metrics: list) -> str:
    """Deterministic plain-English one-liner summarising a feature group."""
    if assessable == 0:
        return _BF_NODATA.get(group, "No data reported for this group.")
    if risk:
        first = next((m["label"] for m in metrics if m["status"] == "risk"), "")
        lead = first[0].lower() + first[1:] if first else "a metric"
        n = "signal needs" if risk == 1 else "signals need"
        return f"{risk} {n} attention — e.g. {lead}."
    if warn:
        n = "metric" if warn == 1 else "metrics"
        return f"Mostly healthy; {warn} {n} to keep an eye on."
    return _BF_POSITIVE.get(group, "All assessed metrics look healthy.")


def _compute_behavioral(tl: Optional[dict]) -> dict:
    """Build the threshold-aware behavioral feature model for the v2 views.

    Each group becomes a summary card (dot meter, counts, plain-English
    takeaway). Groups are returned worst-first so weak areas surface; groups
    with no assessable data sink to the bottom.
    """
    metrics = [_bf_metric(*spec[:5], spec[5], tl) for spec in _BF_SPECS]

    groups = []
    for g in _BF_GROUPS:
        gm = [m for m in metrics if m["group"] == g]
        ok = sum(1 for m in gm if m["status"] == "safe")
        warn = sum(1 for m in gm if m["status"] == "warn")
        risk = sum(1 for m in gm if m["status"] == "risk")
        assessable = ok + warn + risk
        dots = round(5 * ok / assessable) if assessable else 0
        status = ("risk" if risk else "warn" if warn else
                  "healthy" if assessable else "nodata")
        groups.append({
            "name": g, "metrics": gm,
            "ok": ok, "warn": warn, "risk": risk, "assessable": assessable,
            "dots": dots, "status": status,
            "count_label": (f"{ok}/{assessable} ok" if assessable else "no data"),
            "takeaway": _bf_takeaway(g, ok, warn, risk, assessable, gm),
        })

    # Worst-first: data groups before no-data; then lower health ratio, more risk.
    groups.sort(key=lambda c: (
        0 if c["assessable"] else 1,
        (c["ok"] / c["assessable"]) if c["assessable"] else 0,
        -c["risk"],
    ))

    summary = {
        "safe": sum(1 for m in metrics if m["status"] == "safe"),
        "warn": sum(1 for m in metrics if m["status"] == "warn"),
        "risk": sum(1 for m in metrics if m["status"] == "risk"),
        "neutral": sum(1 for m in metrics if m["status"] == "neutral"),
    }

    # Flat list for the table view, sorted risk-first (weak areas on top).
    _SEV = {"risk": 0, "warn": 1, "safe": 2, "neutral": 3}
    flat = [m for g in groups for m in g["metrics"]]
    flat.sort(key=lambda m: _SEV.get(m["status"], 4))

    return {"groups": groups, "flat": flat, "summary": summary}


# ---------------------------------------------------------------------------
# Portfolio Visualizations — at-a-glance header, quick split bars, exposure
# sparkline. All deterministic (server-rendered); the template only loops.
# ---------------------------------------------------------------------------

# Display-name → brand colour (mirrors PRODUCT_COLORS in the template).
_VIZ_PRODUCT_COLORS = {
    "Personal Loan": "#4E79A7", "Credit Card": "#F28E2B", "Home Loan": "#59A14F",
    "Auto Loan": "#E15759", "Business Loan": "#B07AA1", "LAP": "#9C755F",
    "LAS": "#86BCB6", "LAD": "#D37295", "Gold Loan": "#EDC948",
    "Two Wheeler Loan": "#76B7B2", "Consumer Durable": "#FF9DA7",
    "Commercial Vehicle Loan": "#A0CBE8", "Other": "#BAB0AC",
}
_VIZ_FALLBACK = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1",
                 "#9C755F", "#86BCB6", "#D37295", "#EDC948", "#76B7B2"]


def _viz_inr(x) -> str:
    """Compact ₹ lakh/cr formatting."""
    x = float(x or 0)
    if x >= 1e7:
        return f"₹{x / 1e7:.1f}Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.1f}L"
    if x >= 1e3:
        return f"₹{x / 1e3:.0f}K"
    return f"₹{x:.0f}"


def _viz_split(name: str, segments: list) -> dict:
    """A horizontal split bar. segments: [(label, value, color)]. Computes
    width-% per segment; calm 'no data' when everything is zero."""
    total = sum(max(0.0, float(v)) for _, v, _ in segments)
    out = []
    for label, value, color in sorted(segments, key=lambda t: -max(0.0, float(t[1]))):
        v = max(0.0, float(value))
        if v <= 0:
            continue
        out.append({
            "label": label,
            "display": (str(int(v)) if float(v).is_integer() else f"{v:.1f}"),
            "pct": round(v / total * 100, 1) if total else 0,
            "color": color,
        })
    return {"name": name, "has_data": total > 0, "segments": out}


def _viz_sparkline(vals: list, w: int = 240, h: int = 40, pad: int = 4) -> Optional[str]:
    """Inline SVG polyline sparkline (avoids a hidden-tab canvas)."""
    pts = [v for v in vals if v is not None]
    if len(pts) < 2:
        return None
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1.0
    n = len(pts)
    coords = []
    for i, v in enumerate(pts):
        x = pad + i * (w - 2 * pad) / (n - 1)
        y = pad + (1 - (v - lo) / rng) * (h - 2 * pad)
        coords.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{pad},{h - pad} " + poly + f" {w - pad},{h - pad}"
    lx, ly = coords[-1]
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" class="spark" '
        f'role="img" aria-label="exposure trend">'
        f'<polygon points="{area}" fill="#6366f120" stroke="none"/>'
        f'<polyline points="{poly}" fill="none" stroke="#6366f1" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="#6366f1"/></svg>'
    )


def _compute_viz(vectors_data: list, ei, monthly_exposure: Optional[dict]) -> dict:
    """Build the at-a-glance header, quick-view split bars, and exposure
    summary for the Portfolio Visualizations section."""
    total_os = float(getattr(ei, "total_outstanding", 0) or 0)
    total_sanc = float(getattr(ei, "total_sanctioned", 0) or 0)
    util = round(total_os / total_sanc * 100) if total_sanc > 0 else None

    # Per-product rollup
    prods = []
    for v in vectors_data:
        prods.append({
            "name": str(v["loan_type_display"]),
            "os": float(v.get("total_outstanding_amount") or 0),
            "count": int(v.get("loan_count") or 0),
            "secured": bool(v.get("secured")),
        })
    total_count = sum(p["count"] for p in prods) or 0
    n_products = len(prods)

    # Concentration (by outstanding, fallback to count)
    rank_key = "os" if sum(p["os"] for p in prods) > 0 else "count"
    ranked = sorted(prods, key=lambda p: p[rank_key], reverse=True)
    base = sum(p[rank_key] for p in prods) or 1
    if ranked:
        top = ranked[0]
        top_share = top[rank_key] / base * 100
        if top_share >= 60:
            conc = f"Concentrated in {top['name']}"
        elif len(ranked) > 1 and (top[rank_key] + ranked[1][rank_key]) / base * 100 >= 75:
            conc = f"Mostly {top['name']} and {ranked[1]['name']}"
        else:
            conc = f"Spread across {n_products} loan products"
    else:
        conc = "No tradelines reported"

    # Secured vs unsecured (by count)
    sec_count = sum(p["count"] for p in prods if p["secured"])
    unsec_count = total_count - sec_count
    unsec_share = unsec_count / total_count * 100 if total_count else 0
    if total_count == 0:
        sec_clause = ""
    elif unsec_share >= 99:
        sec_clause = "fully unsecured"
    elif unsec_share >= 60:
        sec_clause = "largely unsecured"
    elif unsec_share <= 1:
        sec_clause = "fully secured"
    elif unsec_share <= 40:
        sec_clause = "largely secured"
    else:
        sec_clause = "a mix of secured and unsecured"

    takeaway = conc + (f"; {sec_clause}." if sec_clause else ".")

    chips = [
        {"label": "Outstanding", "value": _viz_inr(total_os)},
        {"label": "Sanctioned", "value": _viz_inr(total_sanc)},
        {"label": "Utilisation", "value": (f"{util}%" if util is not None else "—")},
    ]

    # Quick-view split bars
    def pcol(name, i):
        return _VIZ_PRODUCT_COLORS.get(name) or _VIZ_FALLBACK[i % len(_VIZ_FALLBACK)]

    live_total = sum(int(v.get("live_count") or 0) for v in vectors_data)
    closed_total = sum(int(v.get("closed_count") or 0) for v in vectors_data)
    on_us = sum(int(v.get("on_us_count") or 0) for v in vectors_data)
    off_us = sum(int(v.get("off_us_count") or 0) for v in vectors_data)

    splits = [
        _viz_split("Product mix (by count)",
                   [(p["name"], p["count"], pcol(p["name"], i)) for i, p in enumerate(prods)]),
        _viz_split("Live vs Closed",
                   [("Live", live_total, "#6366f1"), ("Closed", closed_total, "#cbd5e1")]),
        _viz_split("Secured vs Unsecured",
                   [("Secured", sec_count, "#10b981"), ("Unsecured", unsec_count, "#f59e0b")]),
        _viz_split("On-Us (Kotak) vs Off-Us",
                   [("On-Us (Kotak)", on_us, "#6366f1"), ("Off-Us", off_us, "#94a3b8")]),
    ]

    # Exposure over time → total sanctioned exposure per month
    exposure = None
    months = (monthly_exposure or {}).get("months") or []
    series = (monthly_exposure or {}).get("series") or {}
    if months and series:
        totals = [sum(float(series[p][i]) for p in series) for i in range(len(months))]
        if any(t > 0 for t in totals):
            peak = max(totals)
            peak_idx = totals.index(peak)
            now = totals[-1]
            first = next((t for t in totals if t > 0), totals[0])
            down_from_peak = round((peak - now) / peak * 100) if peak else 0
            chg = (now - first) / first * 100 if first else 0
            trend = "rising" if chg > 5 else "easing" if chg < -5 else "stable"
            exposure = {
                "spark": _viz_sparkline(totals),
                "peak": _viz_inr(peak),
                "peak_when": str(months[peak_idx]),
                "now": _viz_inr(now),
                "down_from_peak": down_from_peak,
                "trend": trend,
                "has_detail": True,
            }

    return {"takeaway": takeaway, "chips": chips, "splits": splits, "exposure": exposure}


# Checklist labels that duplicate a scorecard signal (Max DPD / Adverse / FOIR /
# CC-util / Exposure) — dropped from the merged risk grid so each fact appears once.
_RISK_CHECKLIST_DUP = {
    "MAX DPD occurred",
    "Adverse events (write-off / settlement)",
    "High FOIR (> 50%)",
    "CC utilization elevated (≥30%)",
    "Exposure elevated",
}
_SEV_TO_RAG = {"high": "red", "medium": "amber", "positive": "green", "neutral": "neutral"}


def _compute_risk_items(scorecard: dict, bureau_checklist: list) -> list:
    """Fold scorecard signals + the checklist-only binary flags into one compact,
    de-duplicated list for the v3 'Risk Assessment' grid (merge A).

    Each item: {label, value, note, rag, tip, checked}. `checked` is None for a
    measured signal (RAG metric) and True/False for a pass/fail checklist flag.
    Behavioral tl_features tiles are intentionally excluded — their canonical home
    is the Behavioral & Risk Features section.
    """
    items: list = []

    # Deterministic risk signals (CIBIL, Max DPD, CC Util, FOIR, Adverse, Exposure…)
    for s in (scorecard.get("signals") or []):
        items.append({
            "label": s.get("label", ""),
            "value": s.get("value", ""),
            "note": s.get("note", ""),
            "rag": s.get("rag", "neutral"),
            "tip": s.get("tooltip", ""),
            "checked": None,
        })

    # Checklist-only binary flags (Kotak presence/default, live HL, bureau/banking thick)
    for it in bureau_checklist:
        label = it.get("label", "")
        if label in _RISK_CHECKLIST_DUP:
            continue
        checked = bool(it.get("checked"))
        items.append({
            "label": label,
            "value": ("Yes" if checked else "No"),
            "note": it.get("detail") or "",
            "rag": _SEV_TO_RAG.get(it.get("severity", "neutral"), "neutral"),
            "tip": it.get("detail") or "",
            "checked": checked,
        })

    # Categorise worst-first (concerns → positives → info) so the grid reads by
    # severity, like the old v2 checklist. Stable sort keeps signal order within a band.
    _rag_rank = {"red": 0, "amber": 1, "green": 2, "neutral": 3}
    items.sort(key=lambda x: _rag_rank.get(x["rag"], 4))
    return items


def _compute_v2_context(
    bureau_report: Optional[BureauReport],
    scorecard: dict,
    bureau_checklist: list,
    key_findings_data: list,
    tl_features_data: Optional[dict],
    vectors_data: list,
) -> dict:
    """Pre-compute everything the v2 template needs beyond the shared context.

    All RAG/threshold logic lives here (templates only render). Returns plain
    dicts/lists so the payload survives |tojson in the risk-trail export.
    """
    v2: dict = {"kpis": None, "profile": None, "nav_badges": {}, "charts": "null",
                "viz": None, "dpd_accounts": None, "risk_items": []}

    flagged = sum(
        1 for it in bureau_checklist
        if it.get("checked") and it.get("severity") in ("high", "medium")
    )
    findings_high = sum(1 for f in key_findings_data if f.get("severity") == "high_risk")
    # v3 hides per-account (restatement) findings from the Findings panel — badge counts
    # only the derived/portfolio high-risk findings that actually remain visible there.
    findings_high_derived = sum(
        1 for f in key_findings_data
        if f.get("severity") == "high_risk" and not f.get("account_level")
    )
    v2["nav_badges"] = {
        "checklist_flagged": flagged,
        "findings_high": findings_high,
        "findings_high_derived": findings_high_derived,
    }

    # Merged, de-duplicated Risk Assessment grid (merge A) — needs scorecard + checklist,
    # both available even when bureau_report is None, so compute before the early return.
    v2["risk_items"] = _compute_risk_items(scorecard, bureau_checklist)

    if bureau_report is None:
        return v2

    ei = bureau_report.executive_inputs
    tl = tl_features_data or {}

    # ── KPI strip ──────────────────────────────────────────────────────
    tu_score = getattr(ei, "tu_score", None)
    if tu_score is None:
        cibil = {"value": "—", "sub": "Not available", "rag": "neutral"}
    else:
        if tu_score >= 750:
            c_rag, c_note = "green", "Excellent"
        elif tu_score >= 700:
            c_rag, c_note = "amber", "Good"
        elif tu_score >= 650:
            c_rag, c_note = "amber", "Fair"
        else:
            c_rag, c_note = "red", "Poor"
        cibil = {"value": str(tu_score), "sub": f"{c_note} · TransUnion", "rag": c_rag}

    if ei.max_dpd is None:
        max_dpd = {"value": "N/A", "sub": "No DPD data", "rag": "neutral"}
    else:
        parts = []
        if ei.max_dpd_months_ago is not None:
            parts.append(f"{ei.max_dpd_months_ago}M ago")
        if ei.max_dpd_loan_type:
            parts.append(str(ei.max_dpd_loan_type))
        max_dpd = {
            "value": f"{ei.max_dpd} days",
            "sub": " · ".join(parts) if parts else ("Clean history" if ei.max_dpd == 0 else "Delinquent"),
            "rag": "red" if ei.max_dpd > 30 else ("amber" if ei.max_dpd > 0 else "green"),
        }

    foir_val = tl.get("foir")
    if foir_val is None:
        foir = {"value": "N/A", "sub": "Not available", "rag": "neutral"}
    else:
        sub_parts = []
        if tl.get("foir_unsec") is not None:
            sub_parts.append(f"Unsec {tl['foir_unsec']:.1f}%")
        if tl.get("aff_emi") is not None:
            sub_parts.append(f"EMI ₹{tl['aff_emi']:,.0f}")
        foir = {
            "value": f"{foir_val:.1f}%",
            "sub": " · ".join(sub_parts) if sub_parts else "Bureau obligation ÷ income",
            "rag": "red" if foir_val > 65 else ("amber" if foir_val > 40 else "green"),
        }

    unsec_pct = (
        f"{ei.unsecured_outstanding / ei.total_outstanding * 100:.0f}%"
        if ei.total_outstanding > 0 else None
    )
    spark_labels: list = []
    spark_series: list = []
    me = getattr(bureau_report, "monthly_exposure", None)
    if me and me.get("months") and me.get("series"):
        spark_labels = [str(m) for m in me["months"]]
        n = len(spark_labels)
        spark_series = [
            float(sum(me["series"][k][i] for k in me["series"] if i < len(me["series"][k])))
            for i in range(n)
        ]
    exposure = {
        "value": f"₹{format_inr_units(ei.total_outstanding)}",
        "sub": f"Sanctioned ₹{format_inr_units(ei.total_sanctioned)}"
               + (f" · Unsec {unsec_pct}" if unsec_pct else ""),
        "rag": "neutral",
        "labels": spark_labels,
        "series": spark_series,
    }

    signals = scorecard.get("signals") or []
    red_count = sum(1 for s in signals if s.get("rag") == "red")
    amber_count = sum(1 for s in signals if s.get("rag") == "amber")
    stress_pct = round(100 * (red_count + 0.5 * amber_count) / max(len(signals), 1))
    verdict = {
        "value": scorecard.get("verdict", "—"),
        "rag": scorecard.get("verdict_rag", "neutral"),
        "stress_pct": min(stress_pct, 100),
        "sub": f"{red_count} red · {amber_count} amber of {len(signals)} signals",
    }

    v2["kpis"] = {
        "cibil": cibil, "max_dpd": max_dpd, "foir": foir,
        "exposure": exposure, "verdict": verdict,
    }

    # ── Customer profile card ──────────────────────────────────────────
    profile = {
        "ktk_rel": tl.get("ktk_rel"),
        "customer_segment": tl.get("customer_segment"),
        "income_source": tl.get("income_source"),
        "bank_grp": tl.get("bank_grp"),
        "bu_grp": tl.get("bu_grp"),
        "affluence_amt": tl.get("affluence_amt"),
        "node": tl.get("node"),
    }
    v2["profile"] = profile if any(val is not None for val in profile.values()) else None

    # ── Behavioral & Risk Features (summary cards / bars / table) ──────
    v2["behavioral"] = _compute_behavioral(tl)

    # ── v2-only chart payloads (pre-serialized like chart_data) ────────
    live_closed = {
        "labels": [str(v["loan_type_display"]) for v in vectors_data],
        "live": [int(v["live_count"]) for v in vectors_data],
        "closed": [int(v["closed_count"]) for v in vectors_data],
    }

    # Vintage spans: month index axis from earliest open to today
    vintage = None
    spans = []
    today = date.today()
    for v in vectors_data:
        start = _parse_month_str(v.get("earliest_opened"))
        if start is None:
            continue
        if int(v.get("live_count") or 0) > 0:
            end = today
        else:
            end = _parse_month_str(v.get("latest_closed")) or today
        spans.append((str(v["loan_type_display"]), start, end))
    if spans:
        origin = min(s[1] for s in spans)
        axis_len = (today.year - origin.year) * 12 + (today.month - origin.month) + 1
        import calendar
        axis = [
            f"{calendar.month_abbr[(origin.month - 1 + i) % 12 + 1]} {origin.year + (origin.month - 1 + i) // 12}"
            for i in range(axis_len)
        ]
        items = []
        for label, start, end in spans:
            s_idx = (start.year - origin.year) * 12 + (start.month - origin.month)
            e_idx = (end.year - origin.year) * 12 + (end.month - origin.month)
            items.append({"label": label, "start": s_idx, "end": max(e_idx, s_idx + 1)})
        vintage = {"axis": axis, "items": items}

    # Interactive portfolio explorer — per-product metric matrix.
    # The template lets the analyst pick which metric to plot and the chart
    # type; all values are computed here (determinism > template logic).
    def _f(v):
        return float(v) if v is not None else 0.0

    def _util(v):
        r = v.get("utilization_ratio")
        return round(float(r) * 100, 2) if r is not None else None

    def _vint(v):
        m = v.get("avg_vintage_months")
        return round(float(m), 1) if m is not None else None

    explorer = {
        "products": [str(v["loan_type_display"]) for v in vectors_data],
        "metrics": {
            "sanctioned":  {"label": "Sanctioned ₹",    "fmt": "inr", "values": [_f(v.get("total_sanctioned_amount")) for v in vectors_data]},
            "outstanding": {"label": "Outstanding ₹",    "fmt": "inr", "values": [_f(v.get("total_outstanding_amount")) for v in vectors_data]},
            "count":       {"label": "Tradeline Count",  "fmt": "int", "values": [int(v.get("loan_count") or 0) for v in vectors_data]},
            "live":        {"label": "Live",             "fmt": "int", "values": [int(v.get("live_count") or 0) for v in vectors_data]},
            "closed":      {"label": "Closed",           "fmt": "int", "values": [int(v.get("closed_count") or 0) for v in vectors_data]},
            "overdue":     {"label": "Overdue ₹",        "fmt": "inr", "values": [_f(v.get("overdue_amount")) for v in vectors_data]},
            "utilization": {"label": "Utilization %",    "fmt": "pct", "values": [_util(v) for v in vectors_data]},
            "on_us":       {"label": "On-Us Count",      "fmt": "int", "values": [int(v.get("on_us_count") or 0) for v in vectors_data]},
            "vintage":     {"label": "Avg Vintage (mo)", "fmt": "num", "values": [_vint(v) for v in vectors_data]},
            "max_single":  {"label": "Largest Loan ₹",   "fmt": "inr", "values": [_f(v.get("max_single_sanction")) for v in vectors_data]},
            "joint":       {"label": "Joint Tradelines", "fmt": "int", "values": [int(v.get("joint_count") or 0) for v in vectors_data]},
        },
    }

    v2["charts"] = json.dumps({
        "live_closed": live_closed,
        "vintage": vintage,
        "dpd_grid": _compute_dpd_grid(bureau_report.meta.customer_id),
        "explorer": explorer,
    })

    # Per-account DPD swimlanes (months × tradeline, exception-first)
    v2["dpd_accounts"] = _compute_dpd_accounts(bureau_report.meta.customer_id)

    # At-a-glance header + quick split bars + exposure sparkline (server-rendered)
    v2["viz"] = _compute_viz(
        vectors_data,
        bureau_report.executive_inputs,
        getattr(bureau_report, "monthly_exposure", None),
    )

    return v2


# Theme name → template file. "v2" is the maintained default;
# "v3" is the merged/de-duplicated variant (in development);
# "original" and "emerald" are frozen legacy fallbacks.
THEME_TEMPLATES = {
    "v2":       "combined_report_v2.html",
    "v3":       "combined_report_v3.html",
    "original": "combined_report_original.html",
    "emerald":  "combined_report.html",
}
DEFAULT_THEME = "v2"


def render_combined_report_html(
    bureau_report: Optional[BureauReport],
    theme: str = DEFAULT_THEME,
) -> str:
    """Render the Bureau Analyser HTML from the bureau report using Jinja2.

    Args:
        theme: Color scheme to use. Options: "v2" (default), "original", "emerald".

    Returns:
        HTML string.
    """
    template_name = THEME_TEMPLATES.get(theme, THEME_TEMPLATES[DEFAULT_THEME])
    template_dir = Path(__file__).parent.parent.parent / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    env.filters["mask_id"] = mask_customer_id
    env.filters["inr"] = format_inr
    env.filters["inr_units"] = format_inr_units
    env.filters["segment"] = strip_segment_prefix

    # Prepare bureau data for template
    vectors_data = []
    tl_features_data = None
    key_findings_data = []
    if bureau_report:
        for loan_type, vec in bureau_report.feature_vectors.items():
            vec_dict = asdict(vec)
            vec_dict["loan_type_display"] = get_loan_type_display_name(loan_type)
            vec_dict["secured"] = vec.secured
            # v3 Status column (merge B/D): only *real* adverse codes count — filter to the
            # canonical _ADVERSE_FLAGS set so the "NUL" parse artifact isn't shown as adverse
            # (mirrors checklist B2 + the retired Defaulted tab, which both exclude NUL).
            real_adverse = [f for f in (vec.forced_event_flags or []) if f in _ADVERSE_FLAGS]
            vec_dict["real_adverse_flags"] = real_adverse
            vec_dict["is_delinquent"] = bool(
                (vec.max_dpd or 0) > 0 or real_adverse or (vec.overdue_amount or 0) > 0
            )
            vectors_data.append(vec_dict)

        if bureau_report.tradeline_features is not None:
            tl_features_data = asdict(bureau_report.tradeline_features)

        key_findings_data = findings_to_dicts(bureau_report.key_findings) if bureau_report.key_findings else []

    chart_data = _compute_html_chart_data(vectors_data, bureau_report.executive_inputs, bureau_report.monthly_exposure) if bureau_report else None

    from tools.scorecard import compute_scorecard
    scorecard = compute_scorecard(bureau_report=bureau_report)

    from pipeline.reports.report_summary_chain import summarize_exposure_timeline
    exposure_summary = summarize_exposure_timeline(
        bureau_report.monthly_exposure if bureau_report else None
    )

    bureau_checklist = compute_checklist(bureau_report)
    persona = compute_probable_persona(bureau_report)

    # Feature flags — flip to True to restore hidden sections
    section_flags = {
        "show_scorecard_narrative": False,   # summary text inside Risk Variables
    }

    v2 = _compute_v2_context(
        bureau_report, scorecard, bureau_checklist,
        key_findings_data, tl_features_data, vectors_data,
    )

    template = env.get_template(template_name)
    return template.render(
        bureau_report=bureau_report,
        vectors_data=vectors_data,
        tl_features=tl_features_data,
        key_findings=key_findings_data,
        chart_data=chart_data,
        scorecard=scorecard,
        exposure_summary=exposure_summary,
        bureau_checklist=bureau_checklist,
        persona=persona,
        section_flags=section_flags,
        v2=v2,
    )
