# Investment journal

Personal portfolio journal. Daily DCA runs at **Toss** (which doesn't expose a trade-history API), so the repo tracks **intent** (target weights, daily DCA $ split), **confirmation** (a weekly DCA-tracker issue with Mon–Fri checkboxes), **risks** (every concern surfaced in a review becomes a versioned `risks/<id>.md` plus a child discussion issue), and a **strategy layer** — a quality-screened watchlist, if-then scenario rules, and a 3-year horizon plan with phase gates. Claude GitHub Action handles weekly reviews, earnings events, monthly thesis re-checks, risk filing, candidate screening, and annual horizon review.

> _Personal journal. Not financial advice._

## How it works

- **DSL** — `src/investment_journal/` — Pydantic models + renderers for every artifact (allocation, dossier, risks, weekly/thesis review, earnings event, DCA tracker, watchlist, scenarios, horizon plan, codified tone). Source of truth for shape.
- **`portfolio/allocation.yml`** — target weights and per-ticker daily DCA $ (mirrors what's configured at Toss).
- **`portfolio/positions/*.md`** — one dossier per holding (thesis, risks, catalysts, valuation, earnings log). Validated by `Dossier`.
- **`risks/R-*.md`** — one markdown file per risk (yaml frontmatter + body). Filed via `scripts/file_a_risk.py`. Resolved by editing `status: resolved` and adding a `## Resolution` section.
- **`portfolio/watchlist.yml`** — quality-screened candidates across 4 factor buckets (cash, finance, stability, profitability). Screened monthly via Alpha Vantage.
- **`portfolio/scenarios/S-*.md`** — if-then decision rules filed via `scripts/file_a_scenario.py`. Trigger types: metric, thesis-verdict, watchlist, time-gate, dca-shift, drip.
- **`portfolio/horizon_plan.yml`** — 3-year roadmap with phases and decision gates. User-edited.
- **`portfolio/dashboards/`** — auto-rendered dashboards (sankey, DCA P&L, upcoming earnings).
- **GitHub Issues** are the activity log: weekly review, monthly thesis reviews, earnings events, DCA tracker, per-risk discussions, watchlist candidates, scenario tracking, horizon reviews, plus the pinned Risks Index.

## Workflows

| Workflow | When | What it does |
|---|---|---|
| `weekly-review.yml` | Fri 21:30 UTC | Opens a weekly review issue (per-ticker updates, DCA tally, catalyst calendar, risks delta). Files new risks via `file_a_risk.py`; commits the new markdown. |
| `earnings-watcher.yml` | Daily 13:00 UTC | Opens earnings prep issues 7 days ahead of calls. |
| `earnings-recap.yml` | Daily 13:30 UTC | Posts post-call recaps; may file thesis-impacting risks. |
| `dca-tracker.yml` | Sun 22:00 UTC (~Mon 07 KST) | Closes prior week's tracker; opens a fresh Mon–Fri tracker for the week ahead. |
| `dca-tracker-record.yml` | Edit on `dca-tracker` issues | Captures checkbox ticks; fetches Alpha Vantage closing prices; refreshes `dca_history.json` and the P&L dashboard. |
| `thesis-review.yml` | 1st of each month, 22:00 UTC | Opens one thesis-review issue per ticker for the just-completed month. Idempotent. |
| `watchlist-screen.yml` | 1st of each month, 23:00 UTC | Screens each `watching`/`priority` candidate via `screen_candidate.py` (Alpha Vantage); updates `watchlist.yml` screen results; upgrades to `priority` if all 4 buckets pass. |
| `horizon-review.yml` | May 3rd annually, 22:00 UTC | Opens a `horizon-review` issue for the current phase; walks decision gates and surfaces triggered scenarios. |
| `risks-index-sync.yml` | Push to `risks/R-*.md` | Re-renders the pinned **Risks Index** issue body. Creates + pins it on first run. |
| `update-dashboards.yml` | Push to `portfolio/**` | Regenerates the sankey and other dashboards. |
| `claude-mention.yml` | `@claude` in any issue/comment | Claude responds inline. |
| `issue-checkbox-tick.yml` | Edit on `auto-tick`-labeled issues | Claude ticks verifiable `[ ]` items. Never on `dca-tracker`. |

## Local setup

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run pytest -q                              # validates the DSL + every dossier
uv run python scripts/render_dashboards.py   # regenerate the sankey
```

## Dashboards

- [Capital flow — sankey](portfolio/dashboards/dca-flow.md)
- [DCA P&L](portfolio/dashboards/dca-pnl.md) (managed by `dca-tracker-record.yml`)
- [Upcoming earnings](portfolio/dashboards/upcoming-earnings.md) (managed by `earnings-watcher.yml`)

## Position dossiers

Active:

- [VOO — Vanguard S&P 500 ETF](portfolio/positions/VOO.md)
- [HLNE — Hamilton Lane](portfolio/positions/HLNE.md)
- [HALO — Halozyme Therapeutics](portfolio/positions/HALO.md)
- [ETN — Eaton Corp](portfolio/positions/ETN.md)
- [IDCC — InterDigital](portfolio/positions/IDCC.md)
- [P — Everpure](portfolio/positions/P.md)

Closed:

- [MKL — Markel Group](portfolio/positions/MKL.md) — closed 2026-05-03

## Risks

The pinned **Risks Index** issue is auto-rendered from `risks/R-*.md`. To file a risk:

```bash
uv run python scripts/file_a_risk.py \
  --title "..." --severity medium \
  --surfaced-in "manual" \
  --ticker HALO \
  --description "..." --monitor-for "..."
```

To resolve, edit the yaml: `status: resolved`, add `resolved_on` + `resolution_note`, push.

## Watchlist

Candidates are tracked in `portfolio/watchlist.yml`. The monthly `watchlist-screen.yml` workflow
scores each candidate via Alpha Vantage (requires `ALPHA_VANTAGE_API_KEY_2` secret). To add a candidate,
edit `watchlist.yml` with `status: watching` and leave `screen_results: []` — the workflow fills it in.

## Scenarios

Decision rules live in `portfolio/scenarios/S-*.md`. File one via the helper (never write the markdown by hand):

```bash
uv run python scripts/file_a_scenario.py \
  --title "..." \
  --trigger-type time-gate \   # metric | thesis-verdict | watchlist | time-gate | dca-shift | drip
  --ticker P \
  --trigger "Condition that causes this to fire." \
  --action "What to do when it fires." \
  --context "Optional background."
```

The script auto-assigns an ID (`S-YYYY-MM-NNN`), writes the file, opens a GitHub issue with label `scenario`,
and back-fills the issue number. To resolve, edit `status: resolved`, add `resolved_on` + `resolution_note`, push.

## Horizon plan

`portfolio/horizon_plan.yml` holds the 3-year roadmap (3 phases, decision gates per phase). User-edited only.
The annual `horizon-review.yml` workflow opens a review issue on each anniversary walking through the current
phase's decision gates and surfacing triggered scenarios.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for how the system is wired and [`CLAUDE.md`](CLAUDE.md) for the agent guide.
