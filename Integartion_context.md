# Integration Context — Standalone DuckDB SQL Script → App-Consumed CSVs

Portable spec for replicating the "vendored SQL script + subprocess bridge" pattern in
another project. Describes **only** the data-generation script and the integration
mechanism — no application, pipeline, or report logic.

---

## 0. The Core Idea — Generate the CSVs On The Fly

The whole point of this integration is to **derive the processed data files at runtime from
raw extracts**, instead of requiring someone to hand off / upload pre-processed files.

- **Old model (avoided):** the processed `dpd_data.csv` / `tl_features.csv` are produced
  out-of-band and dropped into the project. The app just consumes whatever static file it
  was given. Refreshing data = a manual re-processing + re-upload step, easy to forget, easy
  to get stale/inconsistent.
- **This model (adopted):** the project holds the **raw extracts** (`scrub.csv`, `enq.csv`)
  and the **transformation logic** (the SQL script). The processed CSVs are (re)generated
  **on the fly at startup** whenever the raw inputs change. The processed files become a
  *cache/derived artifact*, not a manually-maintained input.

Consequences that shape everything below:
- Refreshing data = **replace the raw extract and restart**; the processed files rebuild
  themselves. No separate processing tool, no upload step.
- The transformation is **version-controlled and reproducible** — the same raw input always
  yields the same processed output, and the logic lives next to the code that uses it.
- Downstream code is **unchanged** — it still reads the same processed CSVs; it just no
  longer matters whether a human produced them or the bridge did.
- Because generation is automatic, it must be **safe by default**: no raw inputs, or a
  generation failure, must silently fall back to the existing processed files (fail-soft),
  and it must be cheap enough to gate on a staleness check so it doesn't run every launch.

Everything in the rest of this doc is machinery in service of that idea: run the raw→processed
transform automatically, safely, and only when needed.

---

## 1. The Two Pieces

```
raw extracts (CSV)                  ┌──────────────────────────┐            downstream CSVs
  scrub.csv  ──────────────────────▶│  SQL SCRIPT (black box)  │──▶ BU_TL.csv ─┐
  enq.csv    ──────────────────────▶│  bureau_report_..._.py   │──▶ BU_Feats.csv│
                                     └──────────────────────────┘               │
                                                  ▲                             │
                                                  │ subprocess                  ▼
                                     ┌──────────────────────────┐   ┌────────────────────┐
                                     │  BRIDGE (the integration)│──▶│ dpd_data.csv (\t)  │
                                     │  bureau_data_generator.py│   │ tl_features.csv(\t)│
                                     └──────────────────────────┘   └────────────────────┘
```

- **The SQL script** is a self-contained transformation. It is treated as a **vendored
  black box** — never edited. Its only job: read 2 raw CSVs, write 2 processed CSVs.
- **The bridge** owns *all* adaptation: process isolation, path wiring, delimiter
  conversion, schema padding, staleness detection, fail-soft, cleanup.

The golden rule: **the script's logic/output is kept AS-IS; every adaptation lives in the
bridge.** This is what lets the script evolve (or be swapped) without touching downstream.

---

## 2. The SQL Script — Contract & Gotchas

What the script *is*, from an integration standpoint (ignore what the SQL computes):

- **Shape**: one `main()` function containing a long chain of `duckdb.sql("CREATE TABLE …")`
  statements, guarded at the bottom by:
  ```python
  if __name__ == "__main__":
      main()
  ```
  So it runs as a plain `python script.py`.

- **Inputs / outputs are HARD-CODED as BARE relative filenames** at module top:
  ```python
  bu_input_file  = "scrub.csv"     # read
  enq_input_file = "enq.csv"       # read
  bu_feats_output = "BU_Feats.csv" # written
  bu_tl_output    = "BU_TL.csv"    # written
  ```
  ⚠️ **This is the single most important coupling.** The names are relative to the
  **current working directory**, not the script's location. → The caller **must** launch
  the script with `cwd` set to the directory that holds the inputs (and where outputs
  should land). Get this wrong and it either can't find inputs or writes outputs somewhere
  unexpected.

- **Writes comma-separated CSVs** (`df.to_csv(path, index=False)` — default `,`).
  Downstream wants tab-separated → the bridge converts.

- **Builds a long chain of named tables** in DuckDB's *default* connection
  (`PP_HS_BASE_BU_TL_1 … _14`, enquiry tables, maxdpd tables). Several early
  `CREATE TABLE` statements have **no `DROP TABLE IF EXISTS`**. ⚠️ Therefore running
  `main()` twice **in the same process collides** ("table already exists"). A fresh
  process per run is mandatory, not a nicety.

- **Side effect**: it calls `duckdb.connect("mydb.duckdb")` but then uses the global
  `duckdb.sql(...)` (default in-memory connection). Net effect: tables live in-memory, but
  an (essentially empty) **`mydb.duckdb` file is left on disk** in the cwd. The bridge
  deletes it afterward.

- **Only dependencies**: `duckdb`, `pandas`. Nothing app-specific is imported.

**Takeaway for porting a *different* script:** audit for these four properties —
(1) hard-coded relative paths, (2) output delimiter, (3) in-process table/state collisions,
(4) stray files created in cwd. The bridge is designed around exactly these.

---

## 3. The Bridge — Responsibilities (the reusable pattern)

A single module exposing one idempotent entry function, e.g. `ensure_data(force=False) -> bool`.
Returns `True` if it (re)generated this call, `False` otherwise. **Never raises.**

Its responsibilities, in order:

1. **Toggle** — a config flag (`AUTO_GENERATE`) to disable the whole thing; return early if off.

2. **Run-once-per-process guard** — a module-level `_GENERATED` bool so repeated calls
   (e.g. UI reruns) don't re-run the heavy job. `force=True` overrides.

3. **Inputs-present check** — if raw inputs are missing, log and no-op (use existing outputs
   as-is). Set the guard so it won't re-check on every call.

4. **Staleness check** (`_needs_regen`) — regenerate when:
   - any output file is missing, **or**
   - `max(mtime of inputs) > min(mtime of outputs)` (an input is newer than an output).

5. **Run the script in an isolated subprocess** — this is the core technique:
   ```python
   subprocess.run(
       [sys.executable, SCRIPT_PATH],
       cwd=workdir,            # = directory of the raw inputs (CRITICAL, see §2)
       capture_output=True,
       text=True,
   )
   # non-zero returncode → raise RuntimeError with the tail of stderr
   ```
   Why subprocess (not import-and-call):
   - fresh DuckDB state each run → no table-name collisions;
   - the script's global connection / cwd assumptions can't pollute the host process;
   - a crash in the script can't take down the host.

6. **Adapt each raw output → downstream file**:
   ```python
   df = pd.read_csv(raw_path, dtype=str, keep_default_na=False)  # exact values; blanks stay ""
   for col in canonical_cols:                # pad any missing downstream column…
       if col not in df.columns:
           df[col] = ""                      # …as EMPTY, preserving the schema contract
   extras  = [c for c in df.columns if c not in canonical_cols]
   ordered = [c for c in canonical_cols if c in df.columns] + extras  # canonical first, extras after
   df[ordered].to_csv(dst_path, sep="\t", index=False)               # comma → tab
   ```
   - `dtype=str` + `keep_default_na=False` → the script's values are preserved verbatim and
     blank cells render as `""` (not `NaN`), so padded-empty and genuinely-blank look identical.
   - **Schema padding** decouples the script's column set from what downstream expects: the
     canonical column list comes from a checked-in JSON snapshot
     (`{"dpd_data": [...cols], "tl_features": [...cols]}`). Missing → appended empty. Extra
     columns the script emits are kept (appended after the canonical ones). If the snapshot
     can't be loaded, fall through and pass columns through unchanged (fail-soft).

7. **Fail-soft wrapper** — the whole build is in `try/except`; on any error, log a warning,
   set the guard (avoid retry storms), and **leave existing outputs untouched**.

8. **Cleanup in `finally`** — remove the stray `mydb.duckdb` the script leaves in `workdir`.

---

## 4. Config Knobs the Bridge Needs

Centralize these (paths derived from one project-root anchor):

| Setting | Meaning |
|---|---|
| `AUTO_GENERATE` (bool) | Master on/off switch for regeneration. |
| `SCRIPT_PATH` | Absolute path to the vendored SQL script. |
| `SCRUB_FILE`, `ENQ_FILE` | Absolute paths to raw inputs. **Basenames must match the bare names the script hard-codes** (`scrub.csv`, `enq.csv`). Their directory becomes the subprocess `cwd`. |
| `RAW_TL_OUTPUT`, `RAW_FEATS_OUTPUT` | The comma-sep basenames the script writes (`BU_TL.csv`, `BU_Feats.csv`), resolved relative to `cwd`. |
| `DPD_FILE`, `FEATURES_FILE` | Final tab-sep downstream paths the bridge writes. |
| `OUTPUT_SCHEMA_FILE` | JSON snapshot of canonical downstream columns, for padding. |
| delimiter | Downstream delimiter (`\t` here). |

**Naming constraint worth repeating:** because the script references bare `"scrub.csv"` /
`"enq.csv"`, the raw-input basenames are **not free to rename** unless you also edit the
script (which the pattern forbids). Keep the basenames; only their directory is yours to choose.

---

## 5. Wiring Into a Host

- Call the bridge's `ensure_data()` **once at startup, before anything reads the output
  files.** In each entry point:
  ```python
  from <pkg>.data_generator import ensure_data
  ensure_data()   # no-op when inputs absent or outputs fresh; fail-soft
  ```
- No other coupling. Downstream code keeps reading the same output CSVs it always did —
  it neither knows nor cares that they may have just been regenerated.

---

## 6. Replication Checklist (for the new project)

1. Drop the standalone SQL script in unchanged. Note its hard-coded input/output basenames.
2. Place raw inputs in one directory using **exactly those basenames**.
3. Snapshot the expected downstream columns into a JSON file (`{"<out1>": [...], "<out2>": [...]}`).
4. Add the config knobs from §4 (one project-root anchor; derive the rest).
5. Implement the bridge with the §3 responsibilities. Key non-obvious bits:
   - `cwd=<inputs dir>` on the subprocess;
   - fresh subprocess per run (no import-and-call);
   - `dtype=str, keep_default_na=False` on read;
   - delimiter conversion + canonical-column padding on write;
   - delete the stray `mydb.duckdb` in `finally`;
   - fail-soft: keep old outputs on any error.
6. Call `ensure_data()` once at each host entry point, before outputs are read.

---

## 7. Why Each Non-Obvious Choice Exists (so you don't "fix" it away)

| Choice | Reason |
|---|---|
| Subprocess instead of `import main; main()` | Script builds named DuckDB tables in the default connection with no idempotent drops → in-process re-run collides. Subprocess = clean slate + host isolation. |
| `cwd=<inputs dir>` | Script uses bare relative filenames for both read and write. |
| Comma→tab conversion in the bridge | Script writes CSV with default `,`; downstream contract is tab-separated. |
| Canonical-column padding | Decouples the script's evolving column set from the downstream schema contract; missing columns appear (empty) so readers never break. |
| `dtype=str` + `keep_default_na=False` | Preserve exact string values; make padded-empties and real blanks indistinguishable (both `""`). |
| mtime-based staleness | Cheap "regenerate only when raw inputs changed" without hashing. |
| Delete `mydb.duckdb` in `finally` | Script leaves a stray persistent DB file in cwd as a side effect. |
| Fail-soft + run-once guard | A generation failure must never break the host; heavy job must not run repeatedly per process. |
