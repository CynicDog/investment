"""Horizon plan: a 3-phase roadmap that governs the 3-year DCA journey.

Source of truth = `portfolio/horizon_plan.yml`.
User-edited (like allocation.yml). Automation reads it; never writes it unless
the user explicitly asks Claude to update it.

File shape:

    horizon_version: 1
    started_on: 2026-05-03
    total_dca_per_day_usd: 100

    phases:
      - phase: 1
        name: Accumulate
        start: 2026-05-03
        end: 2027-05-03
        objective: |
          Build positions per allocation plan v4. No discretionary changes unless
          a thesis breaks or a high-severity risk triggers a scenario.
        decision_gates:
          - question: All 6 positions still hold thesis?
            answered: false
          - question: Any watchlist candidate ready to add?
            answered: false
          - question: DCA budget increase warranted?
            answered: false
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class DecisionGate(BaseModel):
    question: str = Field(min_length=1)
    answered: bool = False
    answer_note: Optional[str] = None

    @model_validator(mode="after")
    def _check_note(self) -> "DecisionGate":
        if self.answered and not self.answer_note:
            raise ValueError("answered=true requires answer_note")
        return self


class HorizonPhase(BaseModel):
    phase: int = Field(ge=1, le=10)
    name: str = Field(min_length=1)
    start: date
    end: date
    objective: str = Field(min_length=1)
    decision_gates: list[DecisionGate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_dates(self) -> "HorizonPhase":
        if self.end <= self.start:
            raise ValueError(f"Phase {self.phase}: end must be after start")
        return self

    @property
    def is_complete(self) -> bool:
        return all(g.answered for g in self.decision_gates)

    @property
    def gates_answered(self) -> int:
        return sum(1 for g in self.decision_gates if g.answered)


class HorizonPlan(BaseModel):
    horizon_version: int = Field(ge=1)
    started_on: date
    total_dca_per_day_usd: float = Field(gt=0)
    phases: list[HorizonPhase] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_phases(self) -> "HorizonPlan":
        phases_sorted = sorted(self.phases, key=lambda p: p.phase)
        nums = [p.phase for p in phases_sorted]
        if nums != list(range(1, len(nums) + 1)):
            raise ValueError("phase numbers must be consecutive starting at 1")
        return self

    @property
    def current_phase(self) -> HorizonPhase:
        today = date.today()
        for phase in sorted(self.phases, key=lambda p: p.phase):
            if phase.start <= today <= phase.end:
                return phase
        last = max(self.phases, key=lambda p: p.phase)
        return last

    @classmethod
    def load(cls, path) -> "HorizonPlan":
        with open(path) as f:
            return cls.model_validate(yaml.safe_load(f))

    def save(self, path) -> None:
        data = self.model_dump(mode="python")
        data["started_on"] = data["started_on"].isoformat()
        for phase in data["phases"]:
            phase["start"] = phase["start"].isoformat()
            phase["end"] = phase["end"].isoformat()
        Path(path).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)
        )
