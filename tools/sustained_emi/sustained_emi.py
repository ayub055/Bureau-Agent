"""DuckDB-backed sustained-EMI calculation.

The logic lives verbatim in ``sustained_emi.sql`` (ported from Sustained_EMI.ipynb
cells 1-18). This module only marshals the local tradeline rows into a typed frame,
runs that SQL over them via DuckDB, and returns the per-CRN result.

Sustained EMI = the maximum total monthly EMI the customer has paid consecutively
for >= 6 months in the last 3 years (from the scrub date). Deterministic, no LLM,
fail-soft.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.extractors.bureau_feature_extractor import _load_bureau_data
from config.thresholds import SUSTAINED_EMI_TENOR_MONTHS

logger = logging.getLogger(__name__)

_SQL = Path(__file__).with_suffix(".sql").read_text()

# Columns the SQL base pull (cell 1) needs, grouped by target type.
_STR = ("crn", "report_month", "loan_status", "loan_type_new",
        "ownership_type", "sector", "dpd_string")
_NUM = ("sanction_amount", "out_standing_balance", "emi",
        "creditlimit", "high_credit_amount", "over_due_amount")
_DATE = ("date_opened", "date_closed", "last_payment_date",
         "pay_hist_start_date", "pay_hist_end_date")


def _prep(rows: list[dict]) -> pd.DataFrame:
    """Marshal raw string rows into a typed frame ('NULL' -> None, casts)."""
    df = pd.DataFrame(rows, columns=_STR + _NUM + _DATE).replace("NULL", None)
    for c in _NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in _DATE:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def _calculate_sustained_emi(crn, *, report_month=None, rows=None) -> dict:
    """Compute the sustained EMI for a CRN by running the SQL in DuckDB.

    Args:
        crn: customer reference number.
        report_month: restrict to one 'YYYYMM' snapshot; None -> all rows.
        rows: pre-loaded tradeline dicts (same shape as _load_bureau_data());
            None -> load the project's default bureau data. Lets tests/callers
            run the same logic over an alternate input file.

    Returns:
        {"crn", "sustained_emi", "sustained_emi_adj", "sustained_emi_bl",
         "sustained_emi_adj_bl", "max_cc_limit", "cc_income",
         "window_start", "window_end", "report_month"} or, on failure,
        {"crn", "sustained_emi": None, "error": ...}.
    """
    try:
        source = _load_bureau_data() if rows is None else rows
        crn_rows = [r for r in source
                    if str(r.get("crn")) == str(crn)
                    and (report_month is None or r.get("report_month") == report_month)]
        if not crn_rows:
            return {"crn": crn, "sustained_emi": None, "error": "no tradelines"}

        params = pd.DataFrame({"tenor_months": pd.Series([int(SUSTAINED_EMI_TENOR_MONTHS)],
                                                         dtype="int64")})
        con = duckdb.connect()
        con.register("tl_input", _prep(crn_rows))
        con.register("params_input", params)
        con.execute(_SQL)
        res = con.execute(
            "SELECT b.*, c.CC_INCOME "
            "FROM sc_buv2_tradeline_best_rolling_window b "
            "LEFT JOIN sc_buv2_tradeline_cc c ON b.crn = c.crn "
            "LIMIT 1"
        ).df()
        con.close()

        if res.empty:  # no eligible tradeline survived the filters
            return {"crn": crn, "sustained_emi": 0.0, "sustained_emi_adj": 0.0,
                    "sustained_emi_bl": 0.0, "sustained_emi_adj_bl": 0.0,
                    "max_cc_limit": 0.0, "cc_income": 0.0,
                    "window_start": None, "window_end": None, "report_month": report_month}

        res.columns = [c.lower() for c in res.columns]
        row = res.iloc[0]
        _f = lambda k: float(row[k]) if pd.notna(row.get(k)) else 0.0
        return {
            "crn": crn,
            "sustained_emi": _f("sustained_emi"),
            "sustained_emi_adj": _f("sustained_emi_adj"),
            "sustained_emi_bl": _f("sustained_emi_bl"),
            "sustained_emi_adj_bl": _f("sustained_emi_adj_bl"),
            "max_cc_limit": _f("max_cc_limit"),
            "cc_income": _f("cc_income"),
            "window_start": (str(row["window_start"]) if pd.notna(row.get("window_start")) else None),
            "window_end": (str(row["window_end"]) if pd.notna(row.get("window_end")) else None),
            "report_month": report_month,
        }
    except Exception as e:
        logger.warning(f"Sustained EMI calc failed for {crn}: {e}")
        return {"crn": crn, "sustained_emi": None, "error": str(e)}
