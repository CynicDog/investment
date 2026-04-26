# CLAUDE.md — repo guide for Claude

This file is read on every Claude Code or Claude GitHub Action invocation. Read it before doing anything.

## What this repo is

A personal portfolio journal for an investor who DCAs daily at **Toss** (a Korean broker that exposes no trade-history API). Workflows track:

- **Intent** — target weights + per-ticker daily DCA $ in `portfolio/allocation.yml`.
- **Confirmation** — a weekly DCA tracker issue with Mon–Fri checkboxes the user ticks once Toss confirms each fill.
- **Theses & events** — per-position dossiers, monthly thesis review issues, per-quarter earnings issues, weekly review issues.
- **Risks** — every concern surfaced in a review becomes a versioned `risks/R-*.md` file plus a child discussion issue. A pinned `Risks Index` issue aggregates all open risks.

Not a brokerage account. Not financial advice.

## DSL (you must read and use it)

Everything the repo produces has a Pydantic schema in `src/investment_journal/`. Models:

| Model | File | Purpose |
|---|---|---|
| `Allocation`, `Position`, `DCA` | `models/allocation.py` | Validates `portfolio/allocation.yml`. Enforces weights sum to 100 and per-position DCA sums to total. |
| `Dossier` | `models/dossier.py` | Header + required-sections validator over `portfolio/positions/*.md`. Prose stays freeform markdown. |
| `Risk`, `Severity`, `RiskStatus` | `models/risk.py` | One markdown file per risk under `risks/<id>.md` (yaml frontmatter + body). Resolved risks must carry `resolved_on` + `resolution_note`. |
| `WeeklyReview`, `PositionUpdate`, `Catalyst`, `DCASnapshot`, `ThesisStatus` | `models/weekly_review.py` | Shape of a weekly review issue body. |
| `ThesisReview`, `ThesisVerdict` | `models/thesis_review.py` | Shape of a monthly thesis review issue body. |
| `EarningsEvent`, `EarningsRecap` | `models/earnings_event.py` | Shape of an earnings issue (pre-call prep + post-call recap). |
| `DCATracker`, `DCATick` | `models/dca_tracker.py` | Weekly Mon–Fri tracker. Construct via `DCATracker.fresh(monday)`. |
| `Tone`, `TONE_RULES`, `DISCLAIMER` | `models/tone.py` | Codified tone rules. Always append `DISCLAIMER` to top-level issue bodies. |

Renderers (`src/investment_journal/render/`) turn models into markdown:

```python
from investment_journal import Risk, WeeklyReview
from investment_journal.render import render_risk_issue, render_weekly_review

# Build a model, render, post
body = render_weekly_review(my_weekly_review, risks_lookup={r.id: r for r in all_risks})
```

When in doubt: `uv run python -c "from investment_journal import <Thing>; help(<Thing>)"`.

## Filing a risk

**Never write `risks/R-*.md` by hand from a workflow.** Use the helper:

```bash
uv run python scripts/file_a_risk.py \
  --title "HALO single-deal dependency on Vertex Hypercon expansion" \
  --severity medium \
  --surfaced-in "weekly-review/2026-W17" \
  --ticker HALO \
  --description "The 2026-04-07 Vertex deal concentrates near-term Hypercon royalty growth on a single counterparty's program execution." \
  --monitor-for "Vertex Phase II/III readouts on Hypercon-formulated assets; additional Hypercon licensee announcements."
```

The script picks the next free `R-YYYY-MM-NNN` id, writes `risks/<id>.md` (frontmatter + body), opens a child issue (label `risk`), back-fills the issue number into the file, and prints `{"id":"...","issue_number":N,...}` JSON to stdout. Reference the id in the parent review issue's Risks section so it shows up linked.

The workflow that called Claude (`weekly-review.yml`, `earnings-watcher.yml`) commits + pushes the new markdown file after Claude finishes, then runs `scripts/render_risks_index.py` inline to refresh the pinned **Risks Index** issue body.

## Layout

| Path | What it is | Who writes it |
|---|---|---|
| `pyproject.toml` / `uv.lock` | Project metadata + lockfile (uv) | User; locked by CI |
| `src/investment_journal/` | Pydantic DSL + renderers | User |
| `tests/test_models.py` | Smoke tests | User |
| `portfolio/allocation.yml` | Target weights + DCA $ | User only (rare) |
| `portfolio/positions/*.md` | Per-ticker dossier (thesis prose) | User + weekly review may append to `<!-- news-start --> ... <!-- news-end -->` block |
| `portfolio/dashboards/dca-flow.md` | Sankey, regenerated | `scripts/render_dashboards.py` only |
| `risks/R-*.md` | Risk records (one per risk) | `scripts/file_a_risk.py` (Claude or human) |
| `risks/README.md` | Format + lifecycle of risks | User |
| `docs/PROMPTS.md` | Centralized Claude prompts | User |
| `docs/METHODOLOGY.md` | How the system works | User |
| `README.md` | Front page | User |

## Tone for any output you produce

- Terse, factual, present tense. Bullets over paragraphs.
- No predictions ("X will…"). Frame as "as of {date}, X is reported / disclosed / expected per company guidance / consensus".
- No advice language. No "should buy / sell / recommend".
- Cite primary sources inline (10-K, 10-Q, 8-K, IR press release, transcript). Aggregator articles are last resort.
- Numbers: include unit (USD/%) and period (TTM, YoY, QoQ).
- If a number disagrees across sources, list both and flag the discrepancy.
- End every top-level issue body you author with `_Personal journal. Not financial advice._` (or import `DISCLAIMER` from the DSL).

## Issue labels

- `position` — per-ticker dossier discussion (currently unpinned by user choice)
- `weekly-review` — weekly review reports
- `earnings` — per-quarter earnings tracking
- `thesis-review` — monthly thesis re-check (one per ticker per month)
- `dca-tracker` — weekly DCA confirmation checklist
- `risk` — child discussion issue for one risk record (canonical state in `risks/<id>.md`)
- `risks-index` — the single pinned Risks Index issue
- `auto-tick` — eligible for `[ ]→[x]` automation by `issue-checkbox-tick.yml`

## What you must never do

1. **Never tick a `dca-tracker` issue.** Those represent real money — only the user confirms.
2. **Never edit `risks/R-*.md` by hand from a workflow.** Use `scripts/file_a_risk.py` to file new risks; for resolution, instruct the user to set `status: resolved` + `resolved_on` + `resolution_note` and push.
3. **Never edit `portfolio/allocation.yml`** unless the user explicitly states the new weights in the same turn.
4. **Never write `portfolio/dashboards/dca-flow.md` by hand.** It's regenerated by `scripts/render_dashboards.py`.
5. **Never push prices, EPS, or forecasts as facts** without citing the source. If you can't cite, mark `(unverified)`.
6. **Never close `position` issues.** Pinned dossiers, open indefinitely.
7. **Never modify `README.md`** unless explicitly asked.
8. **Never bypass the DSL.** Build a model and render with the supplied renderer rather than emitting hand-formatted markdown that mimics the schema.

## Useful commands

```bash
# Re-render the sankey dashboard
uv run python scripts/render_dashboards.py

# Regenerate the Risks Index issue body
uv run python scripts/render_risks_index.py

# Validate every dossier + allocation
uv run pytest -q

# Run all DSL smoke tests
uv run pytest tests/

# List open weekly reviews
gh issue list --label weekly-review --state open

# Current DCA tracker
gh issue list --label dca-tracker --state open
```

## Disclaimer

Personal journal. Positions, weights, and notes reflect personal opinion as of the date written and may be wrong, stale, or revised without notice. Not financial advice.
