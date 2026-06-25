"""PostgreSQL connector — optional SELECT preview when DATABASE_URL is available."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence, QueryDialect
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


@register
class PostgresSqlConnector(IEvidenceConnector):
    key = "postgres_sql"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        url = os.environ.get("DATABASE_URL", "").strip()
        if not url:
            caveats.append(
                Caveat(
                    code="PG_NO_DSN",
                    title="DATABASE_URL not set",
                    message="Export DATABASE_URL (read-only user recommended) to enable SQL collectors.",
                    severity="warn",
                    remediation="Provide DSN in server env; never commit credentials to git.",
                    references=[],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=None,
                confidence=EvidenceConfidence.UNKNOWN,
                evidence_sources=["postgresql"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="pg_missing_dsn",
            )

        if binding.dialect != QueryDialect.SQL:
            caveats.append(
                Caveat(
                    code="PG_DIALECT",
                    title="Dialect mismatch",
                    message="postgres_sql connector expects dialect=sql.",
                    severity="warn",
                    remediation="Set dialect to sql in binding.",
                    references=[],
                )
            )

        q = (binding.query_body or "").strip()
        if not q:
            caveats.append(
                Caveat(
                    code="PG_EMPTY_QUERY",
                    title="SQL body empty",
                    message="Provide a SELECT that returns a numeric maturity signal (or a view wrapping it).",
                    severity="warn",
                    remediation="Add query_body in Admin → Bindings.",
                    references=[],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=None,
                confidence=EvidenceConfidence.UNKNOWN,
                evidence_sources=["postgresql"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="pg_empty_query",
            )

        try:
            import asyncpg  # type: ignore[import-not-found]
        except ImportError:
            caveats.append(
                Caveat(
                    code="PG_DRIVER",
                    title="asyncpg not installed",
                    message="Add asyncpg to backend requirements to enable SQL execution.",
                    severity="error",
                    remediation="pip install asyncpg (planned dependency for production profile).",
                    references=[],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=float((binding.parameters or {}).get("fallback_score_0_10") or 0)
                if (binding.parameters or {}).get("fallback_score_0_10") is not None
                else None,
                confidence=EvidenceConfidence.LOW,
                evidence_sources=["postgresql"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="pg_no_driver",
            )

        row = None
        try:
            conn = await asyncpg.connect(url, timeout=10, command_timeout=10)
            try:
                if not q.lower().lstrip().startswith("select"):
                    caveats.append(
                        Caveat(
                            code="PG_NON_SELECT",
                            title="Only SELECT is allowed in v0",
                            message="Mutating statements are blocked by policy.",
                            severity="error",
                            remediation="Use a read-only DB role and SELECT-only queries.",
                            references=[],
                        )
                    )
                    return EvidenceCollectionPayload(
                        score_0_10=None,
                        confidence=EvidenceConfidence.UNKNOWN,
                        evidence_sources=["postgresql"],
                        caveats=caveats,
                        last_evidence_at=now,
                        next_check_at=now + timedelta(hours=6),
                        connector_notes="pg_blocked",
                    )
                row = await conn.fetchrow(q)
            finally:
                await conn.close()
        except Exception as exc:  # noqa: BLE001 — surface as caveat
            caveats.append(
                Caveat(
                    code="PG_QUERY_ERROR",
                    title="SQL execution failed",
                    message=str(exc)[:400],
                    severity="error",
                    remediation="Validate SQL against schema; check VPN and role grants.",
                    references=[],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=None,
                confidence=EvidenceConfidence.LOW,
                evidence_sources=["postgresql"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="pg_error",
            )

        score = None
        if row is not None:
            try:
                score = float(row[0])
            except (TypeError, ValueError, IndexError):
                score = None
        caveats.append(
            Caveat(
                code="PG_PREVIEW",
                title="SQL row interpreted as score",
                message="First column of first row is cast to float for 0–10. Tune query to return a single metric.",
                severity="info",
                remediation="Wrap business logic in a SQL view for stable columns.",
                references=[],
            )
        )
        return EvidenceCollectionPayload(
            score_0_10=score,
            confidence=EvidenceConfidence.MEDIUM if score is not None else EvidenceConfidence.LOW,
            evidence_sources=["postgresql"],
            caveats=caveats,
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes="pg_ok",
        )
