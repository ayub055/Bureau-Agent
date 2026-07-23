"""Report metadata schema.

Holds `ReportMeta`, the small metadata block that flows through the bureau
report pipeline (`schemas/bureau_report.py`, `bureau_report_builder.py`).
The former banking `CustomerReport` model and its section blocks were removed
with the banking layer.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ReportMeta(BaseModel):
    """Report metadata."""
    customer_id: int
    prty_name: Optional[str] = Field(default=None, description="Party/Customer name")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    analysis_period: str = Field(default="Last 6 months")
    currency: str = Field(default="INR")
    transaction_count: int = Field(default=0)
