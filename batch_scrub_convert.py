#!/usr/bin/env python3
"""Batch sibling of bureau_data_xml_converter.py.

Runs the XML → CSV conversion for every `*.xml` found (recursively) under a folder
tree, and writes each result into a master `scrub_data` folder that MIRRORS the input
folder layout. For input  <root>/<sub…>/<name>.xml  it writes:

    <scrub_data>/<sub…>/<name>_scrub.csv
    <scrub_data>/<sub…>/<name>_enq.csv

e.g.  data/Shreyas_cases/CE1290/CE1290report.xml
      → scrub_data/CE1290/CE1290report_scrub.csv  (+ _enq.csv)

Reuses bureau_data_xml_converter.convert() verbatim — it changes no pipeline code and
does NOT touch data/dpd_data.csv (this is only the raw XML→CSV extract step, archived
per case). Output file names use the space-stripping trick from rename_xml_spaces.py.

Usage:
    python batch_scrub_convert.py                                # root=data/Shreyas_cases, out=scrub_data
    python batch_scrub_convert.py data/Shreyas_cases            # explicit input root
    python batch_scrub_convert.py data/Shreyas_cases scrub_data # explicit input root + master folder
    python batch_scrub_convert.py --dry-run                     # list planned conversions only
"""
import argparse
import sys
from pathlib import Path

from bureau_data_xml_converter import convert

PROJECT_ROOT = Path(__file__).resolve().parent


def _nospace(name: str) -> str:
    """Same space-stripping trick as rename_xml_spaces.py."""
    return "".join(name.split())


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (PROJECT_ROOT / q)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert every XML in a folder tree to scrub/enq CSVs, mirrored under a master folder")
    ap.add_argument("root", nargs="?", default="data/Shreyas_cases",
                    help="Folder scanned recursively for *.xml (default: data/Shreyas_cases)")
    ap.add_argument("out", nargs="?", default="scrub_data",
                    help="Master output folder mirroring the input layout (default: scrub_data)")
    ap.add_argument("--dry-run", action="store_true", help="List planned conversions, then exit")
    args = ap.parse_args()

    root = _resolve(args.root)
    out_root = _resolve(args.out)
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    xmls = sorted(root.rglob("*.xml"))
    if not xmls:
        print(f"No .xml files found under {root}")
        return 0

    print(f"Found {len(xmls)} XML file(s) under {root}\nWriting CSVs under {out_root}\n")
    ok, failed = [], []
    for i, xml in enumerate(xmls, 1):
        dest_dir = out_root / xml.parent.relative_to(root)   # mirror the folder layout
        stem = _nospace(xml.stem)
        scrub_path = dest_dir / f"{stem}_scrub.csv"
        enq_path = dest_dir / f"{stem}_enq.csv"
        print(f"[{i}/{len(xmls)}] {xml.relative_to(root)} -> {scrub_path.relative_to(out_root)} (+ _enq.csv)")
        if args.dry_run:
            continue
        try:
            const = convert(str(xml), str(scrub_path), str(enq_path))   # creates dest_dir, writes both CSVs
            print(f"      crn={const['crn']}")
            ok.append(xml)
        except SystemExit:                       # load_root() sys.exit()s on an unparseable XML
            print(f"      FAILED: could not parse {xml}", file=sys.stderr)
            failed.append(xml)
        except Exception as e:
            print(f"      FAILED: {e}", file=sys.stderr)
            failed.append(xml)

    if args.dry_run:
        return 0
    print("\n" + "=" * 60)
    print(f"DONE — {len(ok)} converted, {len(failed)} failed → {out_root}")
    for xml in failed:
        print(f"  FAILED: {xml}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
