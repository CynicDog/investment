#!/usr/bin/env python3
"""
Record DCA fills from a tracker issue and refresh cumulative P&L.

Triggered by the `dca-tracker-record.yml` workflow on `issues.edited`.
Reads the current state of the tracker issue body, joins it against
`portfolio/allocation.yml` for the per-ticker daily target, fetches
closing prices (Alpha Vantage TIME_SERIES_DAILY) for any new (date, ticker)
pairs not yet in `portfolio/dca_history.json`, fetches the latest close per
ticker for mark-to-market, then re-renders:

    portfolio/dca_history.json          (storage)
    portfolio/dashboards/dca-pnl.md     (full dashboard)
    issue body                          (compact P&L block, between markers)

Idempotent: re-runs do not duplicate fills, do not re-fetch prices that are
already stored, and produce a no-op git diff if nothing changed.

Usage:
    uv run python scripts/record_dca_fills.py --issue 42

Environment:
    GH_TOKEN              GitHub token.
    GITHUB_REPOSITORY     OWNER/REPO.
    ALPHAVANTAGE_API_KEY  Required for any price fetch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from investment_journal import Allocation, DCAFill, DCAHistory, Mark
from investment_journal.render import (
    PNL_BLOCK_END,
    PNL_BLOCK_START,
    render_dca_pnl,
    render_dca_pnl_issue_block,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOCATION_PATH = REPO_ROOT / "portfolio" / "allocation.yml"
HISTORY_PATH = REPO_ROOT / "portfolio" / "dca_history.json"
DASHBOARD_PATH = REPO_ROOT / "portfolio" / "dashboards" / "dca-pnl.md"

WEEKDAY_LINE_RE = re.compile(
    r"^- \[(?P<box>[ xX])\]\s+(?P<weekday>Mon|Tue|Wed|Thu|Fri)\s+(?P<date>\d{4}-\d{2}-\d{2})",
    re.MULTILINE,
)
WEEK_OF_RE = re.compile(r"week of \*\*(\d{4}-\d{2}-\d{2})\*\*")
DISCLAIMER_LINE = "_Personal journal. Not financial advice._"


def gh(*args: str, check: bool = True) -> str:
    res = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if check and res.returncode != 0:
        sys.stderr.write(f"gh {' '.join(args)} failed:\n{res.stderr}")
        sys.exit(res.returncode)
    return res.stdout


def fetch_issue(repo: str, number: int) -> dict:
    out = gh(
        "issue", "view", str(number), "-R", repo, "--json", "number,title,body,labels"
    )
    return json.loads(out)


def is_dca_tracker(issue: dict) -> bool:
    return any(lbl["name"] == "dca-tracker" for lbl in issue.get("labels", []))


class AlphaVantage:
    """Minimal Alpha Vantage TIME_SERIES_DAILY client. One HTTP call per ticker
    fetches ~100 days of closes; we serve both historical date lookups and the
    latest mark from the same payload."""

    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache: dict[str, dict[date, float]] = {}

    def _series(self, symbol: str) -> dict[date, float]:
        if symbol in self._cache:
            return self._cache[symbol]
        url = (
            self.BASE
            + "?"
            + urllib.parse.urlencode(
                {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "compact",
                    "apikey": self.api_key,
                }
            )
        )
        sys.stderr.write(f"alpha-vantage: fetching {symbol}\n")
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        if "Time Series (Daily)" not in data:
            note = (
                data.get("Note")
                or data.get("Information")
                or data.get("Error Message")
                or str(data)[:200]
            )
            raise RuntimeError(
                f"Alpha Vantage did not return daily series for {symbol}: {note}"
            )
        series: dict[date, float] = {}
        for k, v in data["Time Series (Daily)"].items():
            try:
                series[date.fromisoformat(k)] = float(v["4. close"])
            except (KeyError, ValueError):
                continue
        self._cache[symbol] = series
        time.sleep(1.0)  # be nice to the free tier
        return series

    def close_on_or_before(
        self, symbol: str, target: date, max_lookback_days: int = 7
    ) -> tuple[date, float]:
        """Return (resolved_date, close). Walks back up to max_lookback_days from target
        to find the nearest prior trading day if target is a non-trading day."""
        series = self._series(symbol)
        for offset in range(max_lookback_days + 1):
            d = target - timedelta(days=offset)
            if d in series:
                return d, series[d]
        raise RuntimeError(
            f"No close for {symbol} within {max_lookback_days}d of {target}; "
            f"series spans {min(series)}..{max(series)}"
        )

    def latest(self, symbol: str) -> tuple[date, float]:
        series = self._series(symbol)
        latest_date = max(series)
        return latest_date, series[latest_date]


def parse_week_of(body: str) -> date:
    m = WEEK_OF_RE.search(body)
    if not m:
        raise ValueError("Could not find 'week of **YYYY-MM-DD**' in issue body.")
    return date.fromisoformat(m.group(1))


def parse_ticks(body: str) -> list[tuple[date, bool]]:
    """Returns [(on_date, executed), ...] in order."""
    out: list[tuple[date, bool]] = []
    for m in WEEKDAY_LINE_RE.finditer(body):
        out.append((date.fromisoformat(m.group("date")), m.group("box").lower() == "x"))
    return out


def inject_pnl_block(body: str, block: str) -> str:
    """Replace `<!-- pnl-start --> ... <!-- pnl-end -->` if present, else insert
    just before the disclaimer footer (or append if no footer)."""
    if PNL_BLOCK_START in body and PNL_BLOCK_END in body:
        pre, _, rest = body.partition(PNL_BLOCK_START)
        _, _, post = rest.partition(PNL_BLOCK_END)
        return pre.rstrip() + "\n\n" + block + "\n" + post.lstrip("\n")
    if DISCLAIMER_LINE in body:
        idx = body.index(DISCLAIMER_LINE)
        return body[:idx].rstrip() + "\n\n" + block + "\n\n" + body[idx:]
    return body.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = ap.parse_args()
    if not args.repo:
        sys.stderr.write("--repo OWNER/REPO required (or set GITHUB_REPOSITORY).\n")
        return 2

    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        sys.stderr.write("ALPHAVANTAGE_API_KEY env var not set; cannot fetch prices.\n")
        return 2

    issue = fetch_issue(args.repo, args.issue)
    if not is_dca_tracker(issue):
        sys.stderr.write(
            f"issue #{args.issue} is not labeled dca-tracker; nothing to do.\n"
        )
        return 0

    body = issue["body"] or ""
    week_of = parse_week_of(body)
    ticks = parse_ticks(body)
    if not ticks:
        sys.stderr.write("No weekday checkbox lines found in body.\n")
        return 0

    allocation = Allocation.load(ALLOCATION_PATH)
    targets = {
        p.ticker: p.dca_per_day_usd
        for p in allocation.positions
        if p.dca_per_day_usd > 0
    }

    history = DCAHistory.load(HISTORY_PATH)
    av = AlphaVantage(api_key)
    today = date.today()

    new_or_changed = 0
    for on_date, executed in ticks:
        if on_date > today:
            continue
        for ticker, target_usd in targets.items():
            existing = history.get(on_date, ticker)
            if executed:
                if existing and existing.executed and existing.price_usd is not None:
                    continue
                resolved_date, close = av.close_on_or_before(ticker, on_date)
                if resolved_date != on_date:
                    sys.stderr.write(
                        f"note: {ticker} {on_date} is non-trading; using {resolved_date} close.\n"
                    )
                shares = target_usd / close
                history.upsert(
                    DCAFill(
                        on_date=on_date,
                        ticker=ticker,
                        executed=True,
                        target_usd=target_usd,
                        price_usd=close,
                        shares=shares,
                    )
                )
                new_or_changed += 1
            else:
                if existing and not existing.executed:
                    continue
                history.upsert(
                    DCAFill(
                        on_date=on_date,
                        ticker=ticker,
                        executed=False,
                        target_usd=target_usd,
                    )
                )
                new_or_changed += 1

    for ticker in sorted(targets.keys()):
        try:
            mark_date, mark_close = av.latest(ticker)
        except RuntimeError as e:
            sys.stderr.write(f"warn: could not fetch latest for {ticker}: {e}\n")
            continue
        history.marks[ticker] = Mark(price_usd=mark_close, as_of=mark_date)

    history.save(HISTORY_PATH)
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(render_dca_pnl(history, today=today))

    block = render_dca_pnl_issue_block(history, week_of=week_of, today=today)
    new_body = inject_pnl_block(body, block)
    if new_body != body:
        body_file = REPO_ROOT / ".dca_tracker_body.md"
        body_file.write_text(new_body)
        gh(
            "issue",
            "edit",
            str(args.issue),
            "-R",
            args.repo,
            "--body-file",
            str(body_file),
        )
        body_file.unlink(missing_ok=True)

    print(
        json.dumps(
            {
                "issue": args.issue,
                "fills_changed": new_or_changed,
                "total_fills": len(history.fills),
                "marks": {t: history.marks[t].price_usd for t in history.marks},
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
