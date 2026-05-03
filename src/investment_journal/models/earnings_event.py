"""Earnings event issue: pre-call prep + post-call recap, one per quarter per ticker."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class EarningsRecap(BaseModel):
    revenue: str = Field(description="e.g. 'Q1 FY26 revenue $X.XXB, +X% YoY'")
    eps: str = Field(description="e.g. 'EPS $X.XX (GAAP) / $X.XX (adj)'")
    guidance: str = Field(
        description="raised / reiterated / lowered + the quoted line.",
    )
    call_quotes: list[str] = Field(
        default_factory=list,
        description="1–3 short verbatim quotes worth keeping.",
    )
    thesis_impact_pending: bool = True
    sources: list[str] = Field(
        default_factory=list,
        description="Citation URLs (press release, transcript, 10-Q).",
    )


class EarningsEvent(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    quarter: str = Field(
        pattern=r"^[1-4]Q\d{2}$",
        description="Format: '1Q26' for Jan–Mar 2026.",
    )
    expected_date: date
    timing: Literal["pre-market", "post-close", "intraday", "unknown"] = "unknown"
    prep_notes: str = ""
    checklist: list[str] = Field(
        default_factory=lambda: [
            "Prep notes written",
            "Earnings released",
            "Recap published in this issue",
            "Thesis-impact assessed (bull/bear case revisions, if any)",
            "Position dossier updated",
        ]
    )
    recap: Optional[EarningsRecap] = None
