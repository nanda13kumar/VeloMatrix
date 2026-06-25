"""Local JSON-driven scores — intended for gitignored `local/demo-data/bindings.json`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


def _confidence_from_param(raw: Any) -> EvidenceConfidence:
    if raw is None:
        return EvidenceConfidence.MEDIUM
    try:
        return EvidenceConfidence(str(raw).lower())
    except ValueError:
        return EvidenceConfidence.MEDIUM


@register
class StaticParameterConnector(IEvidenceConnector):
    """
    Reads `score_0_10`, optional `evidence_sources`, `confidence` from binding.parameters.

    This is the supported way to ship **local-only demo values** without committing secrets
    or tenant-specific numbers to git — keep `local/demo-data/` ignored and generate via
    `scripts/seed_local_demo.py`.
    """

    key = "static"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        params = binding.parameters or {}
        raw_score = params.get("score_0_10")
        try:
            score = float(raw_score) if raw_score is not None else None
        except (TypeError, ValueError):
            score = None
        sources = list(params.get("evidence_sources") or [])
        if not sources:
            sources = ["static_parameters"]
        conf = _confidence_from_param(params.get("confidence"))
        caveats: list[Caveat] = []
        if score is None:
            caveats.append(
                Caveat(
                    code="STATIC_MISSING_SCORE",
                    title="Static connector needs score_0_10",
                    message="Add `score_0_10` under binding.parameters, or switch to a live connector.",
                    severity="warn",
                    remediation="Edit bindings.json or use the Admin UI to persist parameters.",
                    references=[],
                )
            )
        else:
            caveats.append(
                Caveat(
                    code="STATIC_SCORE",
                    title="Scores come from local parameters only",
                    message=(
                        "This sub-dimension is not backed by a live API call. "
                        "Treat as policy/demo until a connector with credentials is configured."
                    ),
                    severity="info",
                    remediation="Replace `static` with loki_logql / postgres_sql / sonarqube_rest when ready.",
                    references=[],
                )
            )
        return EvidenceCollectionPayload(
            score_0_10=score,
            confidence=conf,
            evidence_sources=sources,
            caveats=caveats,
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes="static",
        )
