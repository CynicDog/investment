#!/usr/bin/env python3
"""
Regenerate portfolio dashboards from allocation.yml + trades.csv.

Deterministic, no network. Updates:
  - portfolio/dashboards/allocation.md   (target pie, actual cost-basis pie, drift table)
  - portfolio/dashboards/dca-flow.md     (mermaid flowchart)
  - portfolio/dashboards/upcoming-earnings.md  (only the auto-marked placeholder; watcher fills the rest)
  - portfolio/positions/{TICKER}.md      (only the <!-- trades-start --> ... <!-- trades-end --> block,
                                          and the "At a glance" cost-basis row)
  - README.md                            (only the <!-- portfolio-start --> ... <!-- portfolio-end --> block)

Usage:
    python scripts/render_dashboards.py
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "render_dashboards.py needs PyYAML. Install with: pip install pyyaml\n"
    )
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOCATION_PATH = REPO_ROOT / "portfolio" / "allocation.yml"
TRADES_PATH = REPO_ROOT / "portfolio" / "trades.csv"
POSITIONS_DIR = REPO_ROOT / "portfolio" / "positions"
DASHBOARDS_DIR = REPO_ROOT / "portfolio" / "dashboards"
README_PATH = REPO_ROOT / "README.md"

PORTFOLIO_BLOCK_START = "<!-- portfolio-start -->"
PORTFOLIO_BLOCK_END = "<!-- portfolio-end -->"
TRADES_BLOCK_START = "<!-- trades-start -->"
TRADES_BLOCK_END = "<!-- trades-end -->"


# ---------- IO ----------

def load_allocation() -> dict[str, Any]:
    with ALLOCATION_PATH.open() as f:
        return yaml.safe_load(f)


def load_trades() -> list[dict[str, str]]:
    if not TRADES_PATH.exists():
        return []
    with TRADES_PATH.open(newline="") as f:
        return list(csv.DictReader(f))


# ---------- math ----------

def cost_basis_by_ticker(trades: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """
    Returns {ticker: {"shares": x, "cost": y}}.
    BUY: shares += s, cost += s*p + fee.
    SELL: shares -= s, cost -= s*p (reduce basis pro-rata at avg). Fees on sells add to cost (they offset proceeds in reality, but for journal weight purposes we treat fees as cost added).
    DIV: ignored for cost-basis weight (cash distribution, handled separately).
    """
    agg: dict[str, dict[str, float]] = defaultdict(lambda: {"shares": 0.0, "cost": 0.0})
    for t in trades:
        if not t.get("ticker"):
            continue
        ticker = t["ticker"].strip().upper()
        action = t["action"].strip().upper()
        try:
            shares = float(t["shares"] or 0)
            price = float(t["price"] or 0)
            fee = float(t["fee"] or 0)
        except ValueError:
            continue
        row = agg[ticker]
        if action == "BUY":
            row["shares"] += shares
            row["cost"] += shares * price + fee
        elif action == "SELL":
            # Reduce shares & basis pro-rata at running avg cost.
            if row["shares"] > 0:
                avg = row["cost"] / row["shares"]
                row["cost"] -= avg * shares
                row["shares"] -= shares
                row["cost"] += fee  # fees on sales added to cost
        elif action == "DIV":
            # Cash dividend; ignored for weight computation here.
            pass
    return dict(agg)


def actual_weights(holdings: dict[str, dict[str, float]]) -> dict[str, float]:
    total = sum(h["cost"] for h in holdings.values() if h["cost"] > 0)
    if total <= 0:
        return {}
    return {tkr: 100.0 * h["cost"] / total for tkr, h in holdings.items() if h["cost"] > 0}


# ---------- markdown helpers ----------

def replace_block(text: str, marker_start: str, marker_end: str, new_inner: str) -> str:
    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        re.DOTALL,
    )
    replacement = f"{marker_start}\n{new_inner.strip()}\n{marker_end}"
    if pattern.search(text):
        return pattern.sub(replacement, text)
    # If markers are missing, append them at the end.
    return text.rstrip() + f"\n\n{replacement}\n"


def fmt_pct(x: float) -> str:
    return f"{x:.2f}"


# ---------- renderers ----------

def render_allocation_md(allocation: dict, weights: dict[str, float]) -> str:
    today = date.today().isoformat()
    positions = allocation["positions"]
    cash = allocation.get("cash", {})
    cash_pct = cash.get("target_pct", 0)

    target_pie_lines = [f'    "{p["ticker"]}" : {p["target_pct"]}' for p in positions]
    if cash_pct:
        target_pie_lines.append(f'    "Cash" : {cash_pct}')
    target_pie = "\n".join(target_pie_lines)

    if weights:
        actual_pie_lines = []
        for p in positions:
            v = weights.get(p["ticker"], 0.0)
            if v > 0:
                actual_pie_lines.append(f'    "{p["ticker"]}" : {fmt_pct(v)}')
        actual_pie = "\n".join(actual_pie_lines) if actual_pie_lines else '    "No trades yet" : 100'
        actual_block = (
            "```mermaid\n"
            f"pie showData title Actual cost-basis allocation (as of {today})\n"
            f"{actual_pie}\n"
            "```\n"
        )
    else:
        actual_block = (
            "_No trades logged yet. Actual allocation pie will appear after the first trade is recorded "
            "via the trade-log issue template._\n"
        )

    drift_rows = []
    for p in positions:
        actual = weights.get(p["ticker"], 0.0)
        drift = actual - p["target_pct"]
        drift_rows.append(
            f'| {p["ticker"]} | {p["target_pct"]:.0f} | {fmt_pct(actual)} | {drift:+.2f} |'
        )
    if cash_pct:
        # Cash actual we don't track here without a cash ledger — leave blank.
        drift_rows.append(f'| Cash | {cash_pct:.0f} | — | — |')
    drift_table = (
        "| Ticker | Target % | Actual % | Drift (pp) |\n"
        "|---|---|---|---|\n"
        + "\n".join(drift_rows)
    )

    return f"""# Allocation

_Auto-generated by `scripts/render_dashboards.py`. Do not edit by hand._

## Target

```mermaid
pie showData title Target allocation
{target_pie}
```

## Actual (cost-basis)

{actual_block}

## Drift

{drift_table}

> Drift uses cost-basis weights (deterministic from `trades.csv`). Market-value drift is reported in the weekly review issue.
"""


def render_dca_flow_md(allocation: dict) -> str:
    total = allocation["dca"]["total_per_day_usd"]
    lines = [f'flowchart LR\n  A["Daily ${total}"]']
    for p in allocation["positions"]:
        lines.append(f'  A --> {p["ticker"]}["{p["ticker"]} ${p["dca_per_day_usd"]}"]')
    cash = allocation.get("cash", {})
    if cash.get("daily_set_aside_usd"):
        lines.append(f'  A --> CASH["Cash ${cash["daily_set_aside_usd"]}"]')
    diagram = "\n".join(lines)
    return f"""# DCA flow

_Auto-generated by `scripts/render_dashboards.py`. Do not edit by hand._

```mermaid
{diagram}
```
"""


def render_upcoming_earnings_md_placeholder() -> str:
    return """# Upcoming earnings

_Populated by `.github/workflows/earnings-watcher.yml`. Until the first run, this is empty._

```mermaid
gantt
    title Upcoming earnings (placeholder)
    dateFormat YYYY-MM-DD
    section Pending
    Run earnings-watcher to populate :a1, 2026-04-26, 1d
```
"""


def render_position_trades_block(ticker: str, trades: list[dict[str, str]]) -> str:
    rows = [t for t in trades if t.get("ticker", "").upper() == ticker.upper()]
    if not rows:
        return "_No trades logged yet for this ticker._"
    header = "| Date | Action | Shares | Price | Fee | Notes |\n|---|---|---|---|---|---|"
    body_lines = []
    for r in rows:
        body_lines.append(
            f'| {r["date"]} | {r["action"]} | {r["shares"]} | {r["price"]} | {r["fee"]} | {r.get("notes","")} |'
        )
    return header + "\n" + "\n".join(body_lines)


def render_readme_block(allocation: dict, weights: dict[str, float], holdings: dict[str, dict[str, float]]) -> str:
    today = date.today().isoformat()
    target_rows = []
    for p in allocation["positions"]:
        actual = weights.get(p["ticker"], 0.0)
        drift = actual - p["target_pct"]
        h = holdings.get(p["ticker"], {"shares": 0.0, "cost": 0.0})
        target_rows.append(
            f'| {p["ticker"]} | {p["name"]} | {p["target_pct"]:.0f}% | {fmt_pct(actual)}% | {drift:+.2f} | {h["shares"]:.4f} | ${h["cost"]:.2f} |'
        )
    table = (
        "| Ticker | Name | Target | Actual (cost-basis) | Drift (pp) | Shares | Total cost |\n"
        "|---|---|---|---|---|---|---|\n"
        + "\n".join(target_rows)
    )
    pie = "\n".join(f'    "{p["ticker"]}" : {p["target_pct"]}' for p in allocation["positions"])
    cash_pct = allocation.get("cash", {}).get("target_pct", 0)
    if cash_pct:
        pie += f'\n    "Cash" : {cash_pct}'

    return f"""_Last refreshed: {today}_

```mermaid
pie showData title Target allocation
{pie}
```

{table}

See [`portfolio/dashboards/allocation.md`](portfolio/dashboards/allocation.md) for the full breakdown including the actual cost-basis pie."""


# ---------- top-level ----------

def main() -> int:
    allocation = load_allocation()
    trades = load_trades()
    holdings = cost_basis_by_ticker(trades)
    weights = actual_weights(holdings)

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    (DASHBOARDS_DIR / "allocation.md").write_text(render_allocation_md(allocation, weights))
    (DASHBOARDS_DIR / "dca-flow.md").write_text(render_dca_flow_md(allocation))

    upcoming_path = DASHBOARDS_DIR / "upcoming-earnings.md"
    if not upcoming_path.exists():
        upcoming_path.write_text(render_upcoming_earnings_md_placeholder())

    # Update each position file's trades block.
    for p in allocation["positions"]:
        ticker = p["ticker"]
        pos_path = POSITIONS_DIR / f"{ticker}.md"
        if not pos_path.exists():
            continue
        text = pos_path.read_text()
        new_block = render_position_trades_block(ticker, trades)
        text = replace_block(text, TRADES_BLOCK_START, TRADES_BLOCK_END, new_block)
        pos_path.write_text(text)

    # Update README portfolio block.
    if README_PATH.exists():
        text = README_PATH.read_text()
        text = replace_block(
            text,
            PORTFOLIO_BLOCK_START,
            PORTFOLIO_BLOCK_END,
            render_readme_block(allocation, weights, holdings),
        )
        README_PATH.write_text(text)

    print(f"Rendered dashboards. {len(trades)} trade row(s) processed; {len(weights)} ticker(s) with positive cost basis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
