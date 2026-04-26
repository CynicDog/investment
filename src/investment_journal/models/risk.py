"""Risk: a tracked concern surfaced in a review.

Source of truth = `risks/R-YYYY-MM-NNN-slug.yml` files in the repo.
Each risk also has a GitHub issue (label: `risk`) for discussion.
The Risks Index issue body is regenerated from these files.
"""

from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


Severity = Literal["low", "medium", "high"]
RiskStatus = Literal["open", "monitoring", "resolved"]


class Risk(BaseModel):
    id: str = Field(pattern=r"^R-\d{4}-\d{2}-\d{3}$")
    title: str = Field(min_length=1, max_length=120)
    ticker: Optional[str] = Field(
        default=None,
        description="None for portfolio-level risks; otherwise a ticker in allocation.yml.",
    )
    severity: Severity
    surfaced_in: str = Field(
        description=(
            "Origin reference: 'weekly-review/2026-W17', 'thesis-review/HALO-2026-04', "
            "'earnings/MKL-1Q26', or 'manual'."
        )
    )
    surfaced_on: date
    description: str = Field(min_length=1)
    monitor_for: str = Field(
        min_length=1,
        description="Concrete signals that would resolve this risk (events, disclosures, prints).",
    )
    status: RiskStatus = "open"
    resolved_on: Optional[date] = None
    resolution_note: Optional[str] = None
    issue_number: Optional[int] = Field(
        default=None,
        description="GitHub issue number tracking discussion of this risk.",
    )

    @model_validator(mode="after")
    def _check_resolution(self) -> "Risk":
        if self.status == "resolved":
            if self.resolved_on is None:
                raise ValueError("status='resolved' requires resolved_on")
            if not self.resolution_note:
                raise ValueError("status='resolved' requires resolution_note")
        else:
            if self.resolved_on is not None or self.resolution_note is not None:
                raise ValueError(
                    "resolved_on / resolution_note only apply when status='resolved'"
                )
        return self

    @classmethod
    def load(cls, path) -> "Risk":
        with open(path) as f:
            return cls.model_validate(yaml.safe_load(f))

    @classmethod
    def load_all(cls, dir_path: Path) -> list["Risk"]:
        if not dir_path.exists():
            return []
        risks = []
        for p in sorted(dir_path.glob("R-*.yml")):
            risks.append(cls.load(p))
        return risks

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            self.model_dump(mode="json", exclude_none=False),
            sort_keys=False,
            allow_unicode=True,
        )
