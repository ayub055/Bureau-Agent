#!/usr/bin/env python3
"""TASK 1 + 2 — select all *.xml files under a folder (recursively, so it walks every
sub-folder) and rename them by removing spaces.

Standalone helper (touches nothing in the pipeline). For every `*.xml` at any depth
below the given folder whose name contains whitespace, it strips the spaces and renames
the file (e.g. "CE 1290 report.xml" -> "CE1290report.xml"). Skips files that already
have no spaces, and won't overwrite an existing target.

Because it recurses, one call handles every distinct case folder at once:
    python rename_xml_spaces.py data/Shreyas_cases            # walks CE1290/, CE1291/, ...
    python rename_xml_spaces.py data/Shreyas_cases --dry-run  # preview only
    python rename_xml_spaces.py data/Shreyas_cases/CE1290     # or just one folder
"""
import sys
from pathlib import Path


def rename_xmls(folder: str, dry_run: bool = False) -> None:
    d = Path(folder)
    if not d.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        return
    for xml in sorted(d.rglob("*.xml")):               # every xml in every sub-folder
        new_name = "".join(xml.name.split())
        # new_name = xml.name.split("CIBIL")[0] + "CIBIL"           # remove ALL whitespace
        if new_name == xml.name:
            continue                                   # no spaces -> leave as-is
        target = xml.with_name(new_name)
        if target.exists():
            print(f"SKIP (target exists): {xml} -> {new_name}")
            continue
        print(f"{'WOULD RENAME' if dry_run else 'RENAMED'}: {xml} -> {new_name}")
        if not dry_run:
            xml.rename(target)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 1:
        sys.exit("Usage: python rename_xml_spaces.py <folder> [--dry-run]")
    rename_xmls(args[0], dry_run="--dry-run" in sys.argv)
