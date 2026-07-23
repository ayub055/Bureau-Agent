"""Bureau obligation (total monthly EMI obligation) — DuckDB-wrapped SQL."""

from .obligation import _calculate_obligation

__all__ = ["_calculate_obligation"]
