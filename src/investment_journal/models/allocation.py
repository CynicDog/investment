"""Allocation: target weights + per-position daily DCA $ as configured at the broker."""

from datetime import date
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class DCA(BaseModel):
    cadence: Literal["daily-weekday"]
    total_per_day_usd: float = Field(gt=0)


class Position(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    name: str = Field(min_length=1)
    sector: str = Field(min_length=1)
    target_pct: float = Field(gt=0, le=100)
    dca_per_day_usd: float = Field(ge=0)
    role: str = Field(min_length=1)


class Allocation(BaseModel):
    plan_version: int = Field(ge=1)
    adopted: date
    notes: str = ""
    dca: DCA
    positions: list[Position]

    @model_validator(mode="after")
    def _check_totals(self) -> "Allocation":
        weight_sum = sum(p.target_pct for p in self.positions)
        if abs(weight_sum - 100) > 0.01:
            raise ValueError(f"target_pct must sum to 100, got {weight_sum}")
        dca_sum = sum(p.dca_per_day_usd for p in self.positions)
        if abs(dca_sum - self.dca.total_per_day_usd) > 0.01:
            raise ValueError(
                f"sum of dca_per_day_usd ({dca_sum}) != dca.total_per_day_usd "
                f"({self.dca.total_per_day_usd})"
            )
        tickers = [p.ticker for p in self.positions]
        if len(tickers) != len(set(tickers)):
            raise ValueError("duplicate ticker in positions")
        return self

    @classmethod
    def load(cls, path) -> "Allocation":
        with open(path) as f:
            return cls.model_validate(yaml.safe_load(f))

    def by_ticker(self, ticker: str) -> Position:
        for p in self.positions:
            if p.ticker == ticker:
                return p
        raise KeyError(ticker)
