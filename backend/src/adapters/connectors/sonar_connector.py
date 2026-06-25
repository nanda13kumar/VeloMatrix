"""SonarQube Web API connector — project measures preview when URL + token exist."""

from __future__ import annotations

import os
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


def _auth(binding: BindingSpec) -> tuple[str, dict[str, str]]:
    params = binding.parameters or {}
    base = str(params.get("base_url") or os.environ.get("SONARQUBE_URL", "") or "").rstrip("/")
    token = str(params.get("token") or os.environ.get("SONARQUBE_TOKEN", "") or "")
    headers: dict[str, str] = {}
    if token:
        raw = f"{token}:".encode()
        headers["Authorization"] = "Basic " + b64encode(raw).decode("ascii")
    return base, headers


@register
class SonarQubeRestConnector(IEvidenceConnector):
    key = "sonarqube_rest"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        base, headers = _auth(binding)
        params = binding.parameters or {}
        project_key = str(params.get("project_key") or "")

        if not base:
            caveats.append(
                Caveat(
                    code="SONAR_NO_URL",
                    title="SonarQube URL missing",
                    message="Set SONARQUBE_URL or binding.parameters.base_url.",
                    severity="warn",
                    remediation="Configure Sonar base URL (HTTPS).",
                    references=["https://sonarcloud.io/web_api/"],
                )
            )
            return _fallback(now, caveats, binding)

        status_url = f"{base}/api/system/status"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                st = await client.get(status_url, headers=headers)
                if st.status_code >= 400:
                    caveats.append(
                        Caveat(
                            code="SONAR_STATUS",
                            title="SonarQube status call failed",
                            message=f"HTTP {st.status_code}: {st.text[:200]}",
                            severity="error",
                            remediation="Check URL, token, and TLS interception.",
                            references=[],
                        )
                    )
                    return _fallback(now, caveats, binding)

                if project_key:
                    m_url = f"{base}/api/measures/component"
                    mq: dict[str, Any] = {
                        "component": project_key,
                        "metricKeys": "bugs,vulnerabilities,code_smells,coverage,security_rating,reliability_rating",
                    }
                    mr = await client.get(m_url, params=mq, headers=headers)
                    if mr.status_code >= 400:
                        caveats.append(
                            Caveat(
                                code="SONAR_MEASURES",
                                title="Measures API failed",
                                message=f"HTTP {mr.status_code}: {mr.text[:200]}",
                                severity="warn",
                                remediation="Validate project_key and permissions.",
                                references=[],
                            )
                        )
                        return _fallback(now, caveats, binding)
                    payload = mr.json()
                    comp = payload.get("component") or {}
                    measures = {m["metric"]: m.get("value") for m in comp.get("measures") or []}
                    caveats.append(
                        Caveat(
                            code="SONAR_MEASURES_PREVIEW",
                            title="Sonar measures snapshot",
                            message=f"Keys sampled: {', '.join(list(measures.keys())[:6])}. Map to rubric via policy (v0 uses fallback_score_0_10 if set).",
                            severity="info",
                            remediation="Add rubric mapping or SQL view over Sonar webhook exports.",
                            references=[],
                        )
                    )
                    fb = _fallback_score(binding)
                    score = fb if fb is not None else _heuristic_from_measures(measures)
                    return EvidenceCollectionPayload(
                        score_0_10=score,
                        confidence=EvidenceConfidence.MEDIUM,
                        evidence_sources=["sonarqube"],
                        caveats=caveats,
                        last_evidence_at=now,
                        next_check_at=now + timedelta(hours=6),
                        connector_notes="sonar_measures",
                    )

                caveats.append(
                    Caveat(
                        code="SONAR_NO_PROJECT",
                        title="project_key not set",
                        message="Add binding.parameters.project_key for measure pull.",
                        severity="info",
                        remediation="Set project_key to your Sonar component key.",
                        references=[],
                    )
                )
                return _fallback(now, caveats, binding)
        except httpx.RequestError as exc:
            caveats.append(
                Caveat(
                    code="SONAR_NETWORK",
                    title="Cannot reach SonarQube",
                    message=str(exc),
                    severity="error",
                    remediation="Check VPN / allowlists.",
                    references=[],
                )
            )
            return _fallback(now, caveats, binding)


def _fallback_score(binding: BindingSpec) -> float | None:
    raw = (binding.parameters or {}).get("fallback_score_0_10")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _heuristic_from_measures(measures: dict[str, str | None]) -> float | None:
    cov = measures.get("coverage")
    vuln = measures.get("vulnerabilities")
    try:
        c = float(cov) if cov is not None else None
    except (TypeError, ValueError):
        c = None
    try:
        v = float(vuln) if vuln is not None else None
    except (TypeError, ValueError):
        v = None
    if c is None and v is None:
        return None
    score = 6.0
    if c is not None:
        score = min(10.0, max(0.0, c / 10.0))
    if v is not None:
        score = max(0.0, score - min(5.0, v * 0.4))
    return round(score, 2)


def _fallback(
    now: datetime,
    caveats: list[Caveat],
    binding: BindingSpec,
) -> EvidenceCollectionPayload:
    return EvidenceCollectionPayload(
        score_0_10=_fallback_score(binding),
        confidence=EvidenceConfidence.LOW,
        evidence_sources=["sonarqube"],
        caveats=caveats,
        last_evidence_at=now,
        next_check_at=now + timedelta(hours=6),
        connector_notes="sonar_fallback",
    )
