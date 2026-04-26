# Methodology

How rundowns and dashboards are produced. If you change any of the math or the workflow shape, update this file.

## Source-of-truth files

| File | Hand-edited? | Edited by automation? |
|---|---|---|
| `portfolio/allocation.yml` | Yes (rare, deliberate) | No |
| `portfolio/trades.csv` | **No** — only via trade-log issue + `append-trade.yml` | Yes (append-only) |
| `portfolio/positions/*.md` | Yes (thesis sections) | Yes (only auto-marked blocks: `trades-start/end`, `news-start/end`) |
| `portfolio/dashboards/*.md` | **No** — fully regenerated | Yes (`render_dashboards.py`) |
| `README.md` | Yes (outside `<!-- portfolio-start --> ... <!-- portfolio-end -->`) | Yes (inside markers) |

## Weight math

Two distinct weights are tracked.

### Cost-basis weight (deterministic)

Computed by `scripts/render_dashboards.py` from `trades.csv`:

```
running_shares[t]  = Σ shares (BUY) − Σ shares (SELL)
running_cost[t]    = Σ (shares × price + fee)  for BUYs
                   − Σ (avg_cost_at_sell × shares − fee)  for SELLs
weight[t]          = running_cost[t] / Σ running_cost
```

This is what the **Drift** column in `dashboards/allocation.md` and the README portfolio block use. It does not require a price feed and is reproducible offline.

### Market-value weight (point-in-time)

Computed only inside the weekly review issue, by Claude using web search for last close prices. It is reported as commentary, never written back to a file. If you want a persistent market-value series, that requires a price feed and is explicitly out of scope for v1.

### Cash

Cash is currently a target only. Actual cash held is not tracked in `trades.csv` (no cash ledger). Drift on cash is reported as `—` in the table. This is a deliberate v1 simplification.

## DCA accounting

`allocation.yml` declares per-ticker `dca_per_day_usd`. The DCA itself happens at the broker — this repo does not place orders. Each fill is logged via the trade-log issue template, which captures the actual shares/price/fee (likely close to but not exactly the targeted dollar amount, depending on broker fractional-share rounding).

## Workflow contracts

### `weekly-review.yml`
- **Reads**: `allocation.yml`, `trades.csv`, `dashboards/allocation.md`, all `positions/*.md`.
- **Writes**: a new GitHub issue labeled `weekly-review` titled `Weekly review YYYY-Www`.
- **Does not**: modify any tracked file. Even valuation/news updates to position files happen via a separate, explicit user action (or future workflow).

### `earnings-watcher.yml`
- **Reads**: `allocation.yml`, open earnings issues.
- **Writes**: opens earnings issues 7 days ahead; comments + edits issue body to tick `[x] Earnings released` / `[x] Recap published` after the call.
- **Does not**: modify position files directly. Thesis-impact updates remain a human decision.

### `update-dashboards.yml`
- **Reads**: `allocation.yml`, `trades.csv`.
- **Writes**: `dashboards/*.md`, the auto-blocks of `positions/*.md`, the auto-block of `README.md`.
- **No Claude involvement.** Pure deterministic renderer. Must remain so.

### `append-trade.yml`
- **Reads**: trade-log issue body.
- **Writes**: appends one row to `trades.csv`, comments confirmation, closes the issue.
- **No Claude involvement.**

### `issue-checkbox-tick.yml`
- **Triggers**: any edit/comment on an `auto-tick`-labeled issue.
- **Writes**: edits the issue body to flip `[ ] → [x]` for verifiable items only; posts one comment listing what was ticked and why.
- **Conservatism**: only items with an objective check ("date passed", "filing exists at SEC EDGAR") are eligible. Subjective items ("Thesis-impact assessed") are never auto-ticked.

### `claude-mention.yml`
- **Triggers**: `@claude` in any issue or comment.
- **Read-only by default** for the repo; only writes are GitHub issue/PR comments via `gh`.

## Tone & disclaimers

All public-facing artifacts (issue bodies, README, position files) are personal-journal artifacts. They are not investment advice. The weekly review issue carries an explicit disclaimer footer.

## What we explicitly do not do (yet)

- Live price feeds, market-value drift in dashboards, P&L curves.
- Tax lot accounting (FIFO/LIFO/specific ID).
- Currency conversion.
- Broker-side automation (placing orders).
- Performance benchmarking against an external index series.

These can be added later without disturbing the contracts above. The split between "deterministic, file-based math" and "Claude-narrated commentary" is the load-bearing principle — keep them separated.
