#!/usr/bin/env python3
"""Bureau Turnover estimator — self-contained, stdlib only, no project imports.

Reads a scrub.csv (one row per tradeline) and prints, per customer (crn), an
estimated business turnover and its bracket, following the Wheel-LOS method:

  eligible trades -> size by vintage -> product multiplier -> role weight ->
  descending rank-weighted sum -> bracket.

Date/DPD handling mirrors bureau_data_report_creation.py (plain Python, not imported):
  * scrub_date = first-of-report_month minus 1 day (the "as of" cut-off).
  * dpd_string is 3 chars per month, chunk 0 = the most recent reported month
    (= month of min(pay_hist_start_date, scrub_date)); STD/XXX/000 = clean.
  * "current + last 12 months DPD" is anchored to scrub_date (calendar months), so a
    loan closed years ago is judged clean on the recent window, not its whole history.

Usage:  python bureau_turnover.py [path/to/scrub.csv]   (default: data/scrub.csv)
"""
import csv
import sys
from datetime import date, timedelta

# ── loan_type_new -> (category, multiplier). Anything not listed is EXCLUDED. ──
LOAN_MULTIPLIER = {
    # Business Loan — 3.5×
    "Business Loan - General": ("BL", 3.5),
    "Business Loan - Secured": ("BL", 3.5),
    "Business Loan - Unsecured": ("BL", 3.5),
    "Business Loan - Priority Sector - Agriculture": ("BL", 3.5),
    "Business Loan - Priority Sector - Others": ("BL", 3.5),
    "Business Loan - Priority Sector - Small Business": ("BL", 3.5),
    "Business Loan Against Bank Deposits": ("BL", 3.5),
    "Business Non-Funded Credit Facility - General": ("BL", 3.5),
    "Business Non-Funded Credit Facility - Priority Sector-Others": ("BL", 3.5),
    "Business Non-Funded Credit Facility - Priority Sector - Agriculture": ("BL", 3.5),
    "Business Non-Funded Credit Facility - Priority Sector - Small Business": ("BL", 3.5),
    # Commercial Vehicle / LCV / HCV — 3.0×
    "Commercial Vehicle Loan": ("CMVL", 3.0),
    "Tractor Loan": ("CMVL", 3.0),
    "P2P Auto Loan": ("CMVL", 3.0),
    # Auto (incl. Personal / Used Car) — 3.0×
    "Auto Loan (Personal)": ("AL", 3.0),
    "Auto Loan": ("AL", 3.0),
    "Used Car Loan": ("AL", 3.0),
    # Construction / Commercial Equipment — 2.5×
    "Construction Equipment Loan": ("CEL", 2.5),
    # Loan to Professional — 2.5×
    "Loan to Professional": ("LTP", 2.5),
}

_DPD_CLEAN = {"STD", "XXX", "ASSET", "000", ""}     # non-delinquent chunk codes
_AGE_BANDS = ((1, 1.00), (3, 0.85), (5, 0.70))      # (upper-year, factor); else 0.55


# ── tolerant parsers ──────────────────────────────────────────────────────────
def _num(x):
    x = (x or "").strip()
    try:
        return float(x) if x and x.upper() != "NULL" else 0.0
    except ValueError:
        return 0.0


def _date(x):
    x = (x or "").strip()
    try:
        return date.fromisoformat(x[:10]) if x and x.upper() != "NULL" else None
    except ValueError:
        return None


def _midx(d):
    """Absolute month index (year*12 + month) for cheap month arithmetic."""
    return d.year * 12 + d.month - 1


# ── report-mirrored helpers ───────────────────────────────────────────────────
def scrub_date(report_month):
    """First day of report_month minus 1 day (= last day of the prior month)."""
    rm = (report_month or "").strip()
    return date(int(rm[:4]), int(rm[4:6]), 1) - timedelta(days=1)


def minus_years(d, yrs):
    try:
        return d.replace(year=d.year - yrs)
    except ValueError:                              # Feb 29 → Feb 28
        return d.replace(year=d.year - yrs, day=28)


def dpd_clean(dpd_string, pay_hist_start, scrub, months=13):
    """True if no days-past-due in the current + last 12 CALENDAR months (relative to
    scrub). Chunk 0 = most recent reported month = month of min(pay_hist_start, scrub);
    each chunk maps to a calendar month, so long-closed loans are judged only on the
    recent window. STD/XXX/000/blank = clean; numeric>0 or adverse code = delinquent."""
    if not dpd_string:
        return True
    anchor = _midx(min(pay_hist_start, scrub) if pay_hist_start else scrub)
    cur, n = _midx(scrub), len(dpd_string) // 3
    for k in range(months):                         # current, then 12 prior months
        off = anchor - (cur - k)                     # chunk index for that month
        if 0 <= off < n:
            c = dpd_string[off * 3:off * 3 + 3].strip().upper()
            if c in _DPD_CLEAN:
                continue
            if not c.isdigit() or int(c) > 0:        # adverse code, or DPD days > 0
                return False
    return True


def age_factor(age_years):
    for upper, factor in _AGE_BANDS:
        if age_years < upper:
            return factor
    return 0.55


def role_wt(ownership_type):
    return 1.00 if (ownership_type or "").strip().lower() in ("individual", "proprietor") else 0.50


def bracket(t):
    for cap, name in ((25e5, "B1 – Micro"), (1e7, "B2 – Small"),
                      (5e7, "B3 – Lower-Mid"), (25e7, "B4 – Mid")):
        if t < cap:
            return name
    return "B5 – Large"


def _inr(x):
    if x >= 1e7:
        return f"₹{x / 1e7:.2f}Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.2f}L"
    return f"₹{x:,.0f}"


# ── core ──────────────────────────────────────────────────────────────────────
def load_rows(path):
    """Read scrub.csv; drop exact-duplicate rows (identical incl. CV_RN = true
    duplicate reporting; a distinct CV_RN keeps the trade separate)."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen, unique = set(), []
    for r in rows:
        key = tuple(r.values())                     # DictReader keeps column order
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def build_trades(rows):
    """Return (eligible trades, dropped-reason list) for one customer."""
    trades, dropped = [], []
    for r in rows:
        cm = LOAN_MULTIPLIER.get((r.get("loan_type_new") or "").strip())
        if cm is None:
            dropped.append("type not eligible"); continue
        category, mult = cm

        d_open = _date(r.get("date_opened"))
        if d_open is None:
            dropped.append("no date_opened"); continue
        sd = scrub_date(r.get("report_month"))

        if not dpd_clean(r.get("dpd_string"), _date(r.get("pay_hist_start_date")), sd):
            dropped.append("DPD in last 12m"); continue

        days = (sd - d_open).days
        if days / 30.5 < 6:                           # MOB gate, report's /30.5 month measure
            dropped.append("MOB < 6m"); continue

        live = (r.get("loan_status") or "").strip().lower() == "live"
        if not live:
            d_close = _date(r.get("date_closed"))
            if d_close is None or d_close < minus_years(sd, 5):
                dropped.append("closed > 60m ago / not live"); continue

        af = age_factor(days / 365.25)               # vintage in calendar years
        base = max(_num(r.get("sanction_amount")) * af, _num(r.get("out_standing_balance")))
        trades.append({
            "cat": category, "lt": (r.get("loan_type_new") or "").strip(),
            "opened": d_open, "live": live, "own": (r.get("ownership_type") or "").strip(),
            "mult": mult, "base": base,
            "value": base * mult * role_wt(r.get("ownership_type")),
        })
    return trades, dropped


def _turnover(trades):
    """Descending rank-weighted sum: rank i (1=largest) → weight (N−i+1)/N."""
    vals = sorted((t["value"] for t in trades), reverse=True)
    n = len(vals)
    return sum(v * (n - i) / n for i, v in enumerate(vals)) if n else 0.0


def compute_turnover(rows):
    """Turnover over an already-distinct set of tradeline dict rows (no dedup — the
    caller supplies the canonical set, e.g. de-duplicated dpd_data rows). Returns
    {"turnover", "turnover_disp", "bracket", "eligible"}. Safe on 0 eligible trades."""
    trades, _ = build_trades(rows)
    t = _turnover(trades)
    return {"turnover": t, "turnover_disp": _inr(t),
            "bracket": bracket(t), "eligible": len(trades)}


def report(rows):
    by_crn = {}
    for r in rows:
        by_crn.setdefault((r.get("crn") or "").strip(), []).append(r)

    for crn, crows in by_crn.items():
        trades, dropped = build_trades(crows)
        ranked = sorted(trades, key=lambda t: t["value"], reverse=True)
        n = len(ranked)
        turnover = _turnover(ranked)

        print("=" * 78)
        print(f"CRN {crn}   |   trades in file: {len(crows)}   |   eligible: {n}")
        print("-" * 78)
        if ranked:
            print(f"{'#':>2} {'type':<26}{'opened':<11}{'st':<5}{'role':<10}"
                  f"{'base':>12}{'x':>5}{'value':>13}{'rk_wt':>7}")
            for i, t in enumerate(ranked):
                print(f"{i + 1:>2} {t['cat'] + ' ' + t['lt'][:20]:<26}{t['opened'].isoformat():<11}"
                      f"{('Live' if t['live'] else 'Cls'):<5}{t['own'][:9]:<10}"
                      f"{_inr(t['base']):>12}{t['mult']:>5.1f}{_inr(t['value']):>13}{(n - i) / n:>7.3f}")
        print("-" * 78)
        print(f"  Estimated Turnover : {_inr(turnover)}   ({turnover:,.0f})")
        print(f"  Bracket            : {bracket(turnover)}")
        if dropped:
            from collections import Counter
            print(f"  Excluded trades    : {len(dropped)}  "
                  + " · ".join(f"{r}={c}" for r, c in Counter(dropped).most_common()))
        print("=" * 78)


def main():
    report(load_rows(sys.argv[1] if len(sys.argv) > 1 else "data/scrub.csv"))


if __name__ == "__main__":
    main()
