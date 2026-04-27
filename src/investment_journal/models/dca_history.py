"""Cumulative DCA fill history + cost-basis / mark-to-market accounting.

Storage shape (`portfolio/dca_history.json`):

    {
      "fills": [
        {"on_date": "2026-04-21", "ticker": "VOO", "executed": true,
         "target_usd": 32.0, "price_usd": 534.10, "shares": 0.0599},
        {"on_date": "2026-04-22", "ticker": "VOO", "executed": false,
         "target_usd": 32.0}
      ],
      "marks": {
        "VOO": {"price_usd": 545.00, "as_of": "2026-04-25"}
      }
    }

A fill is keyed unique on (on_date, ticker). `executed=True` means the user
ticked the matching weekday box on the dca-tracker issue and the script
captured a closing price for that date. `executed=False` is a journal entry
for a missed/unticked weekday (Toss outage, holiday, manual skip).

`price_usd` is the daily close on `on_date`; if `on_date` was a non-trading
day, the writer falls back to the most recent prior trading day's close.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DCAFill(BaseModel):
    on_date: date
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    executed: bool
    target_usd: float = Field(ge=0, description="USD amount the allocation says we'd DCA on this day.")
    price_usd: Optional[float] = Field(default=None, description="Closing price used for the fill.")
    shares: Optional[float] = Field(default=None, description="target_usd / price_usd, fractional.")

    @model_validator(mode="after")
    def _coherent(self) -> "DCAFill":
        if self.executed:
            if self.price_usd is None or self.shares is None:
                raise ValueError("executed=True requires price_usd and shares")
            if self.price_usd <= 0:
                raise ValueError("price_usd must be positive when executed")
        else:
            if self.price_usd is not None or self.shares is not None:
                raise ValueError("executed=False must have null price_usd and shares")
        return self


class Mark(BaseModel):
    price_usd: float = Field(gt=0)
    as_of: date


class DCAHistory(BaseModel):
    fills: list[DCAFill] = Field(default_factory=list)
    marks: dict[str, Mark] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "DCAHistory":
        if not Path(path).exists():
            return cls()
        with open(path) as f:
            return cls.model_validate(json.load(f))

    def save(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.model_dump_json(indent=2) + "\n")

    def get(self, on_date: date, ticker: str) -> Optional[DCAFill]:
        for f in self.fills:
            if f.on_date == on_date and f.ticker == ticker:
                return f
        return None

    def upsert(self, fill: DCAFill) -> None:
        for i, f in enumerate(self.fills):
            if f.on_date == fill.on_date and f.ticker == fill.ticker:
                self.fills[i] = fill
                return
        self.fills.append(fill)

    def tickers(self) -> list[str]:
        return sorted({f.ticker for f in self.fills if f.executed})

    def cost_basis(self, ticker: str) -> float:
        return sum(f.target_usd for f in self.fills if f.ticker == ticker and f.executed)

    def shares_held(self, ticker: str) -> float:
        return sum((f.shares or 0.0) for f in self.fills if f.ticker == ticker and f.executed)

    def fills_count(self, ticker: str) -> int:
        return sum(1 for f in self.fills if f.ticker == ticker and f.executed)

    def market_value(self, ticker: str, mark: float) -> float:
        return self.shares_held(ticker) * mark

    def unrealized_pnl(self, ticker: str, mark: float) -> tuple[float, float]:
        """Returns (absolute_usd, percent). 0/0 → (0, 0)."""
        cb = self.cost_basis(ticker)
        if cb == 0:
            return 0.0, 0.0
        mv = self.market_value(ticker, mark)
        return mv - cb, (mv / cb - 1.0) * 100.0

    def fills_in_week(self, monday: date) -> list[DCAFill]:
        from datetime import timedelta
        end = monday + timedelta(days=4)
        return sorted(
            (f for f in self.fills if monday <= f.on_date <= end),
            key=lambda f: (f.on_date, f.ticker),
        )
