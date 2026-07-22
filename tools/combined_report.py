"""Bureau Analyser report tool - renders the bureau report via the rich
combined-report renderer/template.

Builds the bureau report (deterministic feature extraction + aggregation),
generates the LLM bureau narrative, then renders the bureau-only document
(HTML + optional PDF) plus a one-row Excel export for batch merging.
"""

import logging
import os
from typing import Optional, Tuple

from schemas.bureau_report import BureauReport
from tools.bureau import generate_bureau_report_pdf

logger = logging.getLogger(__name__)

# Directory where per-customer Excel files are written
_EXCEL_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports", "excel"
)


def generate_combined_report_pdf(
    customer_id: int,
    theme: str = "v2",
    save_intermediate: bool = True,
) -> Tuple[Optional[BureauReport], str]:
    """Generate the Bureau Analyser report as HTML (+ optional PDF).

    Steps:
        1. Build bureau report + LLM narrative
        2. Render bureau-only document (combined renderer/template)
        3. Export a one-row Excel file for batch merging

    Args:
        customer_id: The customer identifier (CRN).
        theme: HTML theme name (default "v2"; "original" and "emerald" are legacy).
        save_intermediate: When False, skip the standalone bureau PDF/HTML and
            the report PDF — only save the report HTML and Excel.  Used by
            batch_reports to avoid disk clutter.

    Returns:
        Tuple of (BureauReport | None, report_path).
    """
    # 1. Bureau report (deterministic build + LLM narrative)
    bureau_report = None
    try:
        if save_intermediate:
            bureau_report, _ = generate_bureau_report_pdf(customer_id)
        else:
            # Build data + LLM narrative but skip the standalone bureau PDF/HTML
            from pipeline.reports.bureau_report_builder import build_bureau_report
            from pipeline.reports.report_summary_chain import generate_bureau_review
            bureau_report = build_bureau_report(customer_id)
            try:
                bureau_report.narrative = generate_bureau_review(
                    bureau_report.executive_inputs,
                    tradeline_features=bureau_report.tradeline_features,
                    monthly_exposure=bureau_report.monthly_exposure,
                    customer_id=customer_id,
                )
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Bureau report unavailable for {customer_id}: {e}")

    # Exposure commentary (deterministic) — used by Excel export
    exposure_text = None
    try:
        from pipeline.reports.report_summary_chain import summarize_exposure_timeline
        exposure_text = summarize_exposure_timeline(
            bureau_report.monthly_exposure if bureau_report else None
        )
    except Exception as e:
        logger.warning(f"Exposure summary failed for {customer_id}: {e}")

    # 2. Render bureau-only document
    from pipeline.renderers.combined_report_renderer import render_combined_report
    report_path = render_combined_report(
        bureau_report, theme=theme, save_pdf=save_intermediate,
    )

    # 3. Export one-row Excel file for this customer (batch-merge later)
    try:
        from tools.excel_exporter import build_excel_row, export_row_to_excel
        row = build_excel_row(
            customer_id=customer_id,
            bureau_report=bureau_report,
            report_path=report_path,
            exposure_summary=exposure_text,
        )
        excel_path = os.path.join(_EXCEL_OUTPUT_DIR, f"{customer_id}.xlsx")
        export_row_to_excel(row, excel_path)
    except Exception as exc:
        logger.warning("Excel export failed for %s: %s", customer_id, exc)

    return bureau_report, report_path
