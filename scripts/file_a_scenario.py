#!/usr/bin/env python3
"""File a new Scenario: validate via DSL, write `portfolio/scenarios/<id>.md`
(frontmatter + body), open a GitHub issue (label=scenario), back-fill the issue
number into the file, print the result as JSON.

Usage:
    uv run python scripts/file_a_scenario.py \\
        --title "Close P if no AI data infra evidence by 12 months" \\
        --trigger-type time-gate \\
        --ticker P \\
        --trigger "At the 12-month mark (2027-05-03), P has not disclosed material AI data infra revenue." \\
        --action "Halt DCA into P; run close_position.py; redistribute $8/day to highest-conviction position." \\
        --context "P was added as speculative 8% on AI data infra pivot thesis."

Stdout (JSON, one line):
    {"id": "S-2026-05-001", "issue_number": 55, "path": "portfolio/scenarios/S-2026-05-001.md"}
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

from investment_journal.models.scenario import Scenario, TriggerType
from investment_journal.render import render_scenario_issue


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = REPO_ROOT / "portfolio" / "scenarios"


def next_id(today: date) -> str:
    prefix = f"S-{today.strftime('%Y-%m')}"
    existing_nums: list[int] = []
    if SCENARIOS_DIR.exists():
        for p in SCENARIOS_DIR.glob(f"{prefix}-*.md"):
            m = re.match(rf"^{re.escape(prefix)}-(\d{{3}})$", p.stem)
            if m:
                existing_nums.append(int(m.group(1)))
    n = max(existing_nums, default=0) + 1
    return f"{prefix}-{n:03d}"


def gh(*args: str) -> str:
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"gh {' '.join(args)} failed:\n{res.stderr}")
        sys.exit(res.returncode)
    return res.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument(
        "--trigger-type", required=True, dest="trigger_type",
        choices=["metric", "thesis-verdict", "watchlist", "time-gate", "dca-shift", "drip"],
    )
    ap.add_argument("--ticker", default=None, help="Optional. None = portfolio-level scenario.")
    ap.add_argument("--trigger", required=True, dest="trigger_description",
                    help="Description of the trigger condition (when this fires).")
    ap.add_argument("--action", required=True, dest="action_description",
                    help="What to do when the trigger fires.")
    ap.add_argument("--context", default="", dest="context",
                    help="Optional background context.")
    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="OWNER/REPO. Defaults to $GITHUB_REPOSITORY.",
    )
    args = ap.parse_args()
    if not args.repo:
        sys.exit("--repo OWNER/REPO required (or set GITHUB_REPOSITORY).")

    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    sid = next_id(today)
    path = SCENARIOS_DIR / f"{sid}.md"

    scenario = Scenario(
        id=sid,
        title=args.title,
        ticker=args.ticker,
        trigger_type=args.trigger_type,
        trigger_description=args.trigger_description,
        action_description=args.action_description,
        context=args.context,
    )
    path.write_text(scenario.to_markdown())

    body_path = path.with_suffix(".body.tmp")
    body_path.write_text(render_scenario_issue(scenario))
    out = gh(
        "issue", "create", "-R", args.repo,
        "--title", f"Scenario: {sid} — {args.title}",
        "--label", "scenario",
        "--body-file", str(body_path),
    )
    body_path.unlink(missing_ok=True)
    issue_url = out.strip().splitlines()[-1] if out else ""
    issue_n = int(issue_url.rsplit("/", 1)[-1]) if "/" in issue_url else 0

    scenario_with_issue = scenario.model_copy(update={"issue_number": issue_n})
    path.write_text(scenario_with_issue.to_markdown())

    print(json.dumps(
        {"id": sid, "issue_number": issue_n, "path": str(path.relative_to(REPO_ROOT)), "url": issue_url}
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
