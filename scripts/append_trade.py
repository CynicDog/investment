#!/usr/bin/env python3
"""
Parse a trade-log GitHub Issue body (rendered from .github/ISSUE_TEMPLATE/trade-log.yml)
and append a row to portfolio/trades.csv.

GitHub renders issue-form fields with `### Field name` headers followed by the value.
We extract by header. After successful append, print a markdown summary to stdout for
the workflow to comment back on the issue.

Usage (in workflow):
    python scripts/append_trade.py --body-file issue_body.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRADES_PATH = REPO_ROOT / "portfolio" / "trades.csv"

EXPECTED_FIELDS = ["Ticker", "Date", "Action", "Shares", "Price", "Fee", "Notes"]


def extract_field(body: str, field: str) -> str:
    """
    Return the text under `### {field}` up to the next `### ` or end.
    Trims and treats GitHub's `_No response_` placeholder as empty.
    """
    pattern = rf"^###\s+{re.escape(field)}\s*\n(.*?)(?=^###\s|\Z)"
    m = re.search(pattern, body, flags=re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    val = m.group(1).strip()
    if val == "_No response_":
        return ""
    return val


def normalize_date(s: str) -> str:
    s = s.strip()
    if not s:
        return date.today().isoformat()
    # Accept YYYY-MM-DD only.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError(f"date must be YYYY-MM-DD, got: {s!r}")
    return s


def normalize_action(s: str) -> str:
    s = s.strip().upper()
    if s not in ("BUY", "SELL", "DIV"):
        raise ValueError(f"action must be BUY, SELL, or DIV; got: {s!r}")
    return s


def normalize_number(s: str, field: str, allow_zero: bool = True) -> str:
    s = s.strip().replace(",", "").lstrip("$")
    if not s:
        if allow_zero:
            return "0"
        raise ValueError(f"{field} required")
    try:
        f = float(s)
    except ValueError as e:
        raise ValueError(f"{field} must be numeric, got: {s!r}") from e
    if f < 0:
        raise ValueError(f"{field} must be non-negative")
    return f"{f:g}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file", required=True, help="Path to file containing the issue body")
    args = ap.parse_args()

    body = Path(args.body_file).read_text()

    raw = {f: extract_field(body, f) for f in EXPECTED_FIELDS}

    try:
        ticker = raw["Ticker"].strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker):
            raise ValueError(f"ticker looks invalid: {ticker!r}")
        row = {
            "date": normalize_date(raw["Date"]),
            "ticker": ticker,
            "action": normalize_action(raw["Action"]),
            "shares": normalize_number(raw["Shares"], "Shares", allow_zero=False),
            "price": normalize_number(raw["Price"], "Price"),
            "fee": normalize_number(raw["Fee"], "Fee"),
            "notes": raw["Notes"].replace("\n", " ").strip(),
        }
    except ValueError as e:
        sys.stderr.write(f"trade parse error: {e}\n")
        print(f"::error::Trade parse error: {e}")
        return 1

    # Append.
    write_header = not TRADES_PATH.exists() or TRADES_PATH.stat().st_size == 0
    fieldnames = ["date", "ticker", "action", "shares", "price", "fee", "notes"]
    with TRADES_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    # Summary for workflow to post back.
    print("Trade appended:\n")
    print("| Date | Ticker | Action | Shares | Price | Fee | Notes |")
    print("|---|---|---|---|---|---|---|")
    print(f"| {row['date']} | {row['ticker']} | {row['action']} | {row['shares']} | {row['price']} | {row['fee']} | {row['notes']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
