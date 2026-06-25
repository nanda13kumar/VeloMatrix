"""Snyk REST API connector.

Collects aggregate vulnerability counts from a Snyk org or project
and translates them to a 0–10 maturity score.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register

_API = "https://api.snyk.io"


def _token(b: BindingSpec) -> str:
    p = b.parameters or {}
    return str(p.get("token") or os.environ.get("SNYK_TOKEN", "") or "")


def _org(b: BindingSpec) -> str:
    p = b.parameters or {}
    return str(p.get("org_id") or os.environ.get("SNYK_ORG_ID", "") or "")


def _project(b: BindingSpec) -> str | None:
    p = b.parameters or {}
    v = p.get("project_id")
    return str(v) if v else None


def _fb(b: BindingSpec) -> float | None:
    raw = (b.parameters or {}).get("fallback_score_0_10")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _score_from_issues(critical: int, high: int, medium: int, low: int) -> float:
    """
    Weighted penalty from 10:
    - critical: –2.5 per (capped at –5.0)
    - high:     –1.0 per (capped at –3.0)
    - medium:   –0.2 per (capped at –1.5)
    - low:      –0.05 per (capped at –0.5)
    """
    penalty = (
        min(critical * 2.5, 5.0)
        + min(high * 1.0, 3.0)
        + min(medium * 0.2, 1.5)
        + min(low * 0.05, 0.5)
    )
    return round(max(0.0, 10.0 - penalty), 2)


@register
class SnykRestConnector(IEvidenceConnector):
    """
    Pulls vulnerability aggregate from Snyk REST /v1 API.
    Optional: scope to a single project_id, else uses org-level issues.

    Auth: Snyk token in `SNYK_TOKEN` env or `binding.parameters.token`.
    Org:  `SNYK_ORG_ID` env or `binding.parameters.org_id`.
    """

    key = "snyk_rest"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        token = _token(binding)
        org = _org(binding)

        if not token:
            caveats.append(
                Caveat(
                    code="SNYK_NO_TOKEN",
                    title="Snyk token missing",
                    message="Set SNYK_TOKEN env or binding.parameters.token.",
                    severity="warn",
                    remediation="Create a Snyk service account token with `org:read` scope.",
                    references=["https://docs.snyk.io/snyk-api/rest-api"],
                )
            )
            return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "snyk_no_token")

        if not org:
            caveats.append(
                Caveat(
                    code="SNYK_NO_ORG",
                    title="Snyk org_id missing",
                    message="Set SNYK_ORG_ID env or binding.parameters.org_id.",
                    severity="warn",
                    remediation="Find your org ID in Snyk UI under Settings → Organization.",
                    references=[],
                )
            )
            return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "snyk_no_org")

        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        }

        project_id = _project(binding)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                if project_id:
                    url = f"{_API}/v1/org/{org}/project/{project_id}/issues"
                    resp = await client.post(url, json={}, headers=headers)
                else:
                    url = f"{_API}/v1/org/{org}/issues"
                    resp = await client.post(url, json={}, headers=headers)

                if resp.status_code >= 400:
                    caveats.append(
                        Caveat(
                            code="SNYK_API_ERROR",
                            title="Snyk API call failed",
                            message=f"HTTP {resp.status_code}: {resp.text[:280]}",
                            severity="error",
                            remediation="Validate org/project IDs and token scopes.",
                            references=[],
                        )
                    )
                    return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "snyk_api_err")

                data = resp.json()
                issues = data.get("issues") or {}
                vulns = (issues.get("vulnerabilities") or {}) if isinstance(issues, dict) else {}

                counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
                if isinstance(vulns, list):
                    for v in vulns:
                        sev = str(v.get("issueData", {}).get("severity") or v.get("severity") or "").lower()
                        if sev in counts:
                            counts[sev] += 1
                elif isinstance(vulns, dict):
                    for k in counts:
                        counts[k] = int(vulns.get(k) or 0)

                score = _score_from_issues(**counts)
                caveats.append(
                    Caveat(
                        code="SNYK_SUMMARY",
                        title="Snyk vulnerability summary",
                        message=(
                            f"critical={counts['critical']} high={counts['high']} "
                            f"medium={counts['medium']} low={counts['low']} → score={score}"
                        ),
                        severity="info",
                        remediation=(
                            "Focus on critical/high; patch or suppress with justification. "
                            "Tune _score_from_issues penalties in snyk_connector.py for your risk posture."
                        ),
                        references=["https://docs.snyk.io/manage-risk/prioritize-issues-for-fixing"],
                    )
                )
                if counts["critical"] > 0:
                    caveats.append(
                        Caveat(
                            code="SNYK_CRITICAL_OPEN",
                            title="Open critical CVEs detected",
                            message=f"{counts['critical']} critical vulnerabilities are unresolved.",
                            severity="error",
                            remediation="Treat critical open vulns as blocker for production deployments.",
                            references=[],
                        )
                    )

        except httpx.RequestError as exc:
            caveats.append(
                Caveat(
                    code="SNYK_NETWORK",
                    title="Cannot reach Snyk API",
                    message=str(exc),
                    severity="error",
                    remediation="Check internet egress and proxy settings.",
                    references=[],
                )
            )
            return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "snyk_network")

        conf = EvidenceConfidence.HIGH if project_id else EvidenceConfidence.MEDIUM
        return _ret(now, score, conf, caveats, "snyk_ok")


def _ret(
    now: datetime,
    score: float | None,
    conf: EvidenceConfidence,
    caveats: list[Caveat],
    note: str,
) -> EvidenceCollectionPayload:
    return EvidenceCollectionPayload(
        score_0_10=score,
        confidence=conf,
        evidence_sources=["snyk"],
        caveats=caveats,
        last_evidence_at=now,
        next_check_at=now + timedelta(hours=6),
        connector_notes=note,
    )
