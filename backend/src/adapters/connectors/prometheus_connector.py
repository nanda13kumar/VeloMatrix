"""Prometheus / Thanos / Cortex PromQL connector.

Works with any OpenMetrics-compatible HTTP endpoint.
"""

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


def _params(b: BindingSpec) -> dict[str, Any]:
    return b.parameters or {}


def _base(b: BindingSpec) -> str:
    p = _params(b)
    return str(p.get("base_url") or os.environ.get("PROMETHEUS_URL", "") or "").rstrip("/")


def _headers(b: BindingSpec) -> dict[str, str]:
    p = _params(b)
    token = str(p.get("bearer_token") or os.environ.get("PROMETHEUS_BEARER_TOKEN", "") or "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _fb(b: BindingSpec) -> float | None:
    raw = _params(b).get("fallback_score_0_10")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _scalar_from_result(data: dict[str, Any]) -> float | None:
    """Extract the first numeric value from a Prometheus instant-query response."""
    result_type = (data.get("data") or {}).get("resultType")
    result = (data.get("data") or {}).get("result") or []
    if not result:
        return None
    if result_type == "scalar":
        val = result[1] if isinstance(result, list) and len(result) > 1 else None
    elif result_type in ("vector", "matrix"):
        first = result[0]
        if result_type == "vector":
            val = (first.get("value") or [None, None])[1]
        else:
            vals = first.get("values") or []
            val = vals[-1][1] if vals else None
    else:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@register
class PrometheusPromqlConnector(IEvidenceConnector):
    """
    Executes an arbitrary PromQL instant query and maps the scalar result to 0–10.

    Mapping modes (set via `parameters.score_mode`):
    - ``raw`` (default): treat returned value directly as 0–10 (clamp).
    - ``ratio``:  value is already a 0–1 ratio → multiply by 10.
    - ``inverse_ratio``:  failure_rate style 0–1 → (1 - value) × 10.
    - ``threshold``: score = 10 if value >= `threshold` else value / threshold * 10.
    """

    key = "prometheus_promql"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        base = _base(binding)

        if not base:
            caveats.append(
                Caveat(
                    code="PROM_NO_URL",
                    title="Prometheus base URL missing",
                    message="Set PROMETHEUS_URL or binding.parameters.base_url (e.g. http://prometheus:9090).",
                    severity="warn",
                    remediation="Export PROMETHEUS_URL server-side; also accepts Thanos/Cortex-compatible endpoints.",
                    references=["https://prometheus.io/docs/prometheus/latest/querying/api/"],
                )
            )
            return _return(now, _fb(binding), EvidenceConfidence.LOW, caveats, "prom_no_url")

        query = (binding.query_body or "").strip()
        if not query:
            caveats.append(
                Caveat(
                    code="PROM_EMPTY_QUERY",
                    title="PromQL query body empty",
                    message="Provide a PromQL expression in query_body that returns a single scalar/vector.",
                    severity="warn",
                    remediation="Example: `sum(rate(http_server_requests_seconds_count[5m])) by (service)`",
                    references=[],
                )
            )
            return _return(now, _fb(binding), EvidenceConfidence.UNKNOWN, caveats, "prom_empty_query")

        try:
            url = urljoin(base + "/", "api/v1/query")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params={"query": query}, headers=_headers(binding))
                if resp.status_code >= 400:
                    caveats.append(
                        Caveat(
                            code="PROM_HTTP_ERROR",
                            title="Prometheus API error",
                            message=f"HTTP {resp.status_code}: {resp.text[:300]}",
                            severity="error",
                            remediation="Validate URL, TLS, and bearer token scope (needs metrics:read at minimum).",
                            references=[],
                        )
                    )
                    return _return(now, _fb(binding), EvidenceConfidence.LOW, caveats, "prom_http_err")

                body = resp.json()
                if body.get("status") != "success":
                    caveats.append(
                        Caveat(
                            code="PROM_QUERY_ERROR",
                            title="PromQL execution failed",
                            message=str(body.get("error") or body)[:300],
                            severity="error",
                            remediation="Validate PromQL against your metric names; check tenant label matchers.",
                            references=[],
                        )
                    )
                    return _return(now, _fb(binding), EvidenceConfidence.LOW, caveats, "prom_query_err")

                raw_value = _scalar_from_result(body)
                score = _map_score(raw_value, _params(binding))

                mode = str(_params(binding).get("score_mode") or "raw")
                caveats.append(
                    Caveat(
                        code="PROM_QUERY_OK",
                        title="PromQL query succeeded",
                        message=(
                            f"raw_value={raw_value!r} → score={score!r} (mode={mode!r}). "
                            "Tune score_mode / threshold in parameters for your units."
                        ),
                        severity="info",
                        remediation="If raw value is not 0–10, set score_mode=ratio or score_mode=threshold with threshold=<target>.",
                        references=[],
                    )
                )

        except httpx.RequestError as exc:
            caveats.append(
                Caveat(
                    code="PROM_NETWORK",
                    title="Cannot reach Prometheus",
                    message=str(exc),
                    severity="error",
                    remediation="Check network, VPN, and mTLS settings.",
                    references=[],
                )
            )
            return _return(now, _fb(binding), EvidenceConfidence.LOW, caveats, "prom_network")

        conf = EvidenceConfidence.HIGH if score is not None else EvidenceConfidence.LOW
        return _return(now, score, conf, caveats, "prom_ok")


def _map_score(value: float | None, params: dict[str, Any]) -> float | None:
    if value is None:
        return None
    mode = str(params.get("score_mode") or "raw").lower()
    threshold = float(params.get("threshold") or 0) or None
    if mode == "ratio":
        return round(max(0.0, min(10.0, value * 10)), 2)
    if mode == "inverse_ratio":
        return round(max(0.0, min(10.0, (1 - value) * 10)), 2)
    if mode == "threshold" and threshold:
        if value >= threshold:
            return 10.0
        return round(max(0.0, (value / threshold) * 10.0), 2)
    return round(max(0.0, min(10.0, value)), 2)


def _return(
    now: datetime,
    score: float | None,
    conf: EvidenceConfidence,
    caveats: list[Caveat],
    note: str,
) -> EvidenceCollectionPayload:
    return EvidenceCollectionPayload(
        score_0_10=score,
        confidence=conf,
        evidence_sources=["prometheus"],
        caveats=caveats,
        last_evidence_at=now,
        next_check_at=now + timedelta(minutes=5),
        connector_notes=note,
    )
