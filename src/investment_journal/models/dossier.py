"""Position dossier: header + required sections + freeform markdown prose.

The DSL validates structure (header line is well-formed, required H2 sections are
present) without parsing the prose itself. The user's thesis writing stays as
plain markdown — easier to read in editors, less brittle than yaml round-trips.
"""

from datetime import date
from pathlib import Path
import re
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator


HEADER_LINE_RE = re.compile(
    r"^>\s*Last reviewed:\s*(?P<reviewed>\d{4}-\d{2}-\d{2})"
    r"\s*&nbsp;•&nbsp;\s*Sector:\s*(?P<sector>[^•]+?)"
    r"\s*&nbsp;•&nbsp;\s*Target:\s*(?P<target>\d+(?:\.\d+)?)%"
    r"\s*&nbsp;•&nbsp;\s*Daily DCA:\s*\$(?P<dca>\d+(?:\.\d+)?)\s*$"
)


REQUIRED_SECTIONS: tuple[str, ...] = (
    "Thesis",
    "Bull case",
    "Bear case & risks",
    "Catalysts (next 12 months)",
    "Valuation snapshot",
    "Capital return",
    "Recent earnings (last 4 quarters)",
    "News & notes",
    "Re-check schedule",
)


class Dossier(BaseModel):
    """Validated facade over a `portfolio/positions/{TICKER}.md` file.

    Construct via `Dossier.from_file(path)`. The `body` field holds the raw
    markdown so renderers / Claude can read sections without re-rendering.
    """

    REQUIRED_SECTIONS: ClassVar[tuple[str, ...]] = REQUIRED_SECTIONS

    ticker: str = Field(pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    name: str
    last_reviewed: date
    sector: str
    target_pct: float = Field(gt=0, le=100)
    dca_per_day_usd: float = Field(ge=0)
    sections: list[str]
    body: str

    @model_validator(mode="after")
    def _required_sections_present(self) -> "Dossier":
        missing = [s for s in REQUIRED_SECTIONS if s not in self.sections]
        if missing:
            raise ValueError(f"dossier missing required sections: {missing}")
        return self

    @classmethod
    def from_file(cls, path: Path) -> "Dossier":
        text = path.read_text()
        lines = text.splitlines()

        # First H1 = "TICKER — Name"
        h1 = next((line for line in lines if line.startswith("# ")), None)
        if not h1:
            raise ValueError(f"{path}: no H1 found")
        m = re.match(r"^#\s+([A-Z][A-Z0-9.-]{0,9})\s+—\s+(.+)$", h1)
        if not m:
            raise ValueError(f"{path}: H1 must match '# TICKER — Name', got: {h1!r}")
        ticker, name = m.group(1), m.group(2).strip()

        # Header blockquote
        hdr = next((line for line in lines if HEADER_LINE_RE.match(line)), None)
        if not hdr:
            raise ValueError(
                f"{path}: header line missing or malformed; expected\n"
                f"  > Last reviewed: YYYY-MM-DD &nbsp;•&nbsp; Sector: ... &nbsp;•&nbsp; Target: X% &nbsp;•&nbsp; Daily DCA: $X"
            )
        hm = HEADER_LINE_RE.match(hdr)
        assert hm  # for type-checkers; we just confirmed it matches above

        sections = [
            line[3:].strip() for line in lines if line.startswith("## ")
        ]

        return cls(
            ticker=ticker,
            name=name,
            last_reviewed=date.fromisoformat(hm.group("reviewed")),
            sector=hm.group("sector").strip(),
            target_pct=float(hm.group("target")),
            dca_per_day_usd=float(hm.group("dca")),
            sections=sections,
            body=text,
        )
