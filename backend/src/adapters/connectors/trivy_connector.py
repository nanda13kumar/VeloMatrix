"""Trivy connector — parses Trivy JSON scan output from a URL or local file path.

Trivy produces JSON with `Results[*].Vulnerabilities[*].Severity`.
This connector fetches that JSON (HTTP or file://) and scores it.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence
from domain.ports import IEvidenceConnector
from domain.schemas import BindingSpec, Caveat

from adapters.connectors.registry import register


def _fb(b: BindingSpec) -> float | None:
    raw = (b.parameters or {}).get("fallback_score_0_10")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _score_trivy(results: list[dict[str, Any]]) -> tuple[float, dict[str, int]]:
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for r in results:
        for v in r.get("Vulnerabilities") or []:
            sev = str(v.get("Severity") or "UNKNOWN").upper()
            if sev in counts:
                counts[sev] += 1
            else:
                counts["UNKNOWN"] += 1
    penalty = (
        min(counts["CRITICAL"] * 3.0, 6.0)
        + min(counts["HIGH"] * 1.0, 3.0)
        + min(counts["MEDIUM"] * 0.2, 1.0)
    )
    return round(max(0.0, 10.0 - penalty), 2), counts


@register
class TrivyJsonConnector(IEvidenceConnector):
    """
    Fetches a Trivy JSON report and scores it.

    Sources (tried in order):
    1. ``parameters.report_url`` — HTTP(S) URL to a JSON report (e.g. from S3 pre-signed URL or CI artifact)
    2. ``parameters.report_path`` — absolute path on the API server filesystem (gitignored demo data)
    3. Environment ``TRIVY_REPORT_PATH``

    Tip: pipe Trivy output to S3 or a local file then point this connector at it:
      trivy image --format json --output /tmp/report.json my-image:latest
    """

    key = "trivy_json"

    async def collect(
        self,
        *,
        product_id: str,
        binding: BindingSpec,
    ) -> EvidenceCollectionPayload:
        now = datetime.now(tz=UTC)
        caveats: list[Caveat] = []
        p = binding.parameters or {}

        report_url = str(p.get("report_url") or "").strip()
        report_path = str(p.get("report_path") or os.environ.get("TRIVY_REPORT_PATH", "") or "").strip()

        body: dict[str, Any] | None = None

        if report_url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.get(report_url)
                    if r.status_code >= 400:
                        caveats.append(
                            Caveat(
                                code="TRIVY_URL_ERROR",
                                title="Trivy report URL returned error",
                                message=f"HTTP {r.status_code}: {r.text[:200]}",
                                severity="error",
                                remediation="Verify the URL and credentials (pre-signed URL expiry, S3 ACL).",
                                references=[],
                            )
                        )
                        return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "trivy_url_err")
                    body = r.json()
            except httpx.RequestError as exc:
                caveats.append(
                    Caveat(
                        code="TRIVY_NETWORK",
                        title="Cannot fetch Trivy report",
                        message=str(exc),
                        severity="error",
                        remediation="Check network, DNS, and TLS.",
                        references=[],
                    )
                )
                return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "trivy_network")

        elif report_path:
            path = Path(report_path)
            if not path.exists():
                caveats.append(
                    Caveat(
                        code="TRIVY_FILE_MISSING",
                        title="Trivy report file not found",
                        message=f"Expected at {path}",
                        severity="warn",
                        remediation=(
                            "Run Trivy in CI and output JSON: "
                            "`trivy image --format json -o /path/to/report.json <image>`. "
                            "Update binding.parameters.report_path or TRIVY_REPORT_PATH env."
                        ),
                        references=["https://aquasecurity.github.io/trivy/latest/docs/configuration/output/"],
                    )
                )
                return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "trivy_file_missing")
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                caveats.append(
                    Caveat(
                        code="TRIVY_PARSE_ERROR",
                        title="Cannot parse Trivy JSON",
                        message=str(exc)[:300],
                        severity="error",
                        remediation="Ensure `--format json` is used (not table or sarif).",
                        references=[],
                    )
                )
                return _ret(now, _fb(binding), EvidenceConfidence.LOW, caveats, "trivy_parse_err")
        else:
            caveats.append(
                Caveat(
                    code="TRIVY_NO_SOURCE",
                    title="No Trivy report source configured",
                    message="Set parameters.report_url or parameters.report_path (or TRIVY_REPORT_PATH env).",
                    severity="warn",
                    remediation=(
                        "Add report_url pointing to a Trivy JSON artifact, or "
                        "set report_path to a local JSON file (can be gitignored under local/)."
                    ),
                    references=[],
                )
            )
            return _ret(now, _fb(binding), EvidenceConfidence.UNKNOWN, caveats, "trivy_no_src")

        results: list[dict[str, Any]] = []
        if isinstance(body, dict):
            results = body.get("Results") or []
        elif isinstance(body, list):
            results = body

        schema_version = body.get("SchemaVersion", 0) if isinstance(body, dict) else 0
        if schema_version < 2:
            caveats.append(
                Caveat(
                    code="TRIVY_OLD_SCHEMA",
                    title="Trivy schema version may be outdated",
                    message=f"Found SchemaVersion={schema_version}. Upgrade Trivy to v0.45+.",
                    severity="info",
                    remediation="Use latest Trivy for consistent JSON structure.",
                    references=[],
                )
            )

        score, counts = _score_trivy(results)
        caveats.append(
            Caveat(
                code="TRIVY_SUMMARY",
                title="Trivy scan summary",
                message=(
                    f"CRITICAL={counts['CRITICAL']} HIGH={counts['HIGH']} "
                    f"MEDIUM={counts['MEDIUM']} LOW={counts['LOW']} → score={score}"
                ),
                severity="info" if counts["CRITICAL"] == 0 else "warn",
                remediation=(
                    "Prioritize CRITICAL and HIGH; use `.trivyignore` with expiry dates for accepted risks. "
                    "Track accepted entries in your risk register."
                ),
                references=["https://aquasecurity.github.io/trivy/latest/docs/configuration/filtering/"],
            )
        )
        if counts["CRITICAL"] > 0:
            caveats.append(
                Caveat(
                    code="TRIVY_CRITICAL",
                    title=f"{counts['CRITICAL']} critical CVE(s) found",
                    message="Critical findings present in the scan report.",
                    severity="error",
                    remediation="Patch base image or dependency. If accepted, document in risk register with review date.",
                    references=[],
                )
            )

        conf = EvidenceConfidence.HIGH if schema_version >= 2 else EvidenceConfidence.MEDIUM
        return _ret(now, score, conf, caveats, "trivy_ok")


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
        evidence_sources=["trivy"],
        caveats=caveats,
        last_evidence_at=now,
        next_check_at=now + timedelta(hours=6),
        connector_notes=note,
    )
