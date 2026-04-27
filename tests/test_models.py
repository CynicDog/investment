"""Smoke tests for the DSL: every model validates and rejects malformed input."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from investment_journal import (
    Allocation,
    DCAFill,
    DCAHistory,
    DCATracker,
    Dossier,
    EarningsEvent,
    Mark,
    Risk,
    ThesisReview,
    WeeklyReview,
)
from investment_journal.models.dca_tracker import DCATick
from investment_journal.models.earnings_event import EarningsRecap
from investment_journal.models.weekly_review import (
    Catalyst,
    DCASnapshot,
    PositionUpdate,
)
from investment_journal.render import (
    render_capital_flow_sankey,
    render_dca_pnl,
    render_dca_pnl_issue_block,
    render_dca_tracker,
    render_earnings_event,
    render_risk_issue,
    render_risks_index,
    render_thesis_review,
    render_weekly_review,
)


REPO = Path(__file__).resolve().parents[1]


def test_allocation_loads_real_file() -> None:
    a = Allocation.load(REPO / "portfolio" / "allocation.yml")
    assert sum(p.target_pct for p in a.positions) == pytest.approx(100.0, abs=0.01)
    assert sum(p.dca_per_day_usd for p in a.positions) == a.dca.total_per_day_usd


def test_allocation_rejects_bad_total() -> None:
    a = Allocation.load(REPO / "portfolio" / "allocation.yml")
    bad = a.model_dump(mode="python")
    bad["positions"][0]["target_pct"] = bad["positions"][0]["target_pct"] + 1
    with pytest.raises(ValidationError):
        Allocation.model_validate(bad)


def test_every_dossier_validates() -> None:
    for p in (REPO / "portfolio" / "positions").glob("[A-Z]*.md"):
        Dossier.from_file(p)


def test_risk_open_and_resolved() -> None:
    open_risk = Risk(
        id="R-2026-04-001",
        title="HALO single-deal dependency on Vertex Hypercon expansion",
        ticker="HALO",
        severity="medium",
        surfaced_in="weekly-review/2026-W17",
        surfaced_on=date(2026, 4, 26),
        description="The Vertex deal concentrates near-term Hypercon royalty growth.",
        monitor_for="Vertex Phase II/III readouts; additional Hypercon licensee announcements.",
    )
    assert open_risk.status == "open"

    resolved = open_risk.model_copy(
        update={
            "status": "resolved",
            "resolved_on": date(2026, 7, 1),
            "resolution_note": "Second Hypercon licensee signed in June.",
        }
    )
    assert resolved.status == "resolved"

    with pytest.raises(ValidationError):
        open_risk.model_copy(update={"status": "resolved"}).model_validate(
            open_risk.model_copy(update={"status": "resolved"}).model_dump()
        )


def test_dca_tracker_must_start_on_monday() -> None:
    DCATracker.fresh(date(2026, 4, 27))  # Monday
    with pytest.raises(ValidationError):
        DCATracker.fresh(date(2026, 4, 28))  # Tuesday


def test_dca_fill_executed_requires_price_and_shares() -> None:
    DCAFill(on_date=date(2026, 4, 21), ticker="VOO", executed=True,
            target_usd=32.0, price_usd=534.10, shares=32.0 / 534.10)
    DCAFill(on_date=date(2026, 4, 21), ticker="VOO", executed=False, target_usd=32.0)
    with pytest.raises(ValidationError):
        DCAFill(on_date=date(2026, 4, 21), ticker="VOO", executed=True, target_usd=32.0)
    with pytest.raises(ValidationError):
        DCAFill(on_date=date(2026, 4, 21), ticker="VOO", executed=False,
                target_usd=32.0, price_usd=534.10, shares=0.06)


def test_dca_history_aggregations_and_render() -> None:
    h = DCAHistory()
    monday = date(2026, 4, 20)
    # Two executed VOO fills + one missed day.
    h.upsert(DCAFill(on_date=monday, ticker="VOO", executed=True,
                     target_usd=32.0, price_usd=500.0, shares=32.0 / 500.0))
    h.upsert(DCAFill(on_date=date(2026, 4, 21), ticker="VOO", executed=True,
                     target_usd=32.0, price_usd=400.0, shares=32.0 / 400.0))
    h.upsert(DCAFill(on_date=date(2026, 4, 22), ticker="VOO", executed=False, target_usd=32.0))
    # Idempotent upsert (overwrites the missed-day entry, no duplicate).
    h.upsert(DCAFill(on_date=date(2026, 4, 22), ticker="VOO", executed=False, target_usd=32.0))
    assert sum(1 for f in h.fills if f.on_date == date(2026, 4, 22)) == 1
    # Cost basis = 32 + 32; shares = 32/500 + 32/400.
    assert h.cost_basis("VOO") == pytest.approx(64.0)
    assert h.shares_held("VOO") == pytest.approx(32.0 / 500.0 + 32.0 / 400.0)
    h.marks["VOO"] = Mark(price_usd=600.0, as_of=date(2026, 4, 25))
    pnl_abs, pnl_pct = h.unrealized_pnl("VOO", 600.0)
    assert pnl_abs > 0
    assert pnl_pct > 0
    out = render_dca_pnl(h, today=date(2026, 4, 26))
    assert "DCA P&L" in out
    assert "VOO" in out
    block = render_dca_pnl_issue_block(h, week_of=monday, today=date(2026, 4, 26))
    assert "<!-- pnl-start -->" in block
    assert "<!-- pnl-end -->" in block
    # In-week fills appear; out-of-week fill is filtered (none here, but check date ordering).
    assert "2026-04-20" in block
    assert "2026-04-22" in block


def test_render_smoke() -> None:
    a = Allocation.load(REPO / "portfolio" / "allocation.yml")
    assert "sankey-beta" in render_capital_flow_sankey(a)

    t = DCATracker.fresh(date(2026, 4, 27))
    out = render_dca_tracker(t)
    assert "Mon 2026-04-27" in out

    r = Risk(
        id="R-2026-04-001",
        title="Test",
        ticker="HALO",
        severity="high",
        surfaced_in="manual",
        surfaced_on=date(2026, 4, 26),
        description="d",
        monitor_for="m",
    )
    assert "R-2026-04-001" in render_risk_issue(r)
    assert "Open (1)" in render_risks_index([r])

    wr = WeeklyReview(
        iso_week="2026-W17",
        generated_on=date(2026, 4, 26),
        dca=DCASnapshot(this_week=4, trailing_4w=[5, 5, 4, 5]),
        per_position={
            "VOO": PositionUpdate(
                ticker="VOO",
                news_bullets=["Index up 1.8% on ceasefire ([cite](http://x))"],
                valuation_line="Fwd P/E ~21x ([cite](http://y))",
                thesis_status="still-holds",
                thesis_status_note="Range intact.",
            )
        },
        catalysts_30d=[Catalyst(when=date(2026, 5, 5), ticker="ETN", event="Q1 earnings")],
        risks_surfaced=[r.id],
    )
    out = render_weekly_review(wr, {r.id: r})
    assert "Weekly review 2026-W17" in out
    assert "4/5" in out

    tr = ThesisReview(
        ticker="HALO",
        month="2026-04",
        verdict="still-holds",
        verdict_note="Vertex deal validates the platform.",
        action="no change",
    )
    assert "HALO 2026-04" in render_thesis_review(tr)

    e = EarningsEvent(
        ticker="MKL",
        quarter="1Q26",
        expected_date=date(2026, 4, 29),
        timing="post-close",
        recap=EarningsRecap(
            revenue="Q1 26 revenue $X.XB +Y% YoY",
            eps="EPS $Z.ZZ adj",
            guidance="reiterated",
            sources=["http://primary"],
        ),
    )
    out = render_earnings_event(e)
    assert "Earnings: MKL 1Q26" in out
    assert "Recap" in out
