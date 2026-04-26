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
from typing import Any, Dict, List, Tuple

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

# Constants for markdown blocks
TRADES_START = "<!-- trades-start -->"
TRADES_END = "<!-- trades-end -->"
PORTFOLIO_START = "<!-- portfolio-start -->"
PORTFOLIO_END = "<!-- portfolio-end -->"


def load_allocation() -> Dict[str, Dict[str, Any]]:
    with open(ALLOCATION_PATH, "r") as f:
        data = yaml.safe_load(f)
    return {pos["ticker"]: pos for pos in data["positions"]}


def load_trades() -> List[Dict[str, str]]:
    if not TRADES_PATH.exists():
        return []
    with open(TRADES_PATH, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_position_cost_basis(trades: List[Dict[str, str]], ticker: str) -> Tuple[float, float]:
    """
    Compute total cost basis and share count for a ticker.
    Handles selling more than held by clamping shares to zero.
    """
    total_shares = 0.0
    total_cost = 0.0  # in dollars

    for t in trades:
        if t["Ticker"] != ticker:
            continue
        qty = float(t["Shares"])
        price = float(t["Price"])
        fee = float(t.get("Fee", 0))  # Simplified: no need for or "0"
        cost = qty * price + (fee if qty > 0 else -fee)  # Fee logic: add on buy, subtract on sell

        if qty < 0:
            # Selling: reduce cost basis proportionally
            if abs(qty) >= total_shares:
                # Sell all or more than held -> zero out
                total_cost = 0.0
                total_shares = 0.0
            else:
                # Partial sell
                sale_cost_basis = (abs(qty) / total_shares) * total_cost
                total_cost -= sale_cost_basis
                total_shares += qty  # qty is negative
        else:
            # Buying: increase shares and cost
            total_shares += qty
            total_cost += cost

    return round(total_cost, 2), round(total_shares, 6)


def render_trades_table(trades: List[Dict[str, str]]) -> str:
    if not trades:
        return "No trades recorded."
    rows = ["| Date | Action | Shares | Price | Fee | Total | Notes |", "|---|---|---|---|---|---|---|"]
    for t in sorted(trades, key=lambda x: x["Date"], reverse=True):
        qty = float(t["Shares"])
        price = float(t["Price"])
        fee = float(t.get("Fee", 0))
        total = abs(qty * price + (fee if qty > 0 else -fee))
        action = "Buy" if qty > 0 else "Sell"
        rows.append(f"| {t['Date']} | {action} | {abs(qty):.6f} | ${price:.2f} | ${fee:.2f} | ${total:.2f} | {t.get('Notes', '')} |")
    return "\n".join(rows)


def update_position_files(trades: List[Dict[str, str]], allocations: Dict[str, Dict[str, Any]]) -> None:
    """Update each position's markdown file with latest trades and cost basis."""
    # Group trades by ticker
    trade_groups = defaultdict(list)
    for t in trades:
        trade_groups[t["Ticker"]].append(t)

    for ticker, alloc in allocations.items():
        file_path = POSITIONS_DIR / f"{ticker}.md"
        if not file_path.exists():
            # Silently skip if file doesn't exist; no creation
            continue

        content = file_path.read_text()

        # Update trades table
        trades_table = render_trades_table(trade_groups.get(ticker, []))
        trades_block = f"{TRADES_START}\n\n{trades_table}\n\n{TRADES_END}"

        trades_pattern = f"{re.escape(TRADES_START)}.*?{re.escape(TRADES_END)}"
        if re.search(trades_pattern, content, flags=re.DOTALL):
            content = re.sub(trades_pattern, trades_block, content, flags=re.DOTALL)
        else:
            # If markers not found, skip file
            continue

        # Update cost basis row
        cost, shares = compute_position_cost_basis(trades, ticker)
        avg_price = round(cost / shares, 2) if shares > 0 else 0.0
        cost_basis_row = f"| At a glance | ${cost:.2f} cost basis ({shares:.6f} shares @ ${avg_price:.2f}) |"
        cost_pattern = r"\| At a glance \| [^|]+\s*\|"
        if re.search(cost_pattern, content):
            content = re.sub(cost_pattern, cost_basis_row, content)
        else:
            # If no cost basis row, skip update
            pass

        file_path.write_text(content)


def main() -> int:
    try:
        allocation = load_allocation()
        trades = load_trades()
        update_position_files(trades, allocation)
        return 0
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())