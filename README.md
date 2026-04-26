# Investment journal

Personal portfolio journal. Daily DCA runs at **Toss** (which doesn't expose a trade-history API), so the repo tracks **intent** (target weights, daily DCA $ split) and **confirmation** (a weekly DCA-tracker issue with Mon–Fri checkboxes you tick once Toss confirms each fill). Claude GitHub Action handles weekly reviews, earnings events, and thesis re-checks.

> _Personal journal. Not financial advice._

## How it works

- **`portfolio/allocation.yml`** — target weights and per-ticker daily DCA amount (mirrors what's configured at Toss).
- **`portfolio/positions/*.md`** — one dossier per holding (thesis, risks, catalysts, valuation, earnings log).
- **`portfolio/dashboards/*.md`** — auto-rendered Mermaid visuals (pie, flowchart, sankey).
- **GitHub Issues** are the activity log:
  - Per-ticker dossier discussions (one pinned per holding).
  - Weekly DCA tracker — five `[ ]` Mon–Fri checkboxes, ticked by hand once Toss fills.
  - Earnings events, thesis reviews, weekly reviews. Many use `[ ]` items the Claude bot ticks when verifiable.

## Workflows

| Workflow | When | What it does |
|----------|------|--------------|
| `weekly-review.yml` | Fri 21:30 UTC | Opens a weekly review issue: per-ticker updates, DCA tally, catalyst calendar |
| `earnings-watcher.yml` | Daily 13:00 UTC | Opens earnings issues 7 days ahead; posts recaps after the call |
| `dca-tracker.yml` | Sun 22:00 UTC (~Mon 07 KST) | Closes prior week's tracker; opens a new Mon–Fri tracker for the week ahead |
| `claude-mention.yml` | `@claude` in any issue/comment | Claude responds inline |
| `update-dashboards.yml` | Push to `portfolio/**` | Regenerates dashboards + this README's portfolio block |
| `issue-checkbox-tick.yml` | Edit on `auto-tick`-labeled issues | Claude ticks verifiable `[ ]` items (never on dca-tracker) |

## Dashboards

- [Capital flow — sankey](portfolio/dashboards/dca-flow.md) — auto-generated from `allocation.yml`
- [Upcoming earnings](portfolio/dashboards/upcoming-earnings.md) — managed by `earnings-watcher.yml`

## Position dossiers

- [VOO — Vanguard S&P 500 ETF](portfolio/positions/VOO.md)
- [HLNE — Hamilton Lane](portfolio/positions/HLNE.md)
- [HALO — Halozyme Therapeutics](portfolio/positions/HALO.md)
- [ETN — Eaton Corp](portfolio/positions/ETN.md)
- [MKL — Markel Group](portfolio/positions/MKL.md)
- [IDCC — InterDigital](portfolio/positions/IDCC.md)

## Setup (one-time, after first push to GitHub)

1. **Add repo secret** `ANTHROPIC_API_KEY` (Settings → Secrets and variables → Actions).
2. **Workflow permissions**: Settings → Actions → General → set workflow permissions to *Read and write*, allow Actions to create PRs.
3. **Manually run each workflow once** via `workflow_dispatch` to confirm wiring:
   ```bash
   gh workflow run update-dashboards.yml
   gh workflow run weekly-review.yml
   gh workflow run earnings-watcher.yml
   ```
4. **Pin the position issues** + the latest weekly review.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for how rundowns are produced and [`CLAUDE.md`](CLAUDE.md) for the agent guide.
