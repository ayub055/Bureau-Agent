"""Configuration settings for the system."""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

SUMMARY_MODEL = "llama3.2"  # Bureau review narration

# Models that support the Ollama `think` parameter (emit <think> reasoning traces)
THINKING_MODEL_PREFIXES = ("deepseek-r1", "qwq", "qwen3", "phi4-reasoning")


def is_thinking_model(model_name: str) -> bool:
    """Check if a model supports reasoning/thinking mode."""
    name = model_name.lower()
    return any(name.startswith(p) for p in THINKING_MODEL_PREFIXES)

# LLM inference parameters — change here to affect all LLM calls
LLM_TEMPERATURE: float = 0       # Deterministic output for all analytical calls
LLM_SEED: int = 42               # Reproducibility seed

# =============================================================================
# DATA PATHS — Change these when switching to new data files
# =============================================================================

# Bureau DPD tradeline data
BUREAU_DPD_FILE = os.path.join(_PROJECT_ROOT, "data", "dpd_data.csv")
BUREAU_DPD_DELIMITER = "\t"

# Pre-computed tradeline features
TL_FEATURES_FILE = os.path.join(_PROJECT_ROOT, "data", "tl_features.csv")
TL_FEATURES_DELIMITER = "\t"

# --- On-the-fly bureau data generation (raw scrub/enq -> processed CSVs) ---
# The vendored DuckDB script is run as a subprocess to (re)derive the processed
# files above from raw extracts, so refreshing data = replace the raw extract and
# restart. See tools/bureau_data_generator.py (the bridge) and Integartion_context.md.
AUTO_GENERATE = True  # master on/off switch for regeneration
BUREAU_GEN_SCRIPT = os.path.join(_PROJECT_ROOT, "bureau_data_report_creation.py")
# Raw inputs — basenames MUST stay scrub.csv / enq.csv (the script hard-codes them);
# their directory (data/) becomes the subprocess cwd.
SCRUB_FILE = os.path.join(_PROJECT_ROOT, "data", "scrub.csv")
ENQ_FILE = os.path.join(_PROJECT_ROOT, "data", "enq.csv")
# Comma-separated files the script writes, resolved relative to that cwd.
RAW_TL_OUTPUT = "BU_TL.csv"        # -> BUREAU_DPD_FILE
RAW_FEATS_OUTPUT = "BU_Feats.csv"  # -> TL_FEATURES_FILE
# Canonical downstream columns, used to pad/order the converted output (fail-soft).
OUTPUT_SCHEMA_FILE = os.path.join(_PROJECT_ROOT, "config", "bureau_output_schema.json")

LOG_DIR = "logs"
