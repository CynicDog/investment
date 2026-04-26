#!/usr/bin/env python3
"""File a new Risk: validate via DSL, write `risks/<id>-<slug>.yml`, open a GitHub
discussion issue (label=risk), back-fill the issue number into the yaml, print
the result as JSON.

Used by Claude workflows (weekly-review, earnings-watcher) and by humans.

Usage:
    uv run python scripts/file_a_risk.py \\
        --title "..." \\
        --severity medium \\
        --surfaced-in weekly-review/2026-W17 \\
        --ticker HALO \\
        --description "..." \\
        --monitor-for "..."

Stdout (JSON, one line):
    {"id": "R-2026-04-001", "issue_number": 23, "path": "risks/R-2026-04-001-...-.yml"}
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

from investment_journal import Risk
from investment_journal.render import render_risk_issue


REPO_ROOT = Path(__file__).resolve().parents[1]
RISKS_DIR = REPO_ROOT / "risks"


def slugify(s: str, max_len: int = 40) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len].rstrip("-")


def next_id(today: date) -> str:
    prefix = f"R-{today.strftime('%Y-%m')}"
    existing_nums: list[int] = []
    if RISKS_DIR.exists():
        for p in RISKS_DIR.glob(f"{prefix}-*.yml"):
            m = re.match(rf"^{re.escape(prefix)}-(\d{{3}})", p.stem)
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
    ap.add_argument("--severity", required=True, choices=["low", "medium", "high"])
    ap.add_argument(
        "--surfaced-in",
        required=True,
        help="e.g. 'weekly-review/2026-W17', 'thesis-review/HALO-2026-04', 'earnings/MKL-1Q26', 'manual'",
    )
    ap.add_argument("--ticker", default=None, help="Optional. None = portfolio-level risk.")
    ap.add_argument("--description", required=True)
    ap.add_argument("--monitor-for", required=True, dest="monitor_for")
    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="OWNER/REPO. Defaults to $GITHUB_REPOSITORY.",
    )
    args = ap.parse_args()
    if not args.repo:
        sys.exit("--repo OWNER/REPO required (or set GITHUB_REPOSITORY).")

    RISKS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    rid = next_id(today)
    slug = slugify(args.title)
    path = RISKS_DIR / f"{rid}-{slug}.yml"

    risk = Risk(
        id=rid,
        title=args.title,
        ticker=args.ticker,
        severity=args.severity,
        surfaced_in=args.surfaced_in,
        surfaced_on=today,
        description=args.description,
        monitor_for=args.monitor_for,
    )
    path.write_text(risk.to_yaml())

    body_path = path.with_suffix(".body.tmp")
    body_path.write_text(render_risk_issue(risk))
    out = gh(
        "issue", "create", "-R", args.repo,
        "--title", f"Risk: {rid} — {args.title}",
        "--label", "risk",
        "--body-file", str(body_path),
    )
    body_path.unlink(missing_ok=True)
    issue_url = out.strip().splitlines()[-1] if out else ""
    issue_n = int(issue_url.rsplit("/", 1)[-1]) if "/" in issue_url else 0

    risk_with_issue = risk.model_copy(update={"issue_number": issue_n})
    path.write_text(risk_with_issue.to_yaml())

    print(json.dumps(
        {"id": rid, "issue_number": issue_n, "path": str(path.relative_to(REPO_ROOT)), "url": issue_url}
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
