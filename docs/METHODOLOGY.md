# Methodology

How rundowns and dashboards are produced. If you change any of the math or the workflow shape, update this file.

## Source-of-truth files

| File | Hand-edited? | Edited by automation? |
|---|---|---|
| `portfolio/allocation.yml` | Yes (rare, deliberate) | No |
| `portfolio/positions/*.md` | Yes (thesis sections) | Yes (only `<!-- news-start --> / news-end` block by weekly review) |
| `portfolio/dashboards/*.md` | **No** — fully regenerated | Yes (`render_dashboards.py`) |
| `README.md` | Yes (outside markers) | Yes (inside `<!-- portfolio-start --> / portfolio-end` markers) |

The user runs the actual daily DCA at **Toss**, which does not expose a trade-history API. The repo therefore tracks **intent** (target weights, daily DCA $ allocations as configured at Toss) and **confirmation** (weekly DCA tracker issues with `[ ]` checkboxes), not real broker fills. There is no trades.csv, no cost-basis tracking, no share-count math.

## DCA confirmation tracking

The `dca-tracker.yml` workflow runs every Sunday 22:00 UTC (~Monday 07:00 KST):

1. Closes any still-open `dca-tracker` issue from prior weeks, posting a tally comment (`Auto-closing at end of week. Tally: N/M confirmed.`).
2. Opens a fresh weekly issue titled `DCA tracker: week of YYYY-MM-DD` with five `[ ]` Mon–Fri bullets.

The user ticks a bullet each weekday once Toss confirms the fill in the app. Closed issues become the journal — read by the weekly review to count fills.

A bullet is **never** ticked by automation. Even though `dca-tracker` issues are not labeled `auto-tick`, automation must explicitly exclude them. See CLAUDE.md.

## Dashboards (what the renderer produces)

`scripts/render_dashboards.py` is dependency-free except for PyYAML, deterministic, and runs in <1 second. It reads `portfolio/allocation.yml` and writes:

- **`dashboards/allocation.md`** — target allocation pie (mermaid).
- **`dashboards/dca-flow.md`** — daily $ split as both:
  - a flowchart `Daily $X → ticker $Y` (six edges)
  - a sankey-beta diagram grouped by sector: `Daily $X → sector → ticker`. Sectors are derived from `positions[].sector`, truncated at the first `/` for clean node labels.
- **`dashboards/upcoming-earnings.md`** — placeholder until `earnings-watcher.yml` populates it.
- **`README.md`** — refreshes the auto-block between markers with the target pie + a 5-column position table.

There is no actual-allocation pie, no drift table, no market-value math. Allocation drift is observed visually at Toss.

## Workflow contracts

### `weekly-review.yml`
- **Reads**: `allocation.yml`, all `positions/*.md`, recent closed `dca-tracker` issues.
- **Writes**: a new GitHub issue labeled `weekly-review`, titled `Weekly review YYYY-Www`.
- **Does not**: modify any tracked file.

### `earnings-watcher.yml`
- **Reads**: `allocation.yml`, open earnings issues.
- **Writes**: opens earnings issues 7 days ahead; comments + edits issue body to tick `[x] Earnings released` / `[x] Recap published` after the call.
- **Does not**: modify position files. Thesis-impact updates remain a human decision.

### `update-dashboards.yml`
- **Reads**: `allocation.yml`.
- **Writes**: `dashboards/*.md`, the auto-block of `README.md`.
- **No Claude involvement.** Pure deterministic renderer. Must remain so.

### `dca-tracker.yml`
- **Reads**: open `dca-tracker` issues.
- **Writes**: closes prior week's tracker; opens a new tracker issue.
- **No Claude involvement.**

### `issue-checkbox-tick.yml`
- **Triggers**: edits/comments on `auto-tick`-labeled issues only.
- **Writes**: edits the issue body to flip `[ ] → [x]` for verifiable items only; posts one comment listing what was ticked and why.
- **Hard exclusion**: `dca-tracker` issues never auto-tick (they should not carry the `auto-tick` label, but the workflow must defensively skip them by label even if mislabeled).

### `claude-mention.yml`
- **Triggers**: `@claude` in any issue or comment.
- **Read-only by default** for the repo; only writes are GitHub issue/PR comments via `gh`.

## Tone & disclaimers

All public-facing artifacts (issue bodies, README, position files) are personal-journal artifacts. Not investment advice. The weekly review issue carries an explicit disclaimer footer.

## What we explicitly do not do

- Cost-basis tracking, share-count tracking, real P&L. Toss is the source of truth for actual holdings; we don't try to mirror it.
- Live price feeds, market-value drift dashboards.
- Tax lot accounting (FIFO/LIFO/specific ID).
- Currency conversion between KRW (Toss) and USD (US listings).
- Broker-side automation (placing orders).

If Toss exposes an API in the future, layering cost-basis tracking on top is straightforward: add a `trades.csv`, restore the cost-basis math in `render_dashboards.py`, add an actual-allocation pie. The current design intentionally leaves that hook open.
