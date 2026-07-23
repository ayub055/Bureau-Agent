"""Sustained EMI (rolling 6-month minimum total EMI) — DuckDB-wrapped SQL."""

from .sustained_emi import _calculate_sustained_emi

__all__ = ["_calculate_sustained_emi"]
