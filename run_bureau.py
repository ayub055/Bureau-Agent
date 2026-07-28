"""Simple CLI for the Bureau Analyser.

Generates the Bureau Analyser report (HTML + Excel) for one or more CRNs.

Usage:
    python run_bureau.py 698167220
    python run_bureau.py 698167220 100384958
    python run_bureau.py 698167220 --theme original
    python run_bureau.py --xml data/cust1.xml          # CRN auto-derived from the XML
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
    parser.add_argument("crns", nargs="*", type=int,
                        help="One or more CRNs (optional when --xml is given)")
    parser.add_argument(
        "--xml", type=str, default=None,
        help="Raw CIBIL XML to convert to scrub.csv/enq.csv first; CRN is auto-derived from it",
    )
    parser.add_argument(
        "--theme", default=DEFAULT_THEME, choices=sorted(THEME_TEMPLATES),
        help=f"HTML theme/template to render with (default: {DEFAULT_THEME})",
    )
    args = parser.parse_args()

    # --xml: convert the raw XML → scrub.csv/enq.csv (at the settings paths), then
    # force a data regeneration so the report builds off this customer's data.
    if args.xml:
        import config.settings as S
        from bureau_data_xml_converter import convert
        from tools.bureau_data_generator import ensure_data
        const = convert(args.xml, S.SCRUB_FILE, S.ENQ_FILE)
        logger.info("Converted %s → scrub.csv/enq.csv (crn=%s)", args.xml, const["crn"])
        ensure_data(force=True)
        if not args.crns:
            args.crns = [int(const["crn"])]
    elif not args.crns:
        parser.error("provide at least one CRN, or --xml to derive it from a raw XML")

    from tools.combined_report import generate_combined_report_pdf

    for crn in args.crns:
        logger.info("Generating Bureau Analyser report for CRN %s …", crn)
        _, report_path = generate_combined_report_pdf(crn, theme=args.theme)
        logger.info("→ %s", report_path)


if __name__ == "__main__":
    main()
