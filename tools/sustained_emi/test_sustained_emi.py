"""Validation suite for `_calculate_sustained_emi`.

Runs the real calculator over a caller-supplied tradeline data file and checks its
output against a ground-truth file, per CRN.

Inputs
------
--data      Tradeline rows the code needs: same schema as `dpd_data.csv` (lowercase
            headers, literal 'NULL' for missing). Default: the configured bureau file.
--expected  Ground truth. Columns: `crn` + any of `sustained_emi`, `cc_income`
            (each compared numerically when present). Default: `sample_expected.csv`.

Comparison
----------
Each metric column present in the expected file is compared numerically, within
`--tol` (abs) / 1e-4 (rel).

Usage
-----
    python -m tools.sustained_emi.test_sustained_emi \
        --data tradelines.tsv --expected expected.csv [--delimiter $'\t'] [--tol 1.0]

Exit code is 0 when every CRN passes, 1 otherwise.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

from config.settings import BUREAU_DPD_FILE, BUREAU_DPD_DELIMITER
from .sustained_emi import _calculate_sustained_emi

_DEFAULT_EXPECTED = Path(__file__).with_name("sample_expected.csv")
_METRICS = ("sustained_emi", "cc_income")


def _read_records(path, delimiter):
    """Read a delimited file into row dicts, parsed exactly like the data loader."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [{(k.strip().lower() if k else k): v for k, v in row.items()}
                for row in reader]


def run_suite(data_file, expected_file, *, delimiter="\t", tol=1.0):
    """Return (results, passed) where results is a list of per-CRN dicts."""
    rows = _read_records(data_file, delimiter)
    results, passed = [], 0
    for e in _read_records(expected_file, ","):
        crn = str(e["crn"])
        out = _calculate_sustained_emi(crn, rows=rows)
        checks, ok = [], True
        for m in _METRICS:
            raw = e.get(m)
            if raw in (None, ""):
                continue  # metric not asserted for this file
            exp = float(raw) if raw != "NULL" else 0.0
            got = out.get(m)
            good = got is not None and math.isclose(got, exp, rel_tol=1e-4, abs_tol=tol)
            ok = ok and good
            checks.append((m, exp, got, good))
        passed += ok
        results.append({"crn": crn, "checks": checks, "ok": ok, "error": out.get("error")})
    return results, passed


def _print_report(results, passed):
    for r in results:
        cells = " · ".join(
            f"{m}: exp {exp:,.2f} / got {('%.2f' % got) if got is not None else 'None'}"
            f"{'' if good else ' ✗'}"
            for m, exp, got, good in r["checks"]) or "(no metrics asserted)"
        note = "" if r["ok"] else f"  <-- {r['error'] or 'MISMATCH'}"
        print(f"{r['crn']:<14}{'PASS' if r['ok'] else 'FAIL':<6}{cells}{note}")
    print("-" * 90)
    print(f"{passed}/{len(results)} passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate sustained EMI against ground truth.")
    ap.add_argument("--data", default=BUREAU_DPD_FILE, help="tradeline data file")
    ap.add_argument("--expected", default=str(_DEFAULT_EXPECTED), help="crn[,sustained_emi][,cc_income]")
    ap.add_argument("--delimiter", default=BUREAU_DPD_DELIMITER, help="data file delimiter (default: tab)")
    ap.add_argument("--tol", type=float, default=1.0, help="absolute tolerance")
    a = ap.parse_args(argv)

    results, passed = run_suite(a.data, a.expected, delimiter=a.delimiter, tol=a.tol)
    _print_report(results, passed)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
