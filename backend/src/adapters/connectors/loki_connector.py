"""Loki LogQL connector — health + instant query preview when base URL is configured."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


def _loki_base(binding: BindingSpec) -> str:
    params = binding.parameters or {}
    return str(params.get("base_url") or os.environ.get("LOKI_BASE_URL", "") or "").rstrip("/")


def _auth_headers(binding: BindingSpec) -> dict[str, str]:
    params = binding.parameters or {}
    token = str(params.get("bearer_token") or os.environ.get("LOKI_BEARER_TOKEN", "") or "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _fallback_score(binding: BindingSpec) -> float | None:
    params = binding.parameters or {}
    raw = params.get("fallback_score_0_10")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@register
class LokiLogqlConnector(IEvidenceConnector):
    key = "loki_logql"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        base = _loki_base(binding)
        caveats: list[Caveat] = []
        preview_lines = 0

        if not base:
            caveats.append(
                Caveat(
                    code="LOKI_NO_BASE_URL",
                    title="Loki base URL missing",
                    message="Set `LOKI_BASE_URL` env or binding.parameters.base_url.",
                    severity="warn",
                    remediation="Configure env / binding, then re-run collection.",
                    references=["https://grafana.com/docs/loki/latest/api/"],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=_fallback_score(binding),
                confidence=EvidenceConfidence.LOW,
                evidence_sources=["loki"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="loki_not_configured",
            )

        ready_url = urljoin(base + "/", "ready")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(ready_url, headers=_auth_headers(binding))
                if r.status_code >= 400:
                    caveats.append(
                        Caveat(
                            code="LOKI_READY_FAILED",
                            title="Loki /ready check failed",
                            message=f"HTTP {r.status_code} from {ready_url}",
                            severity="error",
                            remediation="Verify URL, TLS, and bearer token scope.",
                            references=[],
                        )
                    )
                if binding.query_body.strip():
                    q_url = urljoin(base + "/", "loki/api/v1/query")
                    params_q: dict[str, Any] = {"query": binding.query_body, "limit": "5"}
                    qr = await client.get(q_url, params=params_q, headers=_auth_headers(binding))
                    if qr.status_code >= 400:
                        caveats.append(
                            Caveat(
                                code="LOKI_QUERY_FAILED",
                                title="LogQL query rejected",
                                message=f"HTTP {qr.status_code}: {qr.text[:240]}",
                                severity="warn",
                                remediation="Validate LogQL against your schema; check org/tenant headers if applicable.",
                                references=[],
                            )
                        )
                    else:
                        body = qr.json()
                        data = body.get("data") or {}
                        res_type = data.get("resultType")
                        result = data.get("result") or []
                        preview_lines = len(result)
                        caveats.append(
                            Caveat(
                                code="LOKI_QUERY_PREVIEW",
                                title="LogQL executed (sample)",
                                message=f"resultType={res_type!r}, streams={preview_lines}. Map streams to rubric in policy (v0 uses fallback_score_0_10 if present).",
                                severity="info",
                                remediation="Add thresholds in parameters or implement rubric mapper in collector.",
                                references=[],
                            )
                        )
        except httpx.RequestError as exc:
            caveats.append(
                Caveat(
                    code="LOKI_NETWORK",
                    title="Cannot reach Loki",
                    message=str(exc),
                    severity="error",
                    remediation="Check network, DNS, mTLS, and corporate proxies.",
                    references=[],
                )
            )

        score = _fallback_score(binding)
        if score is None and not caveats:
            score = 5.0
            caveats.append(
                Caveat(
                    code="LOKI_DEFAULT_SCORE",
                    title="Default mid score applied",
                    message="Set parameters.fallback_score_0_10 to remove this heuristic.",
                    severity="info",
                    remediation="Define explicit scoring from query results.",
                    references=[],
                )
            )

        return EvidenceCollectionPayload(
            score_0_10=score,
            confidence=EvidenceConfidence.MEDIUM if preview_lines else EvidenceConfidence.LOW,
            evidence_sources=["loki"],
            caveats=caveats,
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes=f"loki preview_streams={preview_lines}",
        )
