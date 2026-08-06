# Handover — Bureau Analyser **v2 UI** theme

_Last updated: 2026-06-11 · Scope: a new interactive HTML theme (`v2`) for the Bureau Analyser report and the work that followed it._

---

## 1. TL;DR

A new HTML theme **`v2`** (`templates/combined_report_v2.html`) was built to match the design system of `bank_report_v2.html` and is now the **default** for all entry points. On top of the visual redesign, three sections were made **interactive with multiple switchable views**:

| Section | What it became |
|---|---|
| **Portfolio Visualizations** (`#charts`) | Tabs: **Explore** (pick metric checkboxes + chart type) · **Quick Views** (donuts + live/closed) · **Exposure Over Time** |
| **Key Findings** (`#findings`) | View toggle: **Carousel** · **Reader** (master–detail) · **Timeline** · **Tiles**, plus severity filter chips |
| **Behavioral & Risk Features** (`#behavioral`) | View toggle: **Bars** (group accordion cards — collapsible, all closed initially, default) · **Table** (sortable, flat). Radar & the separate Summary view removed; missing data is neutral "No data", not risk. |

All numbers/thresholds are computed **deterministically in Python**; the template only renders. Output is **HTML-only** — the FPDF/PDF rendering stack was later removed; for paper, use the browser's print-to-PDF.

**Test CRN:** `698167220`  ·  **Python:** `/Users/ayyoob/anaconda3/bin/python`

---

## 2. Files changed

### Renderer — `pipeline/renderers/combined_report_renderer.py`
The single source of truth for all v2 logic. New/changed:

- **`THEME_TEMPLATES`** (now module-level) + **`DEFAULT_THEME = "v2"`**:
  ```python
  THEME_TEMPLATES = {
      "v2":       "combined_report_v2.html",   # maintained default
      "original": "combined_report_original.html",  # frozen legacy
      "emerald":  "combined_report.html",           # frozen legacy
  }
  ```
  Both CLIs derive their `--theme` choices from this dict, so adding a future theme here is enough.
- **`_compute_v2_context(bureau_report, scorecard, bureau_checklist, key_findings_data, tl_features_data, vectors_data)`** → builds the whole `v2` context dict (see §4). Returns early with just `nav_badges` when `bureau_report is None`.
- **`_compute_dpd_grid(customer_id)`** — months × product DPD grid from raw `payhist_1..36` / `dt1..36` in `dpd_data.csv`. Fully fail-soft (`try/except → None`), same pattern as checklist B6.
- **`_dpd_level()`, `_parse_month_str()`** — small helpers.
- **`_compute_behavioral(tl)`** + config `_BF_GROUPS`, `_BF_SPECS` and helpers `_bf_metric / _bf_display / _bf_hint / _bf_segments` — the threshold-aware behavioral model (see §6.3). Thresholds mirror the rules that previously lived inline in the template.
- `render_combined_report_html(..., theme=DEFAULT_THEME)` and `render_combined_report(..., theme="v2")` defaults flipped; `v2=` added to the `template.render(...)` call (old themes ignore the extra key).

### Template — `templates/combined_report_v2.html` (**new, active default**)
The entire v2 page. Built from the bank_report_v2 design system (exact CSS variables, panels, KPI tiles, tags, tables, `@media print`). Charts use the **local** `{% include 'chart.min.js' %}` (Chart.js v4.4.0) — **never a CDN** (reports must work offline).

### Entry points
- `tools/combined_report.py` — `generate_combined_report_pdf(customer_id, theme="v2", ...)` (batch inherits this).
- `run_bureau.py` — `--theme` `choices=sorted(THEME_TEMPLATES)`, `default=DEFAULT_THEME`.
- `batch_reports.py` — added `--theme`; threaded through `run_batch(..., theme=...)` → `generate_combined_report_pdf(theme=...)`.

### Docs
- `CLAUDE.md` — Gotchas #1/#2 updated: **v2 is the maintained default; original/emerald are frozen legacy** (no longer kept in sync). Entry-point theme list updated.
- `.claude/rules/templates.md` — same rule; new-sections-go-to-v2-only; CDN forbidden.

### NOT touched
`combined_report.html`, `combined_report_original.html`, the Excel exporter, and all extractors/schemas — **every new data field already flows through the existing context** (`tl_features`, `vectors_data`, `executive_inputs`). (The fpdf2 PDF renderers and the standalone `bureau_report.html` were later deleted.)

---

## 3. How it renders (data flow)

```
generate_combined_report_pdf(crn, theme="v2")        tools/combined_report.py
  → build_bureau_report(crn) (+ LLM narrative, fail-soft)
  → render_combined_report(bureau_report, theme="v2")  combined_report_renderer.py
      → render_combined_report_html(bureau_report, theme="v2")
          • vectors_data / tl_features_data / key_findings_data / chart_data
          • scorecard = compute_scorecard(bureau_report=...)
          • bureau_checklist = compute_checklist(...)
          • persona = compute_probable_persona(...)
          • v2 = _compute_v2_context(...)        ← NEW
          → template.render(bureau_report, vectors_data, tl_features,
                            key_findings, chart_data, scorecard,
                            exposure_summary, bureau_checklist, persona,
                            section_flags, v2)
  → writes reports/bureau_analyser_{crn}_report.html (+ excel)
```

The HTML is also copied to `reports/bureau_analyser_html_version/`.

---

## 4. The `v2` context object

Computed in `_compute_v2_context`; consumed by `combined_report_v2.html`. Plain dicts/lists (survives `|tojson` for the risk-trail export).

| Key | Shape | Drives |
|---|---|---|
| `v2.kpis` | `{cibil, max_dpd, foir, exposure, verdict}` — each `{value, sub, rag}`; `exposure` also has `labels/series` (sparkline); `verdict` has `stress_pct` | KPI strip (`#kpis`) |
| `v2.profile` | `{ktk_rel, customer_segment, income_source, bank_grp, bu_grp, affluence_amt, node}` (None if all empty) | Customer Profile card (`#profile`) |
| `v2.nav_badges` | `{checklist_flagged, findings_high}` | red count badges on nav chips |
| `v2.behavioral` | `{groups:[{name, metrics:[…], ok, warn, risk, assessable, dots, status, count_label, takeaway}], flat:[…metrics, risk-first…], summary:{safe,warn,risk,neutral}}`; groups pre-sorted worst-first | Behavioral section (`#behavioral`) |
| `v2.charts` | **pre-serialized JSON string** (rendered `| safe`) → `{live_closed, vintage, dpd_grid, explorer}` | charts + DPD heatmap + explorer |

`v2.charts.explorer = {products:[…], metrics:{key:{label, fmt, values}}}` with 11 metrics (sanctioned, outstanding, count, live, closed, overdue, utilization, on_us, vintage, max_single, joint). `fmt ∈ {inr, int, pct, num}`.

---

## 5. Template section map (`id`s)

`topbar` (sticky, verdict pill, Export/Notes menus) · nav chips + calibration disclaimer · `kpis` · `checklist` (3-col, sortable) · `profile` (profile card + persona) · `signals` (scorecard + tl_features chips) · `summary` (LLM narrative, read-more) · `portfolio` (tabs: Overview / Kotak / Defaulted) · `charts` · `dpd` (tabs: Heatmap / Event Timeline) · `findings` · `products` (tabs: Breakdown / Vintage & Activity / Vintage Timeline) · `behavioral` · footer · floating notepad + back-to-top.

---

## 6. The three interactive sections (detail)

### 6.1 Portfolio Visualizations (`#charts`)
Redesigned 2026-06-11. Leads with a deterministic **at-a-glance header** (`.viz-head`: a plain-English `takeaway` + 3 exposure chips Outstanding / Sanctioned / Utilisation), then tabs (`.tabs`): **Explore / Quick Views / Exposure**. The header, quick-view bars, and exposure sparkline are all **server-rendered** from `v2.viz` (`_compute_viz` in the renderer) — no canvas, so no hidden-tab resize concern.
- **Explore** = interactive builder: **key metric chips + 'More' expander** (`#vizMetric` = `.chipgrp` of `.viz-mchip`; key = Outstanding/Sanctioned/Live/Overdue, rest hidden behind `#vizMore` → `.show-more`) + chart-type pills (`#vizChart`: bar / horizontal / **donut** / line — Pie dropped) → one Chart on `#cmbChartExplorer`. Single metric ⇒ bars colored per product; multiple ⇒ one dataset per metric with a **second y-axis** when units differ. Defaults to Outstanding. Persisted: `bureau_v2_explorer::<crn>`.
- **Quick Views** = compact server-rendered **horizontal split bars** (`v2.viz.splits`): Product mix (by count) · Live vs Closed · Secured vs Unsecured · On-Us vs Off-Us. Single-category splits render as a calm full bar (no broken donut); zero total shows a quiet "No data". The old donut/live-closed Chart.js builders were removed.
- **Exposure** = inline-SVG **sparkline** (`_viz_sparkline`) of total sanctioned exposure + key stats (peak / now / % below peak / trend word). The per-product **stacked-area** chart (`#cmbChartTimeseries`) now lives in a `<details id="expoDetail">` expander; its `toggle` handler resizes the chart on open (it builds at 0px while collapsed). Print CSS force-opens the expander.
- `v2.viz` shape: `{takeaway, chips:[{label,value}], splits:[{name, has_data, segments:[{label,display,pct,color}]}], exposure:{spark(svg), peak, peak_when, now, down_from_peak, trend, has_detail}}`.
- Charts built while a tab is hidden are resized on tab show (see §7).

### 6.2 Key Findings (`#findings`)
View toggle (`#findingsViewToggle`, `.fview-toggle`): **Carousel · Reader · Timeline · Tiles**, remembered in `bureau_v2_findings_view::<crn>`.
- All four views render from the same `key_findings` via a shared Jinja `SEVMAP` (severity → key/word/icon), so severity colour/icon/label and the category chip are consistent.
- **Carousel**: severity filter chips (All / per-severity with counts) + dots/arrows/swipe; filtering uses `display:none` so visible slides stay contiguous for the translate.
- **Reader**: clickable headline list + detail pane. **Timeline**: vertical stepper with severity nodes. **Tiles**: expandable grid (click to reveal inference).

### 6.3 Behavioral & Risk Features (`#behavioral`)
Redesigned 2026-06-11 for readability. View toggle (`#behavioralViewToggle`): **Bars · Table** (Bars is the default), remembered in `bureau_v2_behavioral_view::<crn>`. All driven by `v2.behavioral` from `_compute_behavioral()`:

- **Model**: `_BF_SPECS` lists 24 metrics as `(field, plain_label, group, fmt, direction, params)`. Labels are **plain-English** (jargon dropped); `params.unit ∈ {"%", " months", " days"}` drives plain hints and a `%` value suffix. `direction ∈ {low, high, band, cleanNone, presentNone, neutral}`. Each metric resolves to:
  - `status ∈ {safe, warn, risk, neutral}`
  - `kind = "bar"` (numeric, `segments` [green/amber/red width-%] + `marker` %) **or** `"strip"` (presence/reference; carries `strip_label` like `NO DATA` / `CLEAN` / `REPORTED` / `REFERENCE`)
  - `hint` — plain, rounded (e.g. `healthy below 32 months`, `healthy above 14`, `expected 3–16 months`), via `_bf_hint` / `_bf_num` / `_bf_round`.
- **Missing data → neutral "No data"** (never red risk) for all numeric/presence metrics. **`cleanNone` is preserved** — a missing 0+DPD event still reads positively as `Clean` (genuinely good news, not absent data).
- **Bars** view (default): per-group **accordion cards** (`#bfCards`), sorted **worst-first** ("no data" groups last), **one open at a time** and **all closed initially**. Each card header shows a chevron, a 5-dot meter (`dots` = `round(5·ok/assessable)`), `count_label`, and a deterministic plain-English `takeaway` (`_bf_takeaway`, from `_BF_POSITIVE`/`_BF_NODATA`). The body holds the group's metric rows via the shared `bf_metric_row` Jinja macro (single-line: label + inline `(hint)` + bar + value). Accordion JS lives in the `#behavioral` block; print CSS force-opens every `.bf-card-body` so paper shows all metrics.
- **Table** view: flat sortable (`#bfTable`) over `v2.behavioral.flat` (pre-sorted risk-first); columns Status · Metric · Value · **Healthy when** (plain `hint`). Group column dropped.
- **Radar removed.** There are no charts in this section anymore, so no hidden-tab chart-resize handling is needed.

---

## 7. Conventions & gotchas (read before editing)

- **Logic lives in Python**, not the template (repo rule). Add thresholds/derivations to the renderer; the template only loops/conditionals.
- **Charts must use the local `chart.min.js`** (`{% include %}`), never a CDN. Offline-capable requirement.
- **Charts in hidden tabs render at 0px** → the `tab()` function (charts/portfolio/products/dpd tabs) resizes charts on show via `Chart.getChart(canvas).resize()`. If you add a chart inside a hidden view, make sure its show-handler resizes it. (The behavioral section no longer contains charts after the radar was removed.)
- **Shared `.fview` / `.fview-toggle` classes** are used by both `#findings` and `#behavioral`. **Print rules MUST be section-scoped** — they are: print shows `#findings .fview[data-view="timeline"]` and `#behavioral .fview[data-view="bars"]` (the always-complete views) and hides the rest. A global `.fview` print rule would blank a section.
- **DPD heatmap** (`#dpd`) comes from `_compute_dpd_grid()` reading `payhist_*`/`dt*`. It is fail-soft and **hides gracefully when clean** — the test CRN `698167220` has a clean history, so the heatmap tab auto-falls-back to the event timeline. Test populated cells with a delinquent CRN when one is available in `dpd_data.csv`.
- **localStorage keys** are namespaced per customer to avoid clashing with the bank report: `bureau_v2_notepad::<crn>` (+ `_visible`, `_intro_seen`), `bureau_v2_explorer::<crn>`, `bureau_v2_findings_view::<crn>`, `bureau_v2_behavioral_view::<crn>`.
- The `v2` context is computed for **all** themes but only the v2 template reads it — legacy `original`/`emerald` ignore it, so they keep working.

---

## 8. How to regenerate & verify

```bash
PY=/Users/ayyoob/anaconda3/bin/python

# Single CRN (HTML + Excel), v2 is default
$PY run_bureau.py 698167220
$PY run_bureau.py 698167220 --theme original      # legacy still works
$PY run_bureau.py 698167220 --no-pdf              # HTML + Excel only

# Batch (now supports --theme too)
$PY batch_reports.py --crns 698167220 --theme v2 --output reports/batch_output.xlsx
```

**Checks used during development (all green):**
- No unrendered Jinja: `grep -c '{{' reports/bureau_analyser_698167220_report.html` → 0
- Local Chart.js (no CDN): `grep -c cdn.jsdelivr …` → 0
- Inline JS sanity: extract each `<script>` and run `node --check`.
- Legacy regression: render `theme in (v2, original, emerald)` + `bureau_report=None` programmatically (all render, None shows the absence note).
- Visual: headless Brave screenshot, e.g.
  `"/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" --headless --disable-gpu --window-size=1200,9000 --screenshot=/tmp/out.png "file://…/report.html"` (no Chrome installed on this machine; Brave is Chromium-based).

---

## 9. Known limitations / possible follow-ups

- **DPD heatmap unverified with real delinquency** — only the clean (hide) path was seen, because the sole CRN in `data/dpd_data.csv` is clean. Verify cells/colors against a delinquent CRN.
- **Missing data is now neutral "No data"** (resolved 2026-06-11) — the old `None → risk` rule that made thin-file customers look harsh is gone for numeric/presence metrics. `cleanNone` is intentionally exempt (missing = `Clean` = good).
- **PDF stack removed** — the fpdf2 renderers were deleted; output is HTML-only. The rich v2 design reaches paper via the browser's print-to-PDF (or a future HTML→PDF engine like WeasyPrint, a separate effort).
- **Bullet-bar axis maxes** are hand-set per metric in `_BF_SPECS` (`axis`). If new metrics are added, set a sensible `axis` so the threshold band is visible.

---

## 10. Adding things later

- **New theme:** add to `THEME_TEMPLATES`; both CLIs pick it up automatically.
- **New behavioral metric:** add a row to `_BF_SPECS` (field/plain_label/group/fmt/direction/params; set `unit`, and an `axis` for `bar` metrics so the threshold band is visible). It flows into all three behavioral views, the group dot-meter/takeaway, and the risk-first table automatically.
- **New explorer metric:** add to the `explorer["metrics"]` dict in `_compute_v2_context` (value list aligned to `products`, plus `fmt`). The checkbox + chart wiring is generic.
- **New finding view:** add a `<div class="fview" data-view="…">` inside `#findings` and a toggle button; the toggle JS and per-section print rule already generalize (add the new view to the print rule if it should print).
