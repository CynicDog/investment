# Risks registry

One markdown file per risk: **`risks/R-YYYY-MM-NNN.md`** (filename is the id, no slug). Each file is yaml frontmatter (metadata) + markdown body (Description / Monitor for / Resolution sections).

## File shape

```markdown
---
id: R-2026-04-001
title: Short one-line headline (≤ 120 chars)
ticker: HALO                    # omit for portfolio-level risks
severity: low | medium | high
surfaced_in: weekly-review/2026-W17   # or thesis-review/HALO-2026-04, earnings/MKL-1Q26, manual
surfaced_on: 2026-04-26
status: open                    # open | monitoring | resolved
resolved_on: 2026-07-01         # only when status: resolved
issue_number: 31                # back-filled by file_a_risk.py
---

## Description

Multi-paragraph markdown explaining what the risk is, with citations.

## Monitor for

- Concrete signal A
- Concrete signal B
- Concrete signal C

## Resolution

_(only present when status: resolved — explains why and how it resolved)_
```

The schema lives in `src/investment_journal/models/risk.py`. Validate everything:

```bash
uv run python -c "from pathlib import Path; from investment_journal import Risk; \
  Risk.load_all(Path('risks')); print('all valid')"
```

## Lifecycle

1. A weekly review or earnings watcher surfaces a risk → Claude (or you) calls `scripts/file_a_risk.py`. The script picks the next free id, writes `risks/<id>.md`, opens a child GitHub issue (label `risk`), back-fills the issue number, and prints JSON to stdout.
2. The Claude workflow commits the new `.md` file and runs `scripts/render_risks_index.py` so the pinned **Risks Index** issue body stays current.
3. Discussion happens in the per-risk GitHub issue.
4. To resolve a risk, edit the file directly: change `status: open` → `status: resolved`, add `resolved_on:` to the frontmatter, and add a `## Resolution` section to the body. Push. The `risks-index-sync.yml` workflow re-renders the index. The corresponding child issue can be closed manually.
5. Never delete a resolved file. The index displays the 10 most recently resolved by default; older ones live on disk and stay queryable via git history.
