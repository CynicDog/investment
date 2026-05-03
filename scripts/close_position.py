#!/usr/bin/env python3
"""Close an active position dossier: rewrite its header to CLOSED format and
print a summary of any open risks that still reference the ticker.

Does NOT touch allocation.yml — the caller (Claude or human) updates that file
separately with the new weights.

Usage:
    uv run python scripts/close_position.py \\
        --ticker MKL \\
        --closed-on 2026-05-03 \\
        --reason "Position cleared; DCA redistributed to HLNE (+$3), HALO (+$3), IDCC (+$5)."

Stdout (JSON, one line):
    {"ticker": "MKL", "closed_on": "2026-05-03", "dossier_updated": true, "open_risks": [...]}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT / "src"))

from investment_journal.models.dossier import Dossier, HEADER_LINE_RE, CLOSED_HEADER_LINE_RE
from investment_journal.models.risk import Risk


def main() -> None:
    parser = argparse.ArgumentParser(description="Close an active position dossier.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--closed-on", required=True, help="YYYY-MM-DD")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    closed_on = date.fromisoformat(args.closed_on)
    dossier_path = REPO_ROOT / "portfolio" / "positions" / f"{ticker}.md"

    if not dossier_path.exists():
        print(f"ERROR: {dossier_path} not found", file=sys.stderr)
        sys.exit(1)

    dossier = Dossier.from_file(dossier_path)
    if dossier.status == "closed":
        print(f"ERROR: {ticker} dossier is already marked CLOSED (closed_on={dossier.closed_on})", file=sys.stderr)
        sys.exit(1)

    # Rewrite header line in the raw markdown
    text = dossier_path.read_text()
    lines = text.splitlines(keepends=True)
    new_header = (
        f"> Status: CLOSED &nbsp;•&nbsp; Closed: {closed_on.isoformat()}"
        f" &nbsp;•&nbsp; Sector: {dossier.sector}"
        f" &nbsp;•&nbsp; Last reviewed: {dossier.last_reviewed.isoformat()}\n"
    )
    replaced = False
    new_lines = []
    for line in lines:
        if not replaced and HEADER_LINE_RE.match(line.rstrip()):
            new_lines.append(new_header)
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        print("ERROR: could not locate active header line to replace", file=sys.stderr)
        sys.exit(1)

    dossier_path.write_text("".join(new_lines))

    # Validate the rewritten file loads correctly
    updated = Dossier.from_file(dossier_path)
    assert updated.status == "closed", "post-write validation failed: status != closed"

    # Collect open risks for this ticker
    risks_dir = REPO_ROOT / "risks"
    open_risks = [
        {"id": r.id, "title": r.title, "severity": r.severity, "issue_number": r.issue_number}
        for r in Risk.load_all(risks_dir)
        if r.ticker == ticker and r.status != "resolved"
    ]

    result = {
        "ticker": ticker,
        "closed_on": closed_on.isoformat(),
        "dossier_updated": True,
        "open_risks": open_risks,
    }

    if open_risks:
        print(
            f"WARNING: {len(open_risks)} open risk(s) still reference {ticker}. "
            "Resolve them manually: set status=resolved, resolved_on, and add a ## Resolution section.",
            file=sys.stderr,
        )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
