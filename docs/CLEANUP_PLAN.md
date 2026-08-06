# Cleanup Plan: `data/` move + remove PDF generation + remove dead (banking) code

> Durable copy of the approved cleanup plan. Report output is HTML-only after this.

## Context
The project shipped banking-era residue and a PDF rendering stack that are no longer
wanted. Goal: keep ONLY the HTML report-generation pipeline (byte-for-byte unchanged),
move the datasets into `data/`, and delete the dead code. Removals are deleted outright.
Legacy HTML themes (`v3`/`original`/`emerald`) and the `tools/bureau_income/` test suite
are kept.

## Part A — Move datasets into `data/`
- `dpd_data.csv` → `data/dpd_data.csv`, `tl_features.csv` → `data/tl_features.csv`.
- `config/settings.py` `BUREAU_DPD_FILE` / `TL_FEATURES_FILE` → `os.path.join(_PROJECT_ROOT, "data", ...)`.

## Part B — Delete dead standalone files
- `data/__init__.py` (+ `data/__pycache__/`) — imports a non-existent `data/loader.py`.
- `bank_report_v2.html` (stray output), `dpd_data.csv.bak` (stale backup).

## Part C — Remove dead banking config (`config/settings.py`)
Remove unused constants: `TRANSACTIONS_FILE(+_DELIMITER)`, `RG_SAL_FILE(+_DELIMITER)`,
`RG_INCOME_FILE(+_DELIMITER)`, `MODEL_NAME`, `MAX_ITERATIONS`, `PARSER_MODEL`,
`EXPLAINER_MODEL`, `USE_LLM_EXPLAINER`, `STREAMING_ENABLED`, `STREAM_DELAY`,
`VERBOSE_MODE`, `LLM_TEMPERATURE_CREATIVE`. Keep the pipeline-used ones.

## Part D — Remove ALL PDF generation (HTML unchanged)
Delete: `pipeline/renderers/pdf_renderer.py`, `pipeline/renderers/bureau_pdf_renderer.py`
(after relocating `_compute_html_chart_data` into the combined renderer), `tools/bureau.py`,
`templates/bureau_report.html`.
Edit `pipeline/renderers/combined_report_renderer.py`: remove FPDF imports, `CombinedReportPDF`,
`_render_absence_note`, `_build_combined_pdf`; relocate `_compute_html_chart_data`; simplify
`render_combined_report` to write HTML only (drop `save_pdf`). Refactor `tools/combined_report.py`
to build directly (HTML only). Update `run_bureau.py` (drop `--no-pdf`) and `batch_reports.py`.

## Part E — Strip remaining banking dead code
- `tools/scorecard.py` → `compute_scorecard(bureau_report=None)`; remove `_banking_signals` + customer_report branch.
- `schemas/customer_report.py` → keep only `ReportMeta`; remove `CustomerReport` + its banking blocks.

## Part F — Docs
Update `CLAUDE.md`, `README.md`, `instructions.md`, `docs/HANDOVER_v2_ui.md`: `data/` paths,
HTML-only output, remove references to deleted renderers/templates.

## Verification
Baseline-diff the generated HTML (must be identical), import smoke, `run_bureau.py 698167220`
(no `.pdf` written), batch run, bureau-income suite `1/1`, dead-reference grep.
