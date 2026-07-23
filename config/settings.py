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

LOG_DIR = "logs"
