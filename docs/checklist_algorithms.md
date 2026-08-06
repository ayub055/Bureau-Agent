# Checklist & Signal Algorithms

Traced, code-referenced documentation of how individual bureau signals/checklist
items are computed. Documentation only — see the referenced code for the source of truth.

## Enquiries in last 12 months ("Enquiries — N in 12M")

**Display:** `tools/scorecard.py:175-186` — the "Enquiries" risk signal (value `"{enq} in 12M"`).

**Read as:** `bureau_report.tradeline_features.unsecured_enquiries_12m`
(`pipeline/extractors/tradeline_feature_extractor.py:36` maps CSV column `uns_enq_l12m → unsecured_enquiries_12m`, parsed as int).

**Data source chain (the value is PRE-COMPUTED, not counted at render time):**
- Raw: `enq.csv` (columns `DateOfEnquiry`, `ENQUIRYPURPOSE_NEW`), produced from the CIBIL XML by `bureau_data_xml_converter.py`.
- Computed as `enq_unsec_12M` in `bureau_data_report_creation.py:3846-3857`.
- Renamed `enq_unsec_12M → uns_enq_l12m` when writing `tl_features.csv` (`tools/bureau_data_generator.py:38`).
- Read back as `unsecured_enquiries_12m`.

### Algorithm (the formula)

```
scrub_date  = last day of the month BEFORE report_month
            = (report_month || '01')::date - 1 day          # bureau_data_report_creation.py:17

For each enquiry row (enq.csv):
    account_type_cd = map(ENQUIRYPURPOSE_NEW)                # purpose → code (…:3760-3821)
    SEC_UNSEC_FLAG  = 'UNSEC' if account_type_cd ∈ {0,5,6,8,9,12,13,24,37,38,39,40,
                       41,43,45,47,51,52,53,54,55,56,57,58,61}   # …:3831-3835
                      'SEC'   if ∈ {1,2,3,4,7,11,14,15,17,23,32,33,34,42,44,46,50,59}
                      else 'OTHERS'
    diff_month = ROUND( date_diff('day', DateOfEnquiry, scrub_date) / 30.5 , 4 )   # …:3840

enq_unsec_12M = COUNT( enquiries WHERE
                          DateOfEnquiry <= scrub_date        # …:3856  (no future-dated enquiries)
                      AND SEC_UNSEC_FLAG = 'UNSEC'           # unsecured purposes only
                      AND diff_month <= 12 )                 # …:3852  (within ~12 months)
```

So it is the **count of UNSECURED credit enquiries whose `DateOfEnquiry` falls within
~12 months before `scrub_date`**. "Month" here = 30.5 days, so the window is
`diff_month ≤ 12` ⇒ up to `12 × 30.5 = 366` days back. Secured-purpose enquiries
(HL/LAP/auto/gold/etc.) are excluded; only the unsecured group is counted.

### Thresholds (RAG on the scorecard signal)

`_rag(enq, green_max=T.ENQUIRY_HEALTHY, amber_max=T.ENQUIRY_MODERATE_RISK)` — lower is better
(`tools/scorecard.py:178`, `config/thresholds.py:56-58`).

| Enquiries in 12M | RAG | Note |
|------------------|-----|------|
| ≤ 3  (`ENQUIRY_HEALTHY`)        | green  | "Minimal" |
| 4 – 10 (`> HEALTHY`, `≤ MODERATE_RISK`) | amber | "Moderate" |
| > 10 (`ENQUIRY_MODERATE_RISK`)  | red    | "High pressure" |

(`ENQUIRY_HIGH_RISK = 15` exists in `config/thresholds.py:56` but the scorecard RAG uses
the 3 / 10 breakpoints; 15 / `COMPOSITE_ENQUIRY_THRESHOLD=10` are used by composite logic.)

### Edge cases
- If `unsecured_enquiries_12m is None` (no tradeline features / column missing) the
  "Enquiries" signal is **not emitted** (`tools/scorecard.py:176` guard).
- Only enquiries with `DateOfEnquiry <= scrub_date` count (future-dated rows ignored).
- `OTHERS`/`SEC` purposes never count toward the unsecured 12M figure.
- The count is a warehouse-style pre-computation in SQL (run via DuckDB); the renderer
  never recomputes it — it just reads `uns_enq_l12m`.
