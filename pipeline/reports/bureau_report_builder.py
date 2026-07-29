"""Bureau report builder - deterministic data assembly without LLM.

Orchestrates feature extraction and aggregation to produce a BureauReport.
Parallel to customer_report_builder — NO LLM calls happen here.
"""

import logging
from datetime import datetime

from schemas.customer_report import ReportMeta
from schemas.bureau_report import BureauReport
from ..extractors.bureau_feature_extractor import extract_bureau_features, compute_monthly_exposure, extract_tu_score, extract_raw_loan_type_profile
from ..extractors.bureau_feature_aggregator import aggregate_bureau_features
from ..extractors.tradeline_feature_extractor import extract_tradeline_features
from .key_findings import extract_key_findings

logger = logging.getLogger(__name__)


def _validate_report(report: BureauReport) -> list[str]:
    """Run validation checks on the assembled report. Returns list of warnings."""
    warnings = []
    inputs = report.executive_inputs

    # Check: live + closed == total
    if inputs.live_tradelines + inputs.closed_tradelines != inputs.total_tradelines:
        warnings.append(
            f"Tradeline count mismatch: live({inputs.live_tradelines}) + "
            f"closed({inputs.closed_tradelines}) != total({inputs.total_tradelines})"
        )

    for loan_type, vec in report.feature_vectors.items():
        # Check: utilization only for CC
        if vec.utilization_ratio is not None and loan_type.name != "CC":
            warnings.append(f"Utilization ratio present for non-CC type: {loan_type.name}")

        # Check: no negative balances
        if vec.total_sanctioned_amount < 0:
            warnings.append(f"Negative sanctioned amount for {loan_type.name}")
        if vec.total_outstanding_amount < 0:
            warnings.append(f"Negative outstanding amount for {loan_type.name}")
        if vec.overdue_amount < 0:
            warnings.append(f"Negative overdue amount for {loan_type.name}")

    return warnings


def _compute_bl_sector_distribution(rows: list) -> dict:
    """Decide the FOIR-tile override and, when triggered, the sector breakdown.

    Trigger: more than ``T.BL_SECTOR_DIST_MIN_SHARE`` of ALL the customer's
    tradelines fall in the CMVL/CEL/AL/BL group (``T.BL_SECTOR_DIST_LOAN_TYPES`` —
    "BL" is used as an umbrella label for these commercial/business types). When
    triggered, compute the percentage distribution of the ``ownership_type`` column
    (Individual / Joint / Guarantor) pooled across that same group. Deterministic,
    no LLM.

    Returns a dict (see BureauReport.bl_sector_distribution). ``trigger`` is
    False when there are no tradelines or the group share is at/below the
    threshold. ``bl_count`` is the strict canonical business_loan count, kept
    for reference/audit; the trigger uses ``group_count``/``group_share``.
    """
    import config.thresholds as T
    from schemas.loan_type import normalize_loan_type

    total = len(rows)
    result = {"trigger": False, "group_share": 0.0, "group_count": 0,
              "bl_count": 0, "total": total,
              "title": "Sector distribution of BL (CMVL, CEL, AL, BL)",
              "distribution": []}
    if total == 0:
        return result

    canon = [normalize_loan_type(r.get("loan_type_new")).value for r in rows]
    result["bl_count"] = sum(1 for c in canon if c == "business_loan")

    # Count group membership and pool `ownership_type` values in one pass — the
    # trigger numerator and the distribution denominator are the same CMVL/CEL/AL/BL set.
    group_types = set(T.BL_SECTOR_DIST_LOAN_TYPES)
    counts: dict[str, int] = {}
    group_count = 0
    for row, c in zip(rows, canon):
        if c not in group_types:
            continue
        group_count += 1
        category = (row.get("ownership_type") or "").strip() or "Unknown"
        if category == "NULL":
            category = "Unknown"
        counts[category] = counts.get(category, 0) + 1

    result["group_count"] = group_count
    group_share = group_count / total
    result["group_share"] = round(group_share, 4)
    if group_count == 0 or group_share <= T.BL_SECTOR_DIST_MIN_SHARE:
        return result

    dist = [
        {"category": s, "count": n, "pct": round(100 * n / group_count, 1)}
        for s, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    result["trigger"] = True
    result["distribution"] = dist
    return result


def build_bureau_report(customer_id: int) -> BureauReport:
    """Build a bureau report by extracting and aggregating tradeline features.

    Steps:
        1. Extract per-loan-type feature vectors from raw bureau data
        2. Aggregate vectors into executive summary inputs
        3. Assemble and validate the BureauReport

    Args:
        customer_id: The CRN (customer reference number) from bureau data.

    Returns:
        BureauReport with feature vectors and executive inputs populated.
        Narrative field is left as None — populated downstream by LLM narration.
    """
    # 1. Feature extraction
    feature_vectors = extract_bureau_features(customer_id)

    if not feature_vectors:
        logger.warning(f"No bureau tradelines found for customer {customer_id}")

    # 2. Feature aggregation
    executive_inputs = aggregate_bureau_features(feature_vectors)
    executive_inputs.tu_score = extract_tu_score(customer_id)

    # 2b. Tradeline feature extraction (pre-computed, fail-soft)
    tradeline_features = None
    try:
        tradeline_features = extract_tradeline_features(customer_id)
    except Exception as e:
        logger.warning(f"Tradeline feature extraction failed for {customer_id}: {e}")

    # ratio_good_closed_pl is a warehouse-join field the generation script omits —
    # derive it from the raw tradelines when the source value is missing (fail-soft).
    if tradeline_features is not None and tradeline_features.ratio_good_closed_pl is None:
        try:
            from ..extractors.bureau_feature_extractor import compute_ratio_good_closed_pl
            tradeline_features.ratio_good_closed_pl = compute_ratio_good_closed_pl(customer_id)
        except Exception as e:
            logger.warning(f"ratio_good_closed_pl computation failed for {customer_id}: {e}")

    # 3. Build meta
    meta = ReportMeta(
        customer_id=customer_id,
        generated_at=datetime.now().isoformat(),
        analysis_period="Bureau tradeline history",
        currency="INR",
        transaction_count=executive_inputs.total_tradelines,
    )

    # 4. Key findings (deterministic, fail-soft)
    key_findings = []
    try:
        key_findings = extract_key_findings(
            executive_inputs, feature_vectors, tradeline_features
        )
    except Exception as e:
        logger.warning(f"Key findings extraction failed for {customer_id}: {e}")

    # 4b. Monthly exposure timeseries (fail-soft)
    monthly_exposure = None
    try:
        monthly_exposure = compute_monthly_exposure(customer_id)
    except Exception as e:
        logger.warning(f"Monthly exposure computation failed for {customer_id}: {e}")

    # 4c. Raw loan type profile for persona classification (fail-soft)
    raw_loan_profile = None
    try:
        raw_loan_profile = extract_raw_loan_type_profile(customer_id)
    except Exception as e:
        logger.warning(f"Raw loan type profile extraction failed for {customer_id}: {e}")

    # 4d. Bureau income — deterministic DuckDB-wrapped affluence SQL (fail-soft)
    bureau_income = None
    try:
        from tools.bureau_income import _calculate_bureau_income
        bureau_income = _calculate_bureau_income(customer_id)
    except Exception as e:
        logger.warning(f"Bureau income computation failed for {customer_id}: {e}")

    # 4e. Sustained EMI — deterministic DuckDB-wrapped SQL (fail-soft)
    sustained_emi = None
    try:
        from tools.sustained_emi import _calculate_sustained_emi
        sustained_emi = _calculate_sustained_emi(customer_id)
    except Exception as e:
        logger.warning(f"Sustained EMI computation failed for {customer_id}: {e}")

    # 4f. Bureau obligation — deterministic DuckDB-wrapped SQL (fail-soft)
    obligation = None
    try:
        from tools.obligation import _calculate_obligation
        obligation = _calculate_obligation(customer_id)
    except Exception as e:
        logger.warning(f"Bureau obligation computation failed for {customer_id}: {e}")

    # 4h. Business throughput (Wheel-LOS turnover) — reuses bureau_turnover, fail-soft
    business_throughput = None
    try:
        from bureau_turnover import compute_turnover
        from pipeline.extractors.bureau_feature_extractor import _load_bureau_data, _safe_int
        cid = int(customer_id)
        rows = [r for r in _load_bureau_data() if _safe_int(r.get("crn", "")) == cid]
        business_throughput = compute_turnover(rows)
    except Exception as e:
        logger.warning(f"Business throughput computation failed for {customer_id}: {e}")

    # 4i. FOIR-tile BL sector-distribution override (deterministic, fail-soft).
    # When the book is BL-heavy the FOIR KPI tile is replaced by a `sector`
    # breakdown across CMVL/CEL/AL/BL tradelines (see _compute_bl_sector_distribution).
    bl_sector_distribution = None
    try:
        from pipeline.extractors.bureau_feature_extractor import _load_bureau_data, _safe_int
        cid = int(customer_id)
        _rows = [r for r in _load_bureau_data() if _safe_int(r.get("crn", "")) == cid]
        bl_sector_distribution = _compute_bl_sector_distribution(_rows)
    except Exception as e:
        logger.warning(f"BL sector distribution computation failed for {customer_id}: {e}")

    # 4g. Bureau FOIR from the deterministic modules: Bureau Obligation ÷ Bureau Income.
    # Overrides the pre-computed tl_features FOIR so the report's Income, Obligation and
    # FOIR are mutually consistent (the tile shows module Income/Obligation, so FOIR must
    # be computed from the same two numbers). Fail-soft: if either module is missing or
    # income is non-positive, the tl_features FOIR values are left untouched.
    try:
        _inc = (bureau_income or {}).get("bureau_income")
        _aff = (obligation or {}).get("aff_emi")
        _uns = (obligation or {}).get("emi_unsec")
        if tradeline_features is not None and _inc and _inc > 0 and _aff is not None:
            tradeline_features.aff_emi = round(_aff, 2)
            tradeline_features.unsecured_emi = (round(_uns, 2) if _uns is not None else None)
            tradeline_features.affluence_amt = round(_inc, 2)
            tradeline_features.foir = round(_aff / _inc * 100, 1)
            tradeline_features.foir_unsec = (round(_uns / _inc * 100, 1) if _uns is not None else None)
    except Exception as e:
        logger.warning(f"FOIR override from bureau modules failed for {customer_id}: {e}")

    # 5. Assemble report
    report = BureauReport(
        meta=meta,
        feature_vectors=feature_vectors,
        executive_inputs=executive_inputs,
        tradeline_features=tradeline_features,
        key_findings=key_findings,
        monthly_exposure=monthly_exposure,
        raw_loan_profile=raw_loan_profile,
        bureau_income=bureau_income,
        sustained_emi=sustained_emi,
        obligation=obligation,
        business_throughput=business_throughput,
        bl_sector_distribution=bl_sector_distribution,
    )

    # 6. Validate (fail-soft: log warnings, return partial report)
    warnings = _validate_report(report)
    for w in warnings:
        logger.warning(f"Bureau report validation [{customer_id}]: {w}")

    return report
