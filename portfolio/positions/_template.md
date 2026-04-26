<!--
This is the master per-stock dossier template. Copy it to {TICKER}.md and fill in.
Sections marked AUTO are appended/updated by workflows — do not edit those by hand
unless you also update the workflow that touches them.
-->

# {TICKER} — {Company Name}

> Last reviewed: YYYY-MM-DD &nbsp;•&nbsp; Sector: {sector} &nbsp;•&nbsp; Target: {X}% &nbsp;•&nbsp; Daily DCA: ${X}

## At a glance

| Metric | Value |
|---|---|
| Target allocation | {X}% |
| Cost-basis allocation | _populated by `render_dashboards.py`_ |
| Drift (pp) | _populated_ |
| Shares held | _populated_ |
| Avg cost basis | _populated_ |
| Total cost basis | _populated_ |
| Daily DCA | ${X} |

## Thesis

_3–5 sentences. Why this is in the portfolio at this weight._

## Bull case

- ...
- ...
- ...

## Bear case & risks

- ...
- ...
- ...

## Catalysts (next 12 months)

- [ ] {event} — {expected month/quarter} — {linked issue or `n/a`}
- [ ] ...

## Valuation snapshot

_Last refreshed: YYYY-MM-DD (weekly review)_

| Metric | This stock | Peer / history reference |
|---|---|---|
| P/E (TTM) | — | — |
| P/E (forward) | — | — |
| EV/EBITDA | — | — |
| FCF yield | — | — |
| Net debt / EBITDA | — | — |
| Notes | — | — |

## Capital return

- **Buybacks**: …
- **Dividend**: …
- **Insider activity**: …

## Recent earnings (last 4 quarters)

| Quarter | Revenue | EPS | Guidance change | Notes |
|---|---|---|---|---|
| — | — | — | — | — |
| — | — | — | — | — |
| — | — | — | — | — |
| — | — | — | — | — |

## Trades log

<!-- trades-start -->
_Auto-rendered by `scripts/render_dashboards.py` from `trades.csv` filtered by ticker._
<!-- trades-end -->

## News & notes

<!-- news-start -->
_Weekly review action appends dated bullets here. Most recent first._
<!-- news-end -->

## Re-check schedule

- Quarterly thesis review issue: _link once opened_
- Next earnings (estimated): _populated by earnings-watcher_

---

_Personal journal entry. Not financial advice._
