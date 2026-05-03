"""Watchlist: quality-screened candidates being tracked for potential portfolio addition.

Source of truth = `portfolio/watchlist.yml`.
User-maintained; automation never writes it directly (Claude may suggest additions,
but the user must accept and push the change).

File shape (list of entries):

    watchlist:
      - ticker: MSFT
        name: Microsoft
        sector: Technology / Cloud
        added_on: 2026-05-15
        conviction: medium
        thesis_note: >-
          Dominant cloud + AI platform; Azure share gains consistent. Watching for
          multiple-compression to a more attractive entry point.
        screen_results:
          - bucket: cash
            passed: true
            note: Net cash $XX B; FCF yield ~2.5% TTM (10-K FY25)
          - bucket: finance
            passed: true
            note: D/E 0.4; interest coverage >20x (10-K FY25)
          - bucket: stability
            passed: true
            note: Revenue CAGR 15% (FY21-25); EPS beat 12 of last 16 quarters
          - bucket: profitability
            passed: true
            note: Gross margin 70%, ROIC 28% TTM (10-K FY25)
        status: watching
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


QualityBucket = Literal["cash", "finance", "stability", "profitability"]
WatchlistStatus = Literal["watching", "priority", "parked", "added-to-portfolio"]
Conviction = Literal["high", "medium", "low"]


class ScreenResult(BaseModel):
    bucket: QualityBucket
    passed: bool
    note: Optional[str] = Field(
        default=None,
        description="One-line citation or rationale. Cite primary source (10-K, 10-Q, IR).",
    )


class WatchlistEntry(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    name: str = Field(min_length=1)
    sector: str = Field(min_length=1)
    added_on: date
    conviction: Conviction = "medium"
    thesis_note: str = Field(
        min_length=1,
        description="2-3 sentences: why interesting, what would make it addable.",
    )
    screen_results: list[ScreenResult] = Field(default_factory=list)
    status: WatchlistStatus = "watching"

    @property
    def buckets_passed(self) -> list[QualityBucket]:
        return [r.bucket for r in self.screen_results if r.passed]

    @property
    def all_buckets_passed(self) -> bool:
        return set(self.buckets_passed) == {
            "cash",
            "finance",
            "stability",
            "profitability",
        }


class Watchlist(BaseModel):
    watchlist: list[WatchlistEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, path) -> "Watchlist":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls.model_validate(raw)

    def save(self, path) -> None:
        data = self.model_dump(mode="python")
        for entry in data["watchlist"]:
            entry["added_on"] = entry["added_on"].isoformat()
        Path(path).write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120)
        )

    def by_status(self, status: WatchlistStatus) -> list[WatchlistEntry]:
        return [e for e in self.watchlist if e.status == status]

    def by_conviction(self, conviction: Conviction) -> list[WatchlistEntry]:
        return [e for e in self.watchlist if e.conviction == conviction]

    def ready_candidates(self) -> list[WatchlistEntry]:
        """Entries that passed all 4 quality buckets and are still watching/priority."""
        return [
            e
            for e in self.watchlist
            if e.all_buckets_passed and e.status in ("watching", "priority")
        ]
