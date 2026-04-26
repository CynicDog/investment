# Risks registry

Each open or resolved risk has one yaml file: `R-YYYY-MM-NNN-slug.yml`.

The schema is defined by `investment_journal.models.risk.Risk`. Validate with:

```bash
uv run python -c "from pathlib import Path; from investment_journal import Risk; \
[Risk.load(p) for p in Path('risks').glob('R-*.yml')]; print('all valid')"
```

Lifecycle:

1. A weekly review or thesis review surfaces a risk → Claude (or you) writes a new `R-YYYY-MM-NNN-*.yml` file with `status: open`.
2. A push to `risks/**` triggers `.github/workflows/risks-index-sync.yml`, which:
   - Re-renders the pinned **Risks Index** issue body from all yaml files here.
   - Optionally opens a per-risk discussion issue (label `risk`) and back-fills `issue_number` into the yaml.
3. To resolve a risk, edit the file: set `status: resolved`, fill in `resolved_on` and `resolution_note`. The next sync run updates the index and closes the per-risk issue.

Never delete a resolved risk file — the history matters. The Risks Index only shows the 10 most recently resolved by default.
