"""Bureau income (CIBIL affluence) calculation — DuckDB-wrapped SQL."""

from .bureau_income import _calculate_bureau_income

__all__ = ["_calculate_bureau_income"]
