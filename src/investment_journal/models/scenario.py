"""Scenario: an if-then decision rule that governs when and how the portfolio changes.

Source of truth = `portfolio/scenarios/S-YYYY-MM-NNN.md` files.
Each file is yaml frontmatter (metadata) + markdown body (Trigger / Action / Context sections).
Each scenario also has a GitHub issue (label `scenario`) for discussion.

File shape:

    ---
    id: S-2026-05-001
    title: Close P if no AI data infra evidence by 12 months
    ticker: P                        # optional; omit for portfolio-level
    trigger_type: time-gate
    status: active                   # active | triggered | resolved | dismissed
    triggered_on: 2027-05-03         # only when status == triggered or resolved
    issue_number: 42
    ---

    ## Trigger

    At the 12-month mark (2027-05-03), P has not disclosed material AI data infrastructure
    revenue, partnerships, or product direction beyond the FY2025 pivot announcement.

    ## Action

    Begin close process: halt DCA, file a `close_position` request, redistribute $8/day
    to the highest-conviction position at the time.

    ## Context

    P was added as a speculative 8% allocation on the AI data infra thesis pivot. The thesis
    requires evidence of execution within the first year. Without it, the position becomes
    pure speculation with no fundamental anchor.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, model_validator


TriggerType = Literal[
    "metric",           # quantitative threshold (e.g., FCF yield < X%)
    "thesis-verdict",   # thesis review returns 'no' or 'partially'
    "watchlist",        # watchlist candidate passes all quality buckets
    "time-gate",        # specific date or horizon milestone reached
    "dca-shift",        # portfolio-level DCA budget change condition
    "drip",             # dividend income crosses a reinvestment threshold
]

ScenarioStatus = Literal["active", "triggered", "resolved", "dismissed"]


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


class Scenario(BaseModel):
    id: str = Field(pattern=r"^S-\d{4}-\d{2}-\d{3}$")
    title: str = Field(min_length=1, max_length=120)
    ticker: Optional[str] = Field(
        default=None,
        description="None for portfolio-level scenarios; otherwise a ticker.",
    )
    trigger_type: TriggerType
    trigger_description: str = Field(min_length=1)
    action_description: str = Field(min_length=1)
    context: str = ""
    status: ScenarioStatus = "active"
    triggered_on: Optional[date] = None
    resolution_note: Optional[str] = None
    issue_number: Optional[int] = None

    @model_validator(mode="after")
    def _check_status(self) -> "Scenario":
        if self.status in ("triggered", "resolved"):
            if self.triggered_on is None:
                raise ValueError(f"status='{self.status}' requires triggered_on")
        else:
            if self.triggered_on is not None:
                raise ValueError("triggered_on only applies when status is triggered or resolved")
        if self.status == "resolved" and not self.resolution_note:
            raise ValueError("status='resolved' requires resolution_note")
        return self

    @classmethod
    def from_markdown(cls, path: Path) -> "Scenario":
        fm, body = _parse_frontmatter(Path(path).read_text())
        trigger_description = _section(body, "Trigger")
        action_description = _section(body, "Action")
        context = _section(body, "Context")
        return cls.model_validate({
            **fm,
            "trigger_description": trigger_description,
            "action_description": action_description,
            "context": context,
        })

    @classmethod
    def load(cls, path) -> "Scenario":
        return cls.from_markdown(Path(path))

    @classmethod
    def load_all(cls, dir_path: Path) -> list["Scenario"]:
        if not dir_path.exists():
            return []
        return [cls.from_markdown(p) for p in sorted(dir_path.glob("S-*.md"))]

    def to_markdown(self) -> str:
        meta: dict = {"id": self.id, "title": self.title}
        if self.ticker is not None:
            meta["ticker"] = self.ticker
        meta["trigger_type"] = self.trigger_type
        meta["status"] = self.status
        if self.triggered_on is not None:
            meta["triggered_on"] = self.triggered_on.isoformat()
        if self.issue_number is not None:
            meta["issue_number"] = self.issue_number

        fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=120).strip()

        parts = [
            "---",
            fm,
            "---",
            "",
            "## Trigger",
            "",
            self.trigger_description.strip(),
            "",
            "## Action",
            "",
            self.action_description.strip(),
            "",
        ]
        if self.context:
            parts += [
                "## Context",
                "",
                self.context.strip(),
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
