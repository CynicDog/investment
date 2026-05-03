"""Risk: a tracked concern surfaced in a review.

Source of truth = `risks/R-YYYY-MM-NNN.md` files in the repo.
Each file is yaml frontmatter (metadata) + markdown body (Description /
Monitor for / Resolution sections). Each risk also has a GitHub issue
(label `risk`) for discussion. The Risks Index issue body is regenerated
from these files.

File shape:

    ---
    id: R-2026-04-001
    title: ...
    ticker: HLNE                 # optional; omit for portfolio-level
    severity: medium
    surfaced_in: weekly-review/2026-W17
    surfaced_on: 2026-04-26
    status: open                 # open | monitoring | resolved
    resolved_on: 2026-07-01      # only when status == resolved
    issue_number: 31
    ---

    ## Description

    Multi-paragraph markdown ...

    ## Monitor for

    - bullet
    - bullet

    ## Resolution           <!-- only when resolved -->

    Why and how it resolved.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


Severity = Literal["low", "medium", "high"]
RiskStatus = Literal["open", "monitoring", "resolved"]


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("file must start with '---' frontmatter delimiter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("frontmatter is not terminated by '---'")
    fm = yaml.safe_load(text[4:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return fm, body


def _section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)",
        re.M | re.S,
    )
    m = pattern.search(body)
    return m.group(1).strip() if m else ""


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
            "Origin: 'weekly-review/2026-W17', 'thesis-review/HALO-2026-04', "
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
    issue_number: Optional[int] = None

    @model_validator(mode="after")
    def _check_resolution(self) -> "Risk":
        if self.status == "resolved":
            if self.resolved_on is None:
                raise ValueError("status='resolved' requires resolved_on")
            if not self.resolution_note:
                raise ValueError(
                    "status='resolved' requires resolution_note (use the Resolution section)"
                )
        else:
            if self.resolved_on is not None or self.resolution_note is not None:
                raise ValueError(
                    "resolved_on / resolution_note only apply when status='resolved'"
                )
        return self

    @classmethod
    def from_markdown(cls, path: Path) -> "Risk":
        fm, body = _parse_frontmatter(Path(path).read_text())
        description = _section(body, "Description")
        monitor_for = _section(body, "Monitor for")
        resolution = _section(body, "Resolution")
        return cls.model_validate(
            {
                **fm,
                "description": description,
                "monitor_for": monitor_for,
                "resolution_note": resolution
                if (fm.get("status") == "resolved" and resolution)
                else None,
            }
        )

    @classmethod
    def load(cls, path) -> "Risk":
        return cls.from_markdown(Path(path))

    @classmethod
    def load_all(cls, dir_path: Path) -> list["Risk"]:
        if not dir_path.exists():
            return []
        return [cls.from_markdown(p) for p in sorted(dir_path.glob("R-*.md"))]

    def to_markdown(self) -> str:
        meta: dict = {
            "id": self.id,
            "title": self.title,
        }
        if self.ticker is not None:
            meta["ticker"] = self.ticker
        meta["severity"] = self.severity
        meta["surfaced_in"] = self.surfaced_in
        meta["surfaced_on"] = self.surfaced_on.isoformat()
        meta["status"] = self.status
        if self.status == "resolved" and self.resolved_on is not None:
            meta["resolved_on"] = self.resolved_on.isoformat()
        if self.issue_number is not None:
            meta["issue_number"] = self.issue_number

        fm = yaml.safe_dump(
            meta, sort_keys=False, allow_unicode=True, width=120
        ).strip()

        parts = [
            "---",
            fm,
            "---",
            "",
            "## Description",
            "",
            self.description.strip(),
            "",
            "## Monitor for",
            "",
            self.monitor_for.strip(),
            "",
        ]
        if self.status == "resolved":
            parts += [
                "## Resolution",
                "",
                (self.resolution_note or "").strip(),
                "",
            ]
        return "\n".join(parts)
