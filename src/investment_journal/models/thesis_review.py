"""Monthly thesis review issue: does this position's thesis still hold?"""

from typing import Literal

from pydantic import BaseModel, Field


ThesisVerdict = Literal["still-holds", "partially", "no"]


class ThesisReview(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    month: str = Field(
        pattern=r"^\d{4}-\d{2}$",
        description="Month being reviewed, YYYY-MM.",
    )
    verdict: ThesisVerdict
    verdict_note: str = Field(
        min_length=1, description="One sentence supporting the verdict."
    )
    bull_changes: str = ""
    bear_changes: str = ""
    action: str = Field(
        min_length=1,
        description="e.g. 'no change', 'trim 2pp', 'raise target by 2pp'.",
    )
    risks_surfaced: list[str] = Field(default_factory=list)
    risks_resolved: list[str] = Field(default_factory=list)
