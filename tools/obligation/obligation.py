"""DuckDB-backed bureau-obligation calculation.

The logic lives verbatim in ``obligation.sql`` (ported from the internal Redshift
procedure pt1.sql + pt2.sql / sp_bureau_obligation_split1). This module only marshals
the local tradeline rows into a typed frame, runs that SQL over them via DuckDB, and
returns the per-CRN result.

Bureau obligation = the customer's total monthly EMI obligation across all bureau
tradelines, using loan-type-specific EMI rate bands + credit-risk filters. Output is
one row per CRN with five figures (aff_emi / emi_unsec / aff_emi_topup /
emi_unsec_topup / current_emi). Deterministic, no LLM, fail-soft.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.extractors.bureau_feature_extractor import _load_bureau_data
from config.thresholds import OBLIGATION_TENOR_MONTHS

logger = logging.getLogger(__name__)

_SQL = Path(__file__).with_suffix(".sql").read_text()

# Columns the SQL base pull needs, grouped by target type.
_STR = ("crn", "report_month", "loan_status", "loan_type_new",
        "ownership_type", "sector")
_NUM = ("sanction_amount", "out_standing_balance", "emi", "high_credit_amount")
_DATE = ("date_opened", "date_closed", "pay_hist_end_date")


def _prep(rows: list[dict]) -> pd.DataFrame:
    """Marshal raw string rows into a typed frame ('NULL' -> None, casts)."""
    df = pd.DataFrame(rows, columns=_STR + _NUM + _DATE).replace("NULL", None)
    for c in _NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in _DATE:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def _calculate_obligation(crn, *, report_month=None, rows=None) -> dict:
    """Compute the bureau obligation for a CRN by running the SQL in DuckDB.

    Args:
        crn: customer reference number.
        report_month: restrict to one 'YYYYMM' snapshot; None -> all rows.
        rows: pre-loaded tradeline dicts (same shape as _load_bureau_data());
            None -> load the project's default bureau data. Lets tests/callers
            run the same logic over an alternate input file.

    Returns:
        {"crn", "obligation" (== aff_emi), "aff_emi", "emi_unsec", "aff_emi_topup",
         "emi_unsec_topup", "current_emi", "report_month"} or, on failure,
        {"crn", "obligation": None, "error": ...}.
    """
    try:
        source = _load_bureau_data() if rows is None else rows
        crn_rows = [r for r in source
                    if str(r.get("crn")) == str(crn)
                    and (report_month is None or r.get("report_month") == report_month)]
        if not crn_rows:
            return {"crn": crn, "obligation": None, "error": "no tradelines"}

        # None -> inject SQL NULL so every row takes the `tenor IS NULL -> remain_tenor=0`
        # branch (faithful to the source's missing-tenor handling; data has no `tenor`).
        params = pd.DataFrame({"tenor_months": pd.array([OBLIGATION_TENOR_MONTHS], dtype="Int64")})
        con = duckdb.connect()
        con.register("tl_input", _prep(crn_rows))
        con.register("params_input", params)
        con.execute(_SQL)
        res = con.execute(
            "SELECT * FROM sc_obligation_final ORDER BY report_month DESC LIMIT 1"
        ).df()
        con.close()

        if res.empty:  # no eligible tradeline survived the filters
            return {"crn": crn, "obligation": 0.0, "aff_emi": 0.0, "emi_unsec": 0.0,
                    "aff_emi_topup": 0.0, "emi_unsec_topup": 0.0, "current_emi": 0.0,
                    "report_month": report_month}

        res.columns = [c.lower() for c in res.columns]
        row = res.iloc[0]
        _f = lambda k: float(row[k]) if pd.notna(row.get(k)) else 0.0
        return {
            "crn": crn,
            "obligation": _f("aff_emi"),
            "aff_emi": _f("aff_emi"),
            "emi_unsec": _f("emi_unsec"),
            "aff_emi_topup": _f("aff_emi_topup"),
            "emi_unsec_topup": _f("emi_unsec_topup"),
            "current_emi": _f("current_emi"),
            "report_month": report_month,
        }
    except Exception as e:
        logger.warning(f"Bureau obligation calc failed for {crn}: {e}")
        return {"crn": crn, "obligation": None, "error": str(e)}
