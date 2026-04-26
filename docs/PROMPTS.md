# Prompts

Centralized prompt library for the Claude-driven workflows. Workflows reference sections by anchor (`## weekly-review`, `## earnings-watcher`, `## issue-checkbox-tick`).

When you tweak a prompt here, the next workflow run picks it up — no workflow yaml change needed.

> Tone reminder (always applies): terse, factual, present tense; no predictions; no advice language; cite primary sources inline.

---

## weekly-review

Inputs you must read before writing anything:

- `portfolio/allocation.yml` — target weights, DCA per ticker (the user has these configured at Toss).
- Each `portfolio/positions/{TICKER}.md`.
- Closed `dca-tracker` issues from the past 1–4 weeks: `gh issue list --label dca-tracker --state closed --limit 10 --json number,title,body,closedAt`. From each, count `- [x]` lines to get fills-per-week.

Then web-search the last 7 calendar days of news per ticker. Prefer:

1. Company press releases (IR site).
2. SEC filings (8-K, 10-Q, 10-K).
3. Earnings call transcripts.
4. Reputable trade press (last resort, must cite).

Produce one markdown report. Open it as a new issue titled `Weekly review {ISO-week}` (e.g. `Weekly review 2026-W17`) with label `weekly-review`. Body shape:

```markdown
# Weekly review {ISO-week}

_Generated {YYYY-MM-DD}._

## DCA confirmation

- This week: {N}/5 days confirmed at Toss.
- Trailing 4 weeks: {N1}/5, {N2}/5, {N3}/5, {N4}/5.
- Notes: any missed days the user flagged in dca-tracker issue comments.

## Per-position update

### {TICKER}
- News (last 7d): bullet, bullet, bullet — each with a citation link.
- Valuation read: 1 line, e.g. "P/E TTM ~Xx vs 5y avg ~Yx (source: …)".
- Thesis status: still holds / monitor / re-check needed (one sentence why).

(repeat per ticker)

## Catalyst calendar (next 30 days)

- {date}: {ticker} — {event} — {issue link if open}

## Disclaimers

_Personal journal. Not financial advice. Sources cited inline._
```

Constraints:

- Do NOT modify any file in this run except a scratch markdown file you create for the issue body.
- Do NOT change any weights or thesis text in `positions/*.md`.
- Do NOT comment on or edit any `dca-tracker` issue.
- If you cannot find a primary source for a number, mark it `(unverified)`.

---

## earnings-watcher

Inputs:

- `portfolio/allocation.yml` — list of tickers.
- Open earnings issues: `gh issue list --label earnings --state open`.

Loop per ticker. For each:

1. Web-search the next confirmed earnings date. Trust order: company IR site > NASDAQ earnings calendar > broker page. **Do not** rely on aggregators like Yahoo headlines for the date — those are often stale.
2. If no primary-source confirmation, skip this ticker for the run.
3. If date is **within 7 days** AND no open issue exists with title matching `Earnings: {TICKER} {QQ}{YY}`:
   - Compute quarter label (e.g. `1Q26` for Jan–Mar 2026).
   - Open a new issue with title `Earnings: {TICKER} {QQ}{YY}`, labels `earnings,auto-tick`. Body should mirror the `earnings-event.yml` template, populated with the date and any pre-call expectations from prior-quarter guidance you can cite.
4. If an issue exists for a ticker whose earnings was **in the past 0–3 days** AND its body lacks a `### Recap` block:
   - Web-search the press release + transcript (transcripts may take 1–2 days; if not yet, post a partial recap based on the press release alone and add `_transcript pending_`).
   - Post a comment on the issue with the recap shape:
     ```markdown
     ### Recap

     - **Reported**: rev $X.XXB ({+/-X% YoY}), EPS $X.XX (cite source).
     - **Guidance**: raised / reiterated / lowered — quote line.
     - **Call quotes**: 1–3 short verbatim quotes that move the thesis.
     - **Thesis impact**: pending human review (do not auto-update positions/*.md).
     ```
   - Edit the issue body to flip `[ ] Earnings released` → `[x]` and `[ ] Recap published` → `[x]`. Leave the others untouched.

Be conservative. If anything looks wrong, no-op and explain in a comment on a single tracking issue. Better to skip a day than publish a wrong date.

---

## issue-checkbox-tick

You are reviewing one issue (number is in `$ISSUE_NUMBER`). Goal: tick `[ ] → [x]` for items that are now objectively verifiable.

Hard rules:

- **Never tick anything in a `dca-tracker`-labeled issue.** Those represent real money at the user's broker — only the user confirms. If the issue carries that label, exit silently.
- **Never tick subjective items.** Examples: "Thesis-impact assessed", "Action taken", "Allocation in line with target".
- **Never untick** (`[x] → [ ]`).
- **Never edit any file in the repository.** This workflow only modifies issue text.
- **Never tick more than 5 items in a single run**; if there are more, tick the first 5 and note the cap.

Steps:

1. `gh issue view "$ISSUE_NUMBER" --json body,title,labels,comments` — read the full state.
2. Bail out immediately if labels include `dca-tracker`.
3. For each `- [ ]` line in the body, classify:
   - **Auto-tickable** — the criterion is objective and you can verify it from issue context, repo state, or the public web with citation. Examples:
     - `[ ] Earnings released` — verifiable if earnings date in issue body has passed AND a primary press release exists.
     - `[ ] 10-Q filed` — verifiable from SEC EDGAR.
     - `[ ] Recap published` — verifiable if a comment with `### Recap` exists on the issue.
   - **Subjective** — leave alone.
4. For each auto-tickable item you confirmed, build the new body with that line flipped (preserving everything else byte-for-byte).
5. `gh issue edit "$ISSUE_NUMBER" --body-file <new>`.
6. Post ONE comment listing what you ticked and the evidence:
   ```
   Auto-ticked:
   - `[x] Earnings released` — confirmed by press release dated 2026-05-06: <url>
   - `[x] Recap published` — comment #N has `### Recap` block.
   Left untouched: `[ ] Thesis-impact assessed` (subjective).
   ```
7. If nothing is verifiable, post nothing. Exit silently.

---

## Style guide for any issue or comment you author

- Headlines: `## H2` for sections, `### H3` for sub.
- Tables for any 3+ row data set.
- Inline citations: `[source](url)` immediately after the claim.
- Numbers: include units (USD/%) and the period (TTM, YoY, QoQ).
- Footer when authoring a top-level issue body: `_Personal journal. Not financial advice._`.
