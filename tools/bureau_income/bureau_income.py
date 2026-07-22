"""DuckDB-backed bureau-income calculation.

The affluence logic lives verbatim in ``bureau_income.sql`` (ported from
Bureau.ipynb cells 1-28). This module only marshals the local tradeline rows
into a typed frame, runs that SQL over them via DuckDB, and returns the per-CRN
result. Deterministic, no LLM, fail-soft.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.extractors.bureau_feature_extractor import _load_bureau_data

logger = logging.getLogger(__name__)

_SQL = Path(__file__).with_suffix(".sql").read_text()

# Columns the SQL base pull (cell 1) needs, grouped by target type.
_STR = ("crn", "report_month", "loan_status", "loan_type_new",
        "ownership_type", "sector", "dpd_string")
_NUM = ("sanction_amount", "high_credit_amount", "creditlimit", "over_due_amount")
_DATE = ("date_opened", "date_closed", "pay_hist_start_date")

# sc_bu_Affluence2 columns -> output keys (lower-cased for engine-agnostic lookup).
_COMPONENTS = {
    "max_hl": "max_hl", "max_al1": "max_al", "max_pl": "max_pl",
    "max_bl1": "max_bl", "max_lap1": "max_lap", "max_cc_cl": "max_cc_cl",
    "max_cc_hca": "max_cc_hca", "max_cvce": "max_cvce", "max_ltp": "max_ltp",
    "max_affl7": "max_affl7", "max_bureau_income": "max_bureau_income",
}


def _prep(rows: list[dict]) -> pd.DataFrame:
    """Marshal raw string rows into a typed frame ('NULL' -> None, casts)."""
    df = pd.DataFrame(rows, columns=_STR + _NUM + _DATE).replace("NULL", None)
    for c in _NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in _DATE:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def _calculate_bureau_income(crn, *, occupation=None, report_month=None, rows=None) -> dict:
    """Compute the bureau income for a CRN by running the affluence SQL in DuckDB.

    Args:
        crn: customer reference number.
        occupation: occupation code; 'S'/'SPRS'/'SGC'/'SPC' mark self-employed
            (zeroes Business/Property-Loan income). None -> non-self-employed.
        report_month: restrict to one 'YYYYMM' snapshot; None -> all rows.
        rows: pre-loaded tradeline dicts (same shape as _load_bureau_data());
            None -> load the project's default bureau data. Lets tests/callers
            run the same logic over an alternate input file.

    Returns:
        {"crn", "bureau_income" (MAX_AFFL_INFL_ROLL), "stamp_loan", "semp_flag",
         "report_month", "components": {...}} or, on failure,
        {"crn", "bureau_income": None, "error": ...}.
    """
    try:
        source = _load_bureau_data() if rows is None else rows
        crn_rows = [r for r in source
                    if str(r.get("crn")) == str(crn)
                    and (report_month is None or r.get("report_month") == report_month)]
        if not crn_rows:
            return {"crn": crn, "bureau_income": None, "error": "no tradelines"}

        # Explicit string dtype so an all-null occupation stays VARCHAR (else DuckDB
        # infers INT and `occupation IN ('S',...)` fails casting the literals).
        occ = pd.DataFrame({"crn": pd.Series([str(crn)], dtype="string"),
                            "occupation": pd.Series([occupation], dtype="string")})
        con = duckdb.connect()
        con.register("tl_input", _prep(crn_rows))
        con.register("occupation_input", occ)
        con.execute(_SQL)
        res = con.execute("SELECT * FROM sc_bu_Affluence2 LIMIT 1").df()
        con.close()

        if res.empty:  # no qualifying tradeline survived the filters
            return {"crn": crn, "bureau_income": 0.0, "stamp_loan": "NA",
                    "semp_flag": 0, "report_month": report_month, "components": {}}

        res.columns = [c.lower() for c in res.columns]
        row = res.iloc[0]
        _f = lambda k: float(row[k]) if pd.notna(row.get(k)) else 0.0
        return {
            "crn": crn,
            "bureau_income": _f("max_affl_infl_roll"),
            "stamp_loan": row["stamp_loan"],
            "semp_flag": int(row["semp_flag1"] or 0),
            "report_month": report_month,
            "components": {out: _f(src) for src, out in _COMPONENTS.items()},
        }
    except Exception as e:
        logger.warning(f"Bureau income calc failed for {crn}: {e}")
        return {"crn": crn, "bureau_income": None, "error": str(e)}
