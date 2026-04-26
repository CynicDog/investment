"""Investment journal DSL.

Pydantic models + renderers for every artifact the repo produces.
The DSL is the contract between hand-written content (allocation.yml,
position dossiers) and automation-produced content (review issues,
earnings issues, dca-tracker issues, risk issues).
"""

from investment_journal.models.allocation import Allocation, DCA, Position
from investment_journal.models.dossier import Dossier
from investment_journal.models.risk import Risk, Severity, RiskStatus
from investment_journal.models.weekly_review import (
    Catalyst,
    DCASnapshot,
    PositionUpdate,
    ThesisStatus,
    WeeklyReview,
)
from investment_journal.models.thesis_review import ThesisReview, ThesisVerdict
from investment_journal.models.earnings_event import EarningsEvent, EarningsRecap
from investment_journal.models.dca_tracker import DCATracker, DCATick
from investment_journal.models.tone import DISCLAIMER, TONE_RULES, Tone

__all__ = [
    "Allocation",
    "DCA",
    "Position",
    "Dossier",
    "Risk",
    "Severity",
    "RiskStatus",
    "WeeklyReview",
    "PositionUpdate",
    "Catalyst",
    "DCASnapshot",
    "ThesisStatus",
    "ThesisReview",
    "ThesisVerdict",
    "EarningsEvent",
    "EarningsRecap",
    "DCATracker",
    "DCATick",
    "Tone",
    "TONE_RULES",
    "DISCLAIMER",
]
