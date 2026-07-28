"""Bridge: (re)generate the processed bureau CSVs on the fly from raw extracts.

The vendored DuckDB script ``bureau_data_report_creation.py`` is a black box: it
reads the raw extracts ``scrub.csv`` + ``enq.csv`` and writes comma-separated
``BU_TL.csv`` + ``BU_Feats.csv``. This module owns *all* adaptation so the script
stays untouched — process isolation, cwd wiring, comma->tab conversion, canonical
column padding, staleness detection, cleanup — and exposes one idempotent entry:

    ensure_data(force=False) -> bool   # True if it (re)generated this call

Call it once at each host entry point *before* anything reads the processed files.
Deterministic, no LLM, fail-soft: it **never raises** — on any problem it logs a
warning and leaves the existing processed files untouched. See Integartion_context.md.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

import config.settings as S

logger = logging.getLogger(__name__)

# Run-once-per-process guard so repeated entry-point calls don't re-run the job.
_GENERATED = False

# Script-output -> canonical column aliases, keyed by output type.
# {canonical_name: produced_name}; matched case-insensitively, then the produced
# column is renamed to the canonical name so downstream (case-sensitive) readers
# find it. Case-only differences are handled automatically and need no entry here.
_ALIASES = {
    "dpd_data": {},
    "tl_features": {"uns_enq_l12m": "enq_unsec_12M"},
}


def _needs_regen(inputs: list[str], outputs: list[str]) -> bool:
    """Regenerate when any output is missing, or an input is newer than an output."""
    if any(not os.path.exists(o) for o in outputs):
        return True
    newest_input = max(os.path.getmtime(i) for i in inputs)
    oldest_output = min(os.path.getmtime(o) for o in outputs)
    return newest_input > oldest_output


def _load_schema() -> dict:
    """Canonical downstream columns for padding; {} if it can't be loaded (fail-soft)."""
    try:
        return json.loads(Path(S.OUTPUT_SCHEMA_FILE).read_text())
    except Exception as exc:  # noqa: BLE001 - fail-soft, pass columns through unchanged
        logger.warning("Could not load output schema %s: %s", S.OUTPUT_SCHEMA_FILE, exc)
        return {}


def _adapt(raw_path: str, dst_path: str, canonical_cols, delimiter: str,
           aliases: dict | None = None) -> None:
    """Convert one comma-sep script output into the delimited downstream file.

    Values are read as exact strings (blanks stay "", not NaN). Each canonical
    column is matched to a produced column **case-insensitively** (or via
    ``aliases``) and the produced column is renamed to the canonical name/casing,
    so case-only differences and known renames don't silently null downstream.
    Missing canonical columns are padded empty; extra columns the script emits are
    kept after the canonical ones. With no canonical list, columns pass through.
    """
    df = pd.read_csv(raw_path, dtype=str, keep_default_na=False)
    # DuckDB's numeric round-trip in the vendored script emits integer amounts as
    # floats (442000 -> "442000.0"). Strip a trailing ".0"/".00" so processed CSVs
    # match the canonical int-string style; genuine decimals (e.g. "68.5") are left.
    df = df.replace(r"^(-?\d+)\.0+$", r"\1", regex=True)
    if not canonical_cols:
        df.to_csv(dst_path, sep=delimiter, index=False)
        return

    aliases = aliases or {}
    # Case-insensitive index of produced columns -> actual produced name.
    produced_by_lower: dict[str, str] = {}
    for c in df.columns:
        produced_by_lower.setdefault(c.lower(), c)  # first casing wins on collision

    rename: dict[str, str] = {}
    for col in canonical_cols:
        candidates = [col] + ([aliases[col]] if col in aliases else [])
        match = next(
            (produced_by_lower[c.lower()] for c in candidates
             if c.lower() in produced_by_lower),
            None,
        )
        if match is None:
            df[col] = ""          # pad missing canonical column
        elif match != col:
            rename[match] = col    # normalise case / apply alias
    if rename:
        df = df.rename(columns=rename)

    canonical_set = set(canonical_cols)
    extras = [c for c in df.columns if c not in canonical_set]
    ordered = list(dict.fromkeys(list(canonical_cols) + extras))
    df[ordered].to_csv(dst_path, sep=delimiter, index=False)


def ensure_data(force: bool = False) -> bool:
    """Ensure the processed bureau CSVs are fresh, regenerating from raw if needed.

    Returns True if it (re)generated this call, False otherwise. Never raises.
    """
    global _GENERATED

    if not S.AUTO_GENERATE:
        return False
    if _GENERATED and not force:
        return False

    inputs = [S.SCRUB_FILE, S.ENQ_FILE]
    outputs = [S.BUREAU_DPD_FILE, S.TL_FEATURES_FILE]
    workdir = os.path.dirname(S.SCRUB_FILE)

    try:
        if not all(os.path.exists(i) for i in inputs):
            logger.info(
                "Raw inputs (%s) not present — using existing processed files.",
                ", ".join(os.path.basename(i) for i in inputs),
            )
            _GENERATED = True
            return False

        if not force and not _needs_regen(inputs, outputs):
            logger.info("Processed bureau files are up to date — skipping regeneration.")
            _GENERATED = True
            return False

        logger.info("Regenerating processed bureau files from raw extracts …")
        result = subprocess.run(
            [sys.executable, S.BUREAU_GEN_SCRIPT],
            cwd=workdir,  # script uses bare relative filenames for read + write
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"generation script failed (exit {result.returncode}): "
                f"{result.stderr[-2000:]}"
            )

        schema = _load_schema()
        _adapt(
            os.path.join(workdir, S.RAW_TL_OUTPUT),
            S.BUREAU_DPD_FILE,
            schema.get("dpd_data"),
            S.BUREAU_DPD_DELIMITER,
            _ALIASES["dpd_data"],
        )
        _adapt(
            os.path.join(workdir, S.RAW_FEATS_OUTPUT),
            S.TL_FEATURES_FILE,
            schema.get("tl_features"),
            S.TL_FEATURES_DELIMITER,
            _ALIASES["tl_features"],
        )
        logger.info("Processed bureau files regenerated.")
        _GENERATED = True
        return True

    except Exception as exc:  # noqa: BLE001 - fail-soft: keep existing outputs
        logger.warning(
            "Bureau data generation failed (%s) — keeping existing processed files.",
            exc,
        )
        _GENERATED = True  # avoid retry storms within the process
        return False

    finally:
        # The script leaves a stray persistent DB file in cwd as a side effect.
        stray = os.path.join(workdir, "mydb.duckdb")
        if os.path.exists(stray):
            try:
                os.remove(stray)
            except OSError:
                pass
