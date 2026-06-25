"""Runtime evidence bundle produced by connector plugins."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import EvidenceConfidence
from domain.schemas import Caveat


class EvidenceCollectionPayload(BaseModel):
    """Merged into SubDimensionScore by the snapshot builder."""

    score_0_10: float | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.UNKNOWN
    evidence_sources: list[str] = Field(default_factory=list)
    caveats: list[Caveat] = Field(default_factory=list)
    last_evidence_at: datetime | None = None
    next_check_at: datetime | None = None
    connector_notes: str = ""
