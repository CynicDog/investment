"""Codified tone rules and reusable constants."""

from pydantic import BaseModel


TONE_RULES = """\
- Terse, factual, present tense. Bullets over paragraphs.
- No predictions. Frame as "as of {date}, X is reported / disclosed / expected per company guidance / consensus".
- No advice language ("should buy", "should sell", "recommend"). Frame as observations.
- Cite sources inline. Primary sources (10-K, 10-Q, 8-K, IR press release, transcript) over secondary or aggregator articles.
- Numbers carry units (USD/%) and the period (TTM, YoY, QoQ).
- If a number disagrees across sources, list both and flag the discrepancy."""


DISCLAIMER = "_Personal journal. Not financial advice._"


class Tone(BaseModel):
    """Repo tone rules. Mostly read-only constants exposed as a model so workflows can reference them by import path."""

    rules: str = TONE_RULES
    disclaimer: str = DISCLAIMER
