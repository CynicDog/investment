"""Quantitative screener: numeric thresholds for each quality bucket.

Defines the pass/fail criteria used to evaluate watchlist candidates.
Claude (via watchlist-screen.yml) populates ScreenResult notes and passes/fails
based on these thresholds. Humans can override any individual result in watchlist.yml.

Threshold set is intentionally conservative — quality-first filter for long-horizon DCA
positions. Each bucket maps to a set of `MetricThreshold` rules. All rules in a bucket
must pass for the bucket to pass (AND logic within bucket; OR across buckets is not used).

Usage:
    from investment_journal.models.screener import THRESHOLDS, score_candidate

    results = score_candidate(metrics_dict, THRESHOLDS)
    # metrics_dict: {"fcf_yield_pct": 4.2, "net_cash_ratio": 0.15, ...}
    # returns: list[ScreenResult]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from investment_journal.models.watchlist import QualityBucket, ScreenResult


@dataclass(frozen=True)
class MetricThreshold:
    """One numeric check within a quality bucket."""
    metric_key: str
    label: str
    check: Callable[[float], bool]
    unit: str
    direction: str  # "above" | "below" | "range" — for display only


# ---------------------------------------------------------------------------
# Default threshold set — "quality-first" for 3-year DCA positions
# ---------------------------------------------------------------------------

THRESHOLDS: dict[QualityBucket, list[MetricThreshold]] = {
    "cash": [
        MetricThreshold(
            metric_key="fcf_yield_pct",
            label="FCF yield",
            check=lambda v: v >= 3.0,
            unit="%",
            direction="above 3%",
        ),
        MetricThreshold(
            metric_key="net_cash_ratio",
            label="Net cash / total assets",
            check=lambda v: v >= -0.30,   # net debt up to 30% of assets is acceptable
            unit="ratio",
            direction="≥ -0.30",
        ),
    ],
    "finance": [
        MetricThreshold(
            metric_key="debt_to_equity",
            label="Debt / equity",
            check=lambda v: v <= 2.0,
            unit="ratio",
            direction="below 2.0x",
        ),
        MetricThreshold(
            metric_key="interest_coverage",
            label="Interest coverage (EBIT/interest)",
            check=lambda v: v >= 3.0,
            unit="x",
            direction="above 3x",
        ),
        MetricThreshold(
            metric_key="current_ratio",
            label="Current ratio",
            check=lambda v: v >= 1.0,
            unit="ratio",
            direction="above 1.0",
        ),
    ],
    "stability": [
        MetricThreshold(
            metric_key="revenue_cagr_3y_pct",
            label="Revenue CAGR 3Y",
            check=lambda v: v >= 5.0,
            unit="%",
            direction="above 5%",
        ),
        MetricThreshold(
            metric_key="earnings_beat_rate_pct",
            label="EPS beat rate (last 8 quarters)",
            check=lambda v: v >= 60.0,
            unit="%",
            direction="above 60%",
        ),
    ],
    "profitability": [
        MetricThreshold(
            metric_key="gross_margin_pct",
            label="Gross margin",
            check=lambda v: v >= 30.0,
            unit="%",
            direction="above 30%",
        ),
        MetricThreshold(
            metric_key="roic_pct",
            label="ROIC",
            check=lambda v: v >= 10.0,
            unit="%",
            direction="above 10%",
        ),
        MetricThreshold(
            metric_key="roe_pct",
            label="ROE",
            check=lambda v: v >= 10.0,
            unit="%",
            direction="above 10%",
        ),
    ],
}


def score_candidate(
    metrics: dict[str, Optional[float]],
    thresholds: dict[QualityBucket, list[MetricThreshold]] = THRESHOLDS,
) -> list[ScreenResult]:
    """Score a candidate against all four quality buckets.

    Args:
        metrics: key → float value (or None if data unavailable). Keys must match
                 MetricThreshold.metric_key values defined in `thresholds`.
        thresholds: threshold set to use (defaults to THRESHOLDS).

    Returns:
        One ScreenResult per bucket. A bucket passes only when ALL its thresholds pass
        and none have missing data. Missing data → fail with a note flagging the gap.
    """
    results: list[ScreenResult] = []

    for bucket, rules in thresholds.items():
        lines: list[str] = []
        all_pass = True

        for rule in rules:
            val = metrics.get(rule.metric_key)
            if val is None:
                lines.append(f"{rule.label}: N/A (data missing)")
                all_pass = False
            elif rule.check(val):
                lines.append(f"{rule.label}: {val:.1f}{rule.unit} ✓ ({rule.direction})")
            else:
                lines.append(f"{rule.label}: {val:.1f}{rule.unit} ✗ (threshold: {rule.direction})")
                all_pass = False

        results.append(ScreenResult(
            bucket=bucket,
            passed=all_pass,
            note="; ".join(lines),
        ))

    return results


def metric_keys() -> list[str]:
    """All metric_key strings required for a full screen — useful as a data-fetch checklist."""
    keys: list[str] = []
    for rules in THRESHOLDS.values():
        for rule in rules:
            if rule.metric_key not in keys:
                keys.append(rule.metric_key)
    return keys
