"""GitHub REST connector — PAT presence + optional rate-limit probe."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import httpx

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


@register
class GithubRestConnector(IEvidenceConnector):
    key = "github_rest"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        params = binding.parameters or {}
        token = str(params.get("token") or os.environ.get("GITHUB_TOKEN", "") or "")
        api_base = str(params.get("api_base") or "https://api.github.com").rstrip("/")

        if not token:
            caveats.append(
                Caveat(
                    code="GITHUB_NO_TOKEN",
                    title="GitHub token missing",
                    message="Set GITHUB_TOKEN (fine-grained or classic) with repo + actions read.",
                    severity="warn",
                    remediation="Export token server-side; never commit to git.",
                    references=["https://docs.github.com/en/rest"],
                )
            )
            return EvidenceCollectionPayload(
                score_0_10=_fb(binding),
                confidence=EvidenceConfidence.LOW,
                evidence_sources=["github"],
                caveats=caveats,
                last_evidence_at=now,
                next_check_at=now + timedelta(hours=6),
                connector_notes="github_no_token",
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(f"{api_base}/rate_limit", headers=headers)
                if r.status_code >= 400:
                    caveats.append(
                        Caveat(
                            code="GITHUB_RATE_LIMIT",
                            title="GitHub API error",
                            message=f"HTTP {r.status_code}: {r.text[:200]}",
                            severity="error",
                            remediation="Validate token scopes and SSO authorization if enforced.",
                            references=[],
                        )
                    )
                    return EvidenceCollectionPayload(
                        score_0_10=_fb(binding),
                        confidence=EvidenceConfidence.LOW,
                        evidence_sources=["github"],
                        caveats=caveats,
                        last_evidence_at=now,
                        next_check_at=now + timedelta(hours=6),
                        connector_notes="github_error",
                    )
                caveats.append(
                    Caveat(
                        code="GITHUB_TOKEN_OK",
                        title="GitHub token accepted",
                        message="v0 uses rate_limit probe only — wire GraphQL queries in binding.query_body next.",
                        severity="info",
                        remediation="Add workflow_dispatch / commit queries and rubric mapping.",
                        references=[],
                    )
                )
        except httpx.RequestError as exc:
            caveats.append(
                Caveat(
                    code="GITHUB_NETWORK",
                    title="Cannot reach GitHub API",
                    message=str(exc),
                    severity="error",
                    remediation="Check egress allowlists.",
                    references=[],
                )
            )

        score = _fb(binding)
        if score is None:
            score = 6.5
            caveats.append(
                Caveat(
                    code="GITHUB_DEFAULT_SCORE",
                    title="Default score applied",
                    message="Set parameters.fallback_score_0_10 until GraphQL-backed rubric ships.",
                    severity="info",
                    remediation="Define explicit scoring from API responses.",
                    references=[],
                )
            )

        return EvidenceCollectionPayload(
            score_0_10=score,
            confidence=EvidenceConfidence.MEDIUM,
            evidence_sources=["github"],
            caveats=caveats,
            last_evidence_at=now,
            next_check_at=now + timedelta(hours=6),
            connector_notes="github_token_ok",
        )


def _fb(binding: BindingSpec) -> float | None:
    raw = (binding.parameters or {}).get("fallback_score_0_10")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
