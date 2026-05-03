"""Renderers: model → markdown."""

from investment_journal.render.dashboard import (
    PNL_BLOCK_END,
    PNL_BLOCK_START,
    render_capital_flow_sankey,
    render_dca_pnl,
    render_dca_pnl_issue_block,
    render_upcoming_earnings,
)
from investment_journal.render.issue_body import (
    render_dca_tracker,
    render_earnings_event,
    render_horizon_review,
    render_risk_issue,
    render_risks_index,
    render_scenario_issue,
    render_thesis_review,
    render_watchlist_issue,
    render_weekly_review,
)

__all__ = [
    "PNL_BLOCK_END",
    "PNL_BLOCK_START",
    "render_capital_flow_sankey",
    "render_dca_pnl",
    "render_dca_pnl_issue_block",
    "render_upcoming_earnings",
    "render_dca_tracker",
    "render_earnings_event",
    "render_horizon_review",
    "render_risk_issue",
    "render_risks_index",
    "render_scenario_issue",
    "render_thesis_review",
    "render_watchlist_issue",
    "render_weekly_review",
]
