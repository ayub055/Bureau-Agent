#!/usr/bin/env python3
"""Batch-run the full Bureau Analyser pipeline over the renamed Shreyas XMLs, and
save each generated report back into the XML's own folder.

For every `*.xml` found (recursively) under the root folder, this runs the whole
project report generation exactly as the CLI does:

    run_bureau.py --xml <xml>   → convert XML → regenerate dpd_data.csv →
                                  derive CRN → build reports/bureau_analyser_<crn>_report.html
                                  (+ reports/excel/<crn>.xlsx)

Then it copies the HTML report (and the Excel) next to the input XML, named after the
input file — e.g. data/Shreyas_cases/CE1290/CE1290report.xml yields, in that same
folder, CE1290report.html and CE1290report.xlsx. Output names reuse the space-stripping
trick from rename_xml_spaces.py.

Each XML runs in its OWN fresh subprocess on purpose: the extractor caches the tradeline
rows in a module-level global, so a single long-lived process would reuse the first
customer's data for the rest. A new process per XML keeps them isolated.

Standalone — it does not modify any pipeline code; it just calls run_bureau.py.

Usage:
    python run_shreyas_reports.py                          # root = data/Shreyas_cases
    python run_shreyas_reports.py data/Shreyas_cases       # explicit root
    python run_shreyas_reports.py data/Shreyas_cases/CE1290  # one case folder
    python run_shreyas_reports.py --theme v2               # pass a theme through
    python run_shreyas_reports.py --dry-run                # just list what would run
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports"


def _rel(p: Path) -> str:
    """Path relative to the project root for tidy logs; full path if outside it."""
    try:
        return str(p.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(p)


def _nospace(name: str) -> str:
    """Same space-stripping trick as rename_xml_spaces.py."""
    return "".join(name.split())


def _crn_from_xml(xml: Path) -> int:
    """CRN the pipeline uses for this XML (same derivation as run_bureau --xml)."""
    from bureau_data_xml_converter import load_root, _pull_constants
    return int(_pull_constants(load_root(str(xml)))["crn"])


def _save_report_into_folder(xml: Path) -> list:
    """Copy the generated HTML (+ Excel) next to the XML, named after the input file
    (spaces stripped). Returns the destination paths actually written."""
    crn = _crn_from_xml(xml)
    stem = _nospace(xml.stem)
    written = []
    for src, dst in (
        (REPORTS_DIR / f"bureau_analyser_{crn}_report.html", xml.parent / f"{stem}.html"),
        (REPORTS_DIR / "excel" / f"{crn}.xlsx",              xml.parent / f"{stem}.xlsx"),
    ):
        if src.exists():
            shutil.copy2(src, dst)
            written.append(dst)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the report pipeline for every renamed Shreyas XML")
    ap.add_argument("root", nargs="?", default="data/Shreyas_cases",
                    help="Folder to scan recursively for *.xml (default: data/Shreyas_cases)")
    ap.add_argument("--theme", default=None, help="Report theme passed to run_bureau.py (e.g. v2/v3)")
    ap.add_argument("--dry-run", action="store_true", help="List the XMLs that would be processed, then exit")
    args = ap.parse_args()

    root = (PROJECT_ROOT / args.root) if not Path(args.root).is_absolute() else Path(args.root)
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    xmls = sorted(root.rglob("*.xml"))
    if not xmls:
        print(f"No .xml files found under {root}")
        return 0

    print(f"Found {len(xmls)} XML file(s) under {root}\n")
    ok, failed = [], []
    for i, xml in enumerate(xmls, 1):
        print(f"[{i}/{len(xmls)}] {_rel(xml)}")
        if args.dry_run:
            continue
        cmd = [sys.executable, "run_bureau.py", "--xml", str(xml)]
        if args.theme:
            cmd += ["--theme", args.theme]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)   # fresh process per XML

        if result.returncode != 0:
            failed.append(xml)
            continue
        try:
            for dst in _save_report_into_folder(xml):
                print(f"      saved → {_rel(dst)}")
            ok.append(xml)
        except Exception as e:                           # report built, but copy failed
            print(f"      report generated but saving into folder failed: {e}", file=sys.stderr)
            failed.append(xml)

    if args.dry_run:
        return 0

    print("\n" + "=" * 60)
    print(f"DONE — {len(ok)} succeeded, {len(failed)} failed")
    for xml in failed:
        print(f"  FAILED: {_rel(xml)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
