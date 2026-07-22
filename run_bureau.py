"""Simple CLI for the Bureau Analyser.

Generates the Bureau Analyser report (HTML + PDF + Excel) for one or more CRNs.

Usage:
    python run_bureau.py 698167220
    python run_bureau.py 698167220 100384958
    python run_bureau.py 698167220 --no-pdf
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_bureau")


def main() -> None:
    from pipeline.renderers.combined_report_renderer import THEME_TEMPLATES, DEFAULT_THEME

    parser = argparse.ArgumentParser(description="Generate a Bureau Analyser report")
    parser.add_argument("crns", nargs="+", type=int, help="One or more CRNs")
    parser.add_argument(
        "--theme", default=DEFAULT_THEME, choices=sorted(THEME_TEMPLATES),
        help=f"HTML theme/template to render with (default: {DEFAULT_THEME})",
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Skip PDF generation (HTML + Excel only)",
    )
    args = parser.parse_args()

    from tools.combined_report import generate_combined_report_pdf

    for crn in args.crns:
        logger.info("Generating Bureau Analyser report for CRN %s …", crn)
        _, report_path = generate_combined_report_pdf(
            crn, theme=args.theme, save_intermediate=not args.no_pdf,
        )
        logger.info("→ %s", report_path)


if __name__ == "__main__":
    main()
