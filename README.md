# Investment journal

Personal portfolio journal. Daily DCA runs at **Toss** (which doesn't expose a trade-history API), so the repo tracks **intent** (target weights, daily DCA $ split), **confirmation** (a weekly DCA-tracker issue with Mon–Fri checkboxes), and **risks** (every concern surfaced in a review becomes a versioned `risks/<id>.md` plus a child discussion issue, aggregated in a pinned **Risks Index**). Claude GitHub Action handles weekly reviews, earnings events, monthly thesis re-checks, and risk filing.

> _Personal journal. Not financial advice._

## How it works

- **DSL** — `src/investment_journal/` — Pydantic models + renderers for every artifact (allocation, dossier, risks, weekly/thesis review, earnings event, DCA tracker, codified tone). Source of truth for shape.
- **`portfolio/allocation.yml`** — target weights and per-ticker daily DCA $ (mirrors what's configured at Toss).
- **`portfolio/positions/*.md`** — one dossier per holding (thesis, risks, catalysts, valuation, earnings log). Validated by `Dossier`.
- **`risks/R-*.md`** — one markdown file per risk (yaml frontmatter + body). Filed via `scripts/file_a_risk.py`. Resolved by editing `status: resolved` and adding a `## Resolution` section.
- **`portfolio/dashboards/dca-flow.md`** — auto-rendered sankey (Daily $ → sector → ticker).
- **GitHub Issues** are the activity log: weekly review, monthly thesis reviews, earnings events, DCA tracker, per-risk discussions, plus the pinned Risks Index.

## Workflows

| Workflow | When | What it does |
|---|---|---|
| `weekly-review.yml` | Fri 21:30 UTC | Opens a weekly review issue (per-ticker updates, DCA tally, catalyst calendar, risks delta). Files new risks via `file_a_risk.py`; commits the new markdown. |
| `earnings-watcher.yml` | Daily 13:00 UTC | Opens earnings issues 7 days ahead; posts recaps after the call; may file thesis-impacting risks. |
| `dca-tracker.yml` | Sun 22:00 UTC (~Mon 07 KST) | Closes prior week's tracker; opens a fresh Mon–Fri tracker for the week ahead. |
| `thesis-review.yml` | 1st of each month, 22:00 UTC | Opens one thesis-review issue per ticker for the just-completed month. Idempotent. |
| `risks-index-sync.yml` | Push to `risks/R-*.md` | Re-renders the pinned **Risks Index** issue body. Creates + pins it on first run. |
| `claude-mention.yml` | `@claude` in any issue/comment | Claude responds inline. |
| `update-dashboards.yml` | Push to `portfolio/**` | Regenerates the sankey dashboard. |
| `issue-checkbox-tick.yml` | Edit on `auto-tick`-labeled issues | Claude ticks verifiable `[ ]` items. Never on `dca-tracker`. |

## Local setup

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run pytest -q                       # validates the DSL + every dossier
uv run python scripts/render_dashboards.py    # regenerate the sankey
```

## Dashboards

- [Capital flow — sankey](portfolio/dashboards/dca-flow.md)
- [Upcoming earnings](portfolio/dashboards/upcoming-earnings.md) (managed by `earnings-watcher.yml`)

## Position dossiers

- [VOO — Vanguard S&P 500 ETF](portfolio/positions/VOO.md)
- [HLNE — Hamilton Lane](portfolio/positions/HLNE.md)
- [HALO — Halozyme Therapeutics](portfolio/positions/HALO.md)
- [ETN — Eaton Corp](portfolio/positions/ETN.md)
- [MKL — Markel Group](portfolio/positions/MKL.md)
- [IDCC — InterDigital](portfolio/positions/IDCC.md)
- [P — Everpure](portfolio/positions/P.md)

## Risks

The pinned **Risks Index** issue is auto-rendered from `risks/R-*.md`. To file a risk by hand:

```bash
uv run python scripts/file_a_risk.py \
  --title "..." --severity medium \
  --surfaced-in "manual" \
  --ticker HALO \
  --description "..." --monitor-for "..."
```

To resolve, edit the yaml: `status: resolved`, add `resolved_on` + `resolution_note`, push.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for how the system is wired and [`CLAUDE.md`](CLAUDE.md) for the agent guide.
