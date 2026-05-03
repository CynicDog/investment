# Scenarios

Decision rules that govern when and how the portfolio changes. Each scenario is a versioned
markdown file with YAML frontmatter.

## File naming

`S-YYYY-MM-NNN.md` — auto-assigned by `scripts/file_a_scenario.py`.

## Lifecycle

1. **File** — run `scripts/file_a_scenario.py` (CLI or via Claude). Creates the `.md` file
   and opens a GitHub issue (label: `scenario`).
2. **Monitor** — scenario status is `active`. Review in weekly-review or horizon-review issues.
3. **Trigger** — when the trigger condition fires, update `status: triggered` and add
   `triggered_on: YYYY-MM-DD`. The corresponding action should be executed.
4. **Resolve** — after the action is completed, set `status: resolved` and add `resolution_note`.
5. **Dismiss** — if the scenario is superseded or no longer relevant, set `status: dismissed`.

## Trigger types

| Type | When it fires |
|---|---|
| `metric` | A quantitative threshold is breached (FCF yield, D/E, etc.) |
| `thesis-verdict` | A thesis review returns `no` or `partially` |
| `watchlist` | A watchlist candidate passes all 4 quality buckets |
| `time-gate` | A specific date or phase milestone is reached |
| `dca-shift` | Portfolio-level DCA budget change condition is met |
| `drip` | Dividend income crosses a reinvestment threshold |

## Never edit by hand from a workflow

Use `scripts/file_a_scenario.py` to file new scenarios. For status updates, edit the file
directly (set status, triggered_on, resolution_note) and push — the Risks Index does not
cover scenarios, so no auto-sync workflow exists yet.
