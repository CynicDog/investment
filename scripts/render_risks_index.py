#!/usr/bin/env python3
"""
Re-render the body of the pinned "Risks Index" GitHub issue from `risks/R-*.md`.

If the Risks Index issue does not exist yet, it is created (and pinned).
Otherwise its body is replaced with the freshly rendered markdown.

The label `risks-index` marks the index issue (one per repo).

Usage:
    uv run python scripts/render_risks_index.py [--repo OWNER/REPO]

Environment:
    GH_TOKEN   GitHub token (provided by Actions or `gh auth`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from investment_journal import Risk
from investment_journal.render import render_risks_index


REPO_ROOT = Path(__file__).resolve().parents[1]
RISKS_DIR = REPO_ROOT / "risks"
INDEX_TITLE = "Risks Index"
INDEX_LABEL = "risks-index"


def gh(*args: str, check: bool = True) -> str:
    res = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and res.returncode != 0:
        sys.stderr.write(f"gh {' '.join(args)} failed:\n{res.stderr}")
        sys.exit(res.returncode)
    return res.stdout


def find_index_issue(repo: str) -> int | None:
    out = gh(
        "issue", "list", "-R", repo,
        "--label", INDEX_LABEL, "--state", "all", "--limit", "5",
        "--json", "number,title",
    )
    items = json.loads(out or "[]")
    for it in items:
        if it["title"] == INDEX_TITLE:
            return int(it["number"])
    return None


def write_body_file(body: str) -> Path:
    p = REPO_ROOT / "risks" / ".index_body.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="OWNER/REPO. Defaults to $GITHUB_REPOSITORY.",
    )
    args = ap.parse_args()
    if not args.repo:
        sys.stderr.write("--repo OWNER/REPO required (or set GITHUB_REPOSITORY).\n")
        return 2

    risks = Risk.load_all(RISKS_DIR)
    body = render_risks_index(risks)
    body_file = write_body_file(body)

    n = find_index_issue(args.repo)
    if n is None:
        out = gh(
            "issue", "create", "-R", args.repo,
            "--title", INDEX_TITLE,
            "--label", INDEX_LABEL,
            "--body-file", str(body_file),
        )
        url = out.strip().splitlines()[-1] if out else ""
        new_n = int(url.rsplit("/", 1)[-1]) if "/" in url else None
        print(f"Created Risks Index issue: {url}")
        if new_n is not None:
            gh("issue", "pin", str(new_n), "-R", args.repo, check=False)
            print(f"Pinned issue #{new_n}.")
    else:
        gh(
            "issue", "edit", str(n), "-R", args.repo,
            "--body-file", str(body_file),
        )
        print(f"Updated Risks Index issue #{n} ({len(risks)} risks; "
              f"{sum(1 for r in risks if r.status != 'resolved')} open).")

    body_file.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
