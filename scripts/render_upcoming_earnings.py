#!/usr/bin/env python3
"""
Regenerate `portfolio/dashboards/upcoming-earnings.md` from open `earnings`
GitHub issues.

Lists open issues via `gh`, parses ticker/quarter from each title and
expected_date/timing from each body, then renders a sorted table of events
within the configured horizon (default 90 days).

Usage:
    uv run python scripts/render_upcoming_earnings.py [--repo OWNER/REPO] [--horizon 90]

Environment:
    GH_TOKEN              GitHub token (provided by Actions or `gh auth`).
    GITHUB_REPOSITORY     Default for --repo when running in Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from investment_journal.models.earnings_event import EarningsEvent
from investment_journal.render import render_upcoming_earnings


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "portfolio" / "dashboards" / "upcoming-earnings.md"

TITLE_RE = re.compile(r"^Earnings:\s+([A-Z][A-Z0-9.-]{0,9})\s+([1-4]Q\d{2})\s*$")
EXPECTED_RE = re.compile(
    r"^Expected:\s+\*\*(\d{4}-\d{2}-\d{2})\*\*"
    r"(?:\s+\((pre-market|post-close|intraday)\))?",
    re.MULTILINE,
)


def gh(*args: str) -> str:
    res = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        sys.stderr.write(f"gh {' '.join(args)} failed:\n{res.stderr}")
        sys.exit(res.returncode)
    return res.stdout


def parse_issue(item: dict) -> tuple[EarningsEvent, int] | None:
    title = (item.get("title") or "").strip()
    m = TITLE_RE.match(title)
    if not m:
        sys.stderr.write(
            f"skip #{item['number']}: title not earnings-shaped: {title!r}\n"
        )
        return None
    ticker, quarter = m.group(1), m.group(2)
    body = item.get("body") or ""
    em = EXPECTED_RE.search(body)
    if not em:
        sys.stderr.write(f"skip #{item['number']}: no `Expected:` line in body\n")
        return None
    try:
        expected = date.fromisoformat(em.group(1))
    except ValueError:
        sys.stderr.write(f"skip #{item['number']}: bad date {em.group(1)!r}\n")
        return None
    timing = em.group(2) or "unknown"
    try:
        ev = EarningsEvent(
            ticker=ticker,
            quarter=quarter,
            expected_date=expected,
            timing=timing,
        )
    except Exception as e:
        sys.stderr.write(f"skip #{item['number']}: {e}\n")
        return None
    return ev, int(item["number"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="OWNER/REPO. Defaults to $GITHUB_REPOSITORY.",
    )
    ap.add_argument(
        "--horizon",
        type=int,
        default=90,
        help="Days from today to include (default: 90).",
    )
    args = ap.parse_args()
    if not args.repo:
        sys.stderr.write("--repo OWNER/REPO required (or set GITHUB_REPOSITORY).\n")
        return 2

    out = gh(
        "issue",
        "list",
        "-R",
        args.repo,
        "--label",
        "earnings",
        "--state",
        "open",
        "--limit",
        "100",
        "--json",
        "number,title,body",
    )
    items = json.loads(out or "[]")

    events: list[tuple[EarningsEvent, int | None]] = []
    for it in items:
        parsed = parse_issue(it)
        if parsed is not None:
            events.append(parsed)

    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = render_upcoming_earnings(
        events,
        today=date.today(),
        horizon_days=args.horizon,
        repo=args.repo,
    )
    DASHBOARD_PATH.write_text(body)
    print(
        f"Rendered {len(events)}/{len(items)} earnings event(s) → "
        f"{DASHBOARD_PATH.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
