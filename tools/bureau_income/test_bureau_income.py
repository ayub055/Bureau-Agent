"""Validation suite for `_calculate_bureau_income`.

Runs the real calculator over a caller-supplied tradeline data file and checks
its output against a ground-truth file, per CRN.

Inputs
------
--data      Tradeline rows the code needs: same schema as `dpd_data.csv`
            (>= the 14 base columns, lowercase headers, literal 'NULL' for
            missing). An optional `occupation` column is passed through per CRN.
            Default: the project's configured bureau data file.
--expected  Ground truth, columns: `crn, bureau_income, stamp_loan`.
            Default: `sample_expected.csv` next to this file.

Comparison
----------
bureau_income : numeric, within `--tol` (abs) / 1e-4 (rel).
stamp_loan    : exact string match (skipped if blank in the ground truth).

Usage
-----
    python -m tools.bureau_income.test_bureau_income \
        --data tradelines.tsv --expected expected.csv [--delimiter $'\t'] [--tol 1.0]

Exit code is 0 when every CRN passes, 1 otherwise.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

from config.settings import BUREAU_DPD_FILE, BUREAU_DPD_DELIMITER
from .bureau_income import _calculate_bureau_income

_DEFAULT_EXPECTED = Path(__file__).with_name("sample_expected.csv")


def _read_records(path, delimiter):
    """Read a delimited file into row dicts, parsed exactly like the data loader
    (csv.DictReader: raw strings, literal 'NULL' kept, trailing delimiter tolerated)."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [{(k.strip().lower() if k else k): v for k, v in row.items()}
                for row in reader]


def run_suite(data_file, expected_file, *, delimiter="\t", tol=1.0):
    """Return (results, passed) where results is a list of per-CRN dicts."""
    rows = _read_records(data_file, delimiter)

    # Per-CRN occupation, if the data file carries it (first non-null wins).
    occ_by_crn = {}
    if rows and "occupation" in rows[0]:
        for r in rows:
            c, v = str(r["crn"]), r.get("occupation")
            if c not in occ_by_crn and v not in (None, "", "NULL"):
                occ_by_crn[c] = v

    results, passed = [], 0
    for e in _read_records(expected_file, ","):
        crn = str(e["crn"])
        raw = e.get("bureau_income", "")
        exp_income = float(raw) if raw not in ("", "NULL", None) else 0.0
        exp_stamp = (e.get("stamp_loan") or "").strip()

        out = _calculate_bureau_income(crn, occupation=occ_by_crn.get(crn), rows=rows)
        got_income = out.get("bureau_income")
        got_stamp = (out.get("stamp_loan") or "").strip()

        income_ok = got_income is not None and math.isclose(
            got_income, exp_income, rel_tol=1e-4, abs_tol=tol)
        stamp_ok = (got_stamp == exp_stamp) if exp_stamp else True
        ok = income_ok and stamp_ok
        passed += ok
        results.append({
            "crn": crn, "exp_income": exp_income, "got_income": got_income,
            "income_ok": income_ok, "exp_stamp": exp_stamp, "got_stamp": got_stamp,
            "stamp_ok": stamp_ok, "ok": ok, "error": out.get("error"),
        })
    return results, passed


def _print_report(results, passed):
    print(f"{'CRN':<14}{'expected':>13}{'got':>13}  {'exp_stamp':<18}{'got_stamp':<18}result")
    print("-" * 90)
    for r in results:
        got = f"{r['got_income']:.2f}" if r["got_income"] is not None else "None"
        note = "" if r["ok"] else f"  <-- {r['error'] or 'MISMATCH'}"
        print(f"{r['crn']:<14}{r['exp_income']:>13.2f}{got:>13}  "
              f"{r['exp_stamp']:<18}{r['got_stamp']:<18}{'PASS' if r['ok'] else 'FAIL'}{note}")
    print("-" * 90)
    print(f"{passed}/{len(results)} passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate bureau income against ground truth.")
    ap.add_argument("--data", default=BUREAU_DPD_FILE, help="tradeline data file")
    ap.add_argument("--expected", default=str(_DEFAULT_EXPECTED), help="crn,bureau_income,stamp_loan")
    ap.add_argument("--delimiter", default=BUREAU_DPD_DELIMITER, help="data file delimiter (default: tab)")
    ap.add_argument("--tol", type=float, default=1.0, help="absolute income tolerance")
    a = ap.parse_args(argv)

    results, passed = run_suite(a.data, a.expected, delimiter=a.delimiter, tol=a.tol)
    _print_report(results, passed)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
