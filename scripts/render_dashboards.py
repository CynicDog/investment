#!/usr/bin/env python3
"""
Regenerate the sankey dashboard from allocation.yml using the investment_journal DSL.

Deterministic, no network. Writes:
  - portfolio/dashboards/dca-flow.md   (sankey: daily $ → sector → ticker)

Usage:
    uv run python scripts/render_dashboards.py
"""

from pathlib import Path

from investment_journal import Allocation
from investment_journal.render import render_capital_flow_sankey


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOCATION_PATH = REPO_ROOT / "portfolio" / "allocation.yml"
DASHBOARDS_DIR = REPO_ROOT / "portfolio" / "dashboards"


def main() -> int:
    allocation = Allocation.load(ALLOCATION_PATH)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    (DASHBOARDS_DIR / "dca-flow.md").write_text(render_capital_flow_sankey(allocation))
    print(f"Rendered sankey for {len(allocation.positions)} positions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
