"""Explicit no-op connector — score stays empty with actionable caveats."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


@register
class PlaceholderConnector(IEvidenceConnector):
    """Use when wiring exists but integration is intentionally deferred."""

    key = "placeholder"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        return EvidenceCollectionPayload(
            score_0_10=None,
            confidence=EvidenceConfidence.UNKNOWN,
            evidence_sources=[],
            caveats=[
                Caveat(
                    code="PLACEHOLDER_CONNECTOR",
                    title="Datasource not executed",
                    message=(
                        "Binding references `placeholder` — no external API call is made. "
                        "Swap to `static` for local JSON-driven scores, or a live connector once credentials exist."
                    ),
                    severity="info",
                    remediation="Admin → Bindings: change connector to `static` or configure Loki/Sonar/Postgres.",
                    references=["docs/API.md#connectors"],
                )
            ],
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes="placeholder",
        )


class UnknownConnector(IEvidenceConnector):
    """Returned when connector_id is not registered (not added to registry)."""

    key = "unregistered"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        return EvidenceCollectionPayload(
            score_0_10=None,
            confidence=EvidenceConfidence.UNKNOWN,
            evidence_sources=[],
            caveats=[
                Caveat(
                    code="UNKNOWN_CONNECTOR",
                    title="Connector is not registered",
                    message=f"No plugin registered for `{binding.connector_id}`.",
                    severity="error",
                    remediation="Fix connector_id to one of the registered keys, or implement a new adapter.",
                    references=[],
                )
            ],
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes="unknown",
        )
