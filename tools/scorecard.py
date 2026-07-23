"""Scorecard computation — one-page risk verdict for all report types.

Computes a structured scorecard dict from a BureauReport.
No LLM calls — pure deterministic threshold logic using config/thresholds.py.

The scorecard contains:
  - verdict:     "LOW RISK" / "CAUTION" / "HIGH RISK"
  - verdict_rag: "green" / "amber" / "red"
  - signals:     list of RAG-tagged metric chips
  - strengths:   up to 3 positive findings
  - concerns:    up to 3 risk findings
  - verify:      items to cross-check
  - narrative:   LLM summary text (injected by caller)
"""

import logging
from typing import Optional
from utils.helpers import format_inr

import config.thresholds as T

logger = logging.getLogger(__name__)

_ADVERSE_HIGH = {"WRF", "SET", "SMA"}
_ADVERSE_MODERATE = {"SUB", "DBT", "LSS", "WOF"}


def _rag(value, green_max=None, amber_max=None, green_min=None, amber_min=None,
         invert=False):
    """Return 'green' / 'amber' / 'red' for a numeric value.

    Two modes:
      Lower-is-better (invert=False, default):
        value <= green_max → green, <= amber_max → amber, else red
      Higher-is-better (invert=True):
        value >= green_min → green, >= amber_min → amber, else red
    """
    if value is None:
        return "neutral"
    if not invert:
        if green_max is not None and value <= green_max:
            return "green"
        if amber_max is not None and value <= amber_max:
            return "amber"
        return "red"
    else:
        if green_min is not None and value >= green_min:
            return "green"
        if amber_min is not None and value >= amber_min:
            return "amber"
        return "red"


def _rag_exposure(pct_change: float) -> tuple[str, str]:
    """Return (rag, direction_label) for an exposure % change."""
    if pct_change <= -5:
        return "green", f"↓ {abs(pct_change):.0f}% declining"
    elif pct_change < 5:
        return "neutral", "Stable"
    elif pct_change <= 30:
        return "amber", f"↑ {pct_change:.0f}% growing"
    else:
        return "red", f"↑ {pct_change:.0f}% rapid growth"


def _exposure_signals(monthly_exposure: dict) -> list:
    """Compute 6M and 12M sanctioned exposure trend signals independently.

    Returns a list of 0, 1, or 2 signal chips depending on how much history
    is available.  Each chip only appears if its window has enough data.

    Windows:
      12M: current month vs exactly 12M ago   (requires n >= 13 data points)
       6M: last-6M avg vs prior-6M avg        (requires n >= 7 data points)

    RAG convention (lender perspective — growing debt = risk):
      green:   ≤ −5%  (deleveraging)
      neutral: −5% to +5% (stable)
      amber:   +5% to +30% (growing)
      red:     > +30% (rapid accumulation)
    """
    if not monthly_exposure:
        return []

    months = monthly_exposure.get("months", [])
    series = monthly_exposure.get("series", {})
    if not months or not series:
        return []

    n = len(months)
    totals = [
        sum(series[lt][i] for lt in series if i < len(series[lt]))
        for i in range(n)
    ]

    if all(t == 0 for t in totals):
        return []

    chips = []

    # ── 12M point-in-time ────────────────────────────────────────────────────
    if n >= 13:
        current = totals[-1]
        ago_12m = totals[-13]
        if ago_12m > 0:
            pct_12m = (current - ago_12m) / ago_12m * 100
        else:
            pct_12m = 100.0 if current > 0 else 0.0
        rag, direction = _rag_exposure(pct_12m)
        tooltip = (
            f"Sanctioned exposure: {months[-1]} = ₹{current/100000:.1f}L · 12M ago = ₹{ago_12m/100000:.1f}L.\n"
            f"Change: {pct_12m:+.1f}%. Thresholds: ≤−5% = declining · ≤+30% = growing · >+30% = rapid"
        )
        chips.append({"label": "Exposure 12M", "value": direction, "rag": rag, "note": "vs 12M ago", "tooltip": tooltip})


    return chips


def _bureau_signals(bureau_report) -> list:
    """Compute bureau risk signals from BureauReport."""
    signals = []
    ei = bureau_report.executive_inputs
    tl = bureau_report.tradeline_features

    # 0. CIBIL Score (tu_score)
    tu_score = getattr(ei, "tu_score", None)
    if tu_score is not None:
        if tu_score >= 750:
            tu_rag, tu_note = "green", "Excellent"
        elif tu_score >= 700:
            tu_rag, tu_note = "amber", "Good"
        elif tu_score >= 650:
            tu_rag, tu_note = "amber", "Fair"
        else:
            tu_rag, tu_note = "red", "Poor"
        signals.append({
            "label": "CIBIL Score",
            "value": str(tu_score),
            "rag": tu_rag,
            "note": tu_note,
            "tooltip": "TransUnion credit score from bureau data",
        })

    # 1. Max DPD
    dpd = ei.max_dpd
    if dpd is not None:
        rag = _rag(dpd, green_max=0, amber_max=T.DPD_MODERATE_RISK)
        note_parts = []
        if ei.max_dpd_loan_type:
            note_parts.append(ei.max_dpd_loan_type)
        if ei.max_dpd_months_ago is not None:
            note_parts.append(f"{ei.max_dpd_months_ago}M ago")
        note = ", ".join(note_parts) if note_parts else ("Clean" if dpd == 0 else "Delinquent")
        dpd_ctx = f"{ei.max_dpd_loan_type or 'loan'}, {ei.max_dpd_months_ago}M ago" if ei.max_dpd_months_ago is not None else (ei.max_dpd_loan_type or "")
        tooltip = (
            f"Max DPD: {dpd} days{(' (' + dpd_ctx + ')') if dpd_ctx else ''}.\n"
            f"Thresholds: 0 = clean · 1–{T.DPD_MODERATE_RISK} = amber · >{T.DPD_MODERATE_RISK} = high risk"
        )
        signals.append({"label": "Max DPD", "value": f"{dpd} days", "rag": rag, "note": note, "tooltip": tooltip})

    # 2. CC Utilization
    if tl and tl.cc_balance_utilization_pct is not None:
        util = tl.cc_balance_utilization_pct
        rag = _rag(util, green_max=T.CC_UTIL_HEALTHY, amber_max=T.CC_UTIL_HIGH_RISK)
        label_note = "Over-utilized" if util > T.CC_UTIL_HIGH_RISK else (
            "Elevated" if util > T.CC_UTIL_MODERATE_RISK else "Healthy"
        )
        tooltip = (
            f"CC balance utilization: {util:.1f}%.\n"
            f"Thresholds: ≤{T.CC_UTIL_HEALTHY}% = healthy · ≤{T.CC_UTIL_HIGH_RISK}% = elevated · >{T.CC_UTIL_HIGH_RISK}% = over-utilized"
        )
        signals.append({"label": "CC Util", "value": f"{util:.0f}%", "rag": rag, "note": label_note, "tooltip": tooltip})

    # 3. Enquiry Pressure
    if tl and tl.unsecured_enquiries_12m is not None:
        enq = tl.unsecured_enquiries_12m
        rag = _rag(enq, green_max=T.ENQUIRY_HEALTHY, amber_max=T.ENQUIRY_MODERATE_RISK)
        note = "High pressure" if enq > T.ENQUIRY_MODERATE_RISK else (
            "Moderate" if enq > T.ENQUIRY_HEALTHY else "Minimal"
        )
        tooltip = (
            f"Unsecured credit enquiries in last 12M: {enq}.\n"
            f"Thresholds: ≤{T.ENQUIRY_HEALTHY} = minimal · ≤{T.ENQUIRY_MODERATE_RISK} = moderate · >{T.ENQUIRY_MODERATE_RISK} = high pressure"
        )
        signals.append({"label": "Enquiries", "value": f"{enq} in 12M", "rag": rag, "note": note, "tooltip": tooltip})

    # 4. Loan Stacking (new PLs in 6M)
    if tl and tl.new_trades_6m_pl is not None:
        new_pl = tl.new_trades_6m_pl
        rag = _rag(new_pl, green_max=0, amber_max=T.NEW_PL_6M_MODERATE_RISK - 1)
        note = "Rapid stacking" if new_pl >= T.NEW_PL_6M_HIGH_RISK else (
            "Multiple" if new_pl >= T.NEW_PL_6M_MODERATE_RISK else ("1 new PL" if new_pl == 1 else "None")
        )
        tooltip = (
            f"New personal loans opened in last 6M: {new_pl}.\n"
            f"Thresholds: 0 = none · 1 = amber · ≥{T.NEW_PL_6M_MODERATE_RISK} = multiple · ≥{T.NEW_PL_6M_HIGH_RISK} = rapid stacking"
        )
        signals.append({"label": "Loan Stack", "value": f"{new_pl} new PLs", "rag": rag, "note": "6M window", "tooltip": tooltip})

    # 5. Missed Payments
    if tl and tl.pct_missed_payments_18m is not None:
        missed = tl.pct_missed_payments_18m
        rag = _rag(missed, green_max=0, amber_max=T.MISSED_PAYMENTS_HIGH_RISK)
        note = "Frequent missed" if missed > T.MISSED_PAYMENTS_HIGH_RISK else (
            "Some missed" if missed > 0 else "None missed"
        )
        tooltip = (
            f"Missed payment rate over 18M: {missed:.1f}%.\n"
            f"Thresholds: 0% = clean · ≤{T.MISSED_PAYMENTS_HIGH_RISK:.0f}% = some · >{T.MISSED_PAYMENTS_HIGH_RISK:.0f}% = frequent"
        )
        signals.append({"label": "Payments", "value": f"{missed:.0f}% missed", "rag": rag, "note": "18M window", "tooltip": tooltip})

    # 6. Adverse Events (forced event flags across all loan type vectors)
    all_flags = []
    for vec in bureau_report.feature_vectors.values():
        all_flags.extend(vec.forced_event_flags or [])
    if all_flags:
        high_adv = [f for f in all_flags if f in _ADVERSE_HIGH]
        mod_adv = [f for f in all_flags if f in _ADVERSE_MODERATE]
        unique_flags = sorted(set(all_flags))
        rag = "red" if high_adv else ("amber" if mod_adv else "neutral")
        tooltip = (
            f"Forced event flags: {', '.join(unique_flags)}.\n"
            f"High risk: WRF / SET / SMA · Moderate: SUB / DBT / LSS / WOF"
        )
        signals.append({
            "label": "Adverse Events",
            "value": ", ".join(unique_flags[:3]),
            "rag": rag,
            "note": "Forced events detected",
            "tooltip": tooltip,
        })

    # 7. Bureau FOIR (obligation-to-income ratio from bureau data)
    # Definition: aff_emi (total bureau EMI obligation) ÷ affluence_amt_6 (6M income estimate) × 100
    if tl and tl.foir is not None:
        foir_val = tl.foir
        rag = _rag(foir_val, green_max=40, amber_max=65)
        note = "Over-leveraged" if foir_val > 65 else ("Stretched" if foir_val > 40 else "Comfortable")
        aff_emi_str = f"INR {tl.aff_emi:,.0f}" if tl.aff_emi is not None else "N/A"
        aff_inc_str = f"INR {tl.affluence_amt:,.0f}" if tl.affluence_amt is not None else "N/A"
        unsec_str = f"\nFOIR (unsecured only): {tl.foir_unsec:.1f}%" if tl.foir_unsec is not None else ""
        tooltip = (
            f"Bureau obligation-to-income ratio.\n"
            f"Total EMI burden (aff_emi): {aff_emi_str}\n"
            f"Affluence income (6M estimate): {aff_inc_str}\n"
            f"FOIR = aff_emi ÷ affluence_amt × 100 = {foir_val:.1f}%{unsec_str}\n"
            f"Thresholds: ≤40% = comfortable · ≤65% = stretched · >65% = over-leveraged"
        )
        signals.append({
            "label": "FOIR",
            "value": f"{foir_val:.1f}%",
            "rag": rag,
            "note": note,
            "tooltip": tooltip,
        })

    # 8–9. Exposure Trend (12M point-in-time + 6M avg — each shown only if data available)
    signals.extend(_exposure_signals(getattr(bureau_report, "monthly_exposure", None)))

    return signals


def _derive_strengths_concerns(bureau_report, signals: list) -> tuple:
    """Derive strengths, concerns, verify from key_findings + signal list."""
    strengths, concerns, verify = [], [], []

    # From key findings (bureau)
    if bureau_report and bureau_report.key_findings:
        for f in bureau_report.key_findings:
            if f.severity == "positive" and len(strengths) < 3:
                strengths.append(f.finding)
            elif f.severity in ("high_risk", "moderate_risk") and len(concerns) < 3:
                concerns.append(f.finding)

    # From signal list (banking signals where key_findings not available)
    if not concerns:
        for s in signals:
            if s["rag"] == "red" and len(concerns) < 3:
                concerns.append(f"{s['label']}: {s['value']} ({s['note']})")
    if not strengths:
        for s in signals:
            if s["rag"] == "green" and len(strengths) < 3:
                strengths.append(f"{s['label']}: {s['value']}")

    # Verify items
    # Check FOIR signal
    for s in signals:
        if s["label"] == "FOIR" and s["rag"] in ("amber", "red"):
            verify.append("Cross-verify declared income vs salary deposits")
            break

    # EMI mismatch check
    if bureau_report and bureau_report.executive_inputs:
        live = bureau_report.executive_inputs.live_tradelines or 0
        # Count EMIs from banking if available
        if hasattr(bureau_report, "_banking_emi_count"):
            banking_emis = bureau_report._banking_emi_count
        else:
            banking_emis = None
        if live > 3 and banking_emis is not None and banking_emis < live - 1:
            verify.append(f"EMI mismatch: {live} live bureau tradelines vs {banking_emis} EMIs in banking")
        elif live > 4:
            verify.append(f"Verify all {live} live tradelines are reflected in banking obligations")

    # Forced events
    if bureau_report:
        all_flags = []
        for vec in bureau_report.feature_vectors.values():
            all_flags.extend(vec.forced_event_flags or [])
        high_adv = [f for f in all_flags if f in _ADVERSE_HIGH]
        if high_adv:
            verify.append(f"Resolve adverse event status: {', '.join(sorted(set(high_adv)))}")

    if not verify:
        verify.append("Confirm income source from employer or IT returns")

    return strengths[:3], concerns[:3], verify[:3]


def compute_scorecard(bureau_report=None) -> dict:
    """Compute a structured risk scorecard from available report data.

    Args:
        bureau_report: BureauReport or None

    Returns:
        dict with keys: verdict, verdict_rag, signals, strengths, concerns, verify, narrative
    """
    signals = []

    try:
        if bureau_report:
            signals.extend(_bureau_signals(bureau_report))
    except Exception as e:
        logger.warning("Bureau signal computation failed: %s", e)

    # Verdict from RED count
    red_count = sum(1 for s in signals if s["rag"] == "red")

    # Override: forced adverse events → always HIGH RISK
    forced_high = False
    if bureau_report:
        for vec in bureau_report.feature_vectors.values():
            if any(f in _ADVERSE_HIGH for f in (vec.forced_event_flags or [])):
                forced_high = True
                break

    if forced_high or red_count >= 3:
        verdict, verdict_rag = "HIGH RISK", "red"
    elif red_count >= 1:
        verdict, verdict_rag = "CAUTION", "amber"
    else:
        verdict, verdict_rag = "LOW RISK", "green"

    strengths, concerns, verify = _derive_strengths_concerns(bureau_report, signals)

    # Narrative: bureau narrative only. combined_summary injected by combined renderer.
    # customer_review is NOT included — it already appears as a separate section in the report.
    narrative = ""
    if bureau_report and bureau_report.narrative:
        narrative = bureau_report.narrative

    return {
        "verdict": verdict,
        "verdict_rag": verdict_rag,
        "signals": signals,
        "strengths": strengths,
        "concerns": concerns,
        "verify": verify,
        "narrative": narrative,
    }
