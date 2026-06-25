"""Register evidence connectors."""

from __future__ import annotations

from domain.ports import IEvidenceConnector

_CONNECTORS: dict[str, type[IEvidenceConnector]] = {}


def register(cls: type[IEvidenceConnector]) -> type[IEvidenceConnector]:
    key = getattr(cls, "key", None)
    if not key or key == "abstract":
        raise ValueError(f"Connector {cls} must define non-empty `key`")
    _CONNECTORS[key] = cls
    return cls


def _load_all() -> None:
    """Import every connector module once so their @register decorators fire."""
    from adapters.connectors import (  # noqa: PLC0415
        github_connector,
        loki_connector,
        noop_connector,
        postgres_connector,
        prometheus_connector,
        snyk_connector,
        sonar_connector,
        static_connector,
        trivy_connector,
    )
    # reference them so linters don't drop the imports
    _ = (
        github_connector,
        loki_connector,
        noop_connector,
        postgres_connector,
        prometheus_connector,
        snyk_connector,
        sonar_connector,
        static_connector,
        trivy_connector,
    )


def get_connector(connector_id: str) -> IEvidenceConnector:
    _load_all()
    from adapters.connectors.noop_connector import UnknownConnector  # noqa: PLC0415

    norm = (connector_id or "").strip().lower()
    cls = _CONNECTORS.get(norm)
    if not cls:
        return UnknownConnector()
    return cls()


def list_connector_ids() -> list[str]:
    _load_all()
    return sorted(_CONNECTORS.keys())


def connector_metadata() -> list[dict]:
    """Return display metadata for each registered connector."""
    _load_all()
    meta_map = {
        "static": {
            "label": "Static parameters",
            "description": "Scores from local JSON parameters — intended for gitignored demo/seed data.",
            "when_to_use": "Development, local demo, or initial baseline before live integrations.",
            "required_env": [],
            "required_params": ["score_0_10"],
        },
        "placeholder": {
            "label": "Placeholder (no-op)",
            "description": "Explicit wiring that defers collection — surfaces an actionable caveat.",
            "when_to_use": "Future integration planned but not yet wired.",
            "required_env": [],
            "required_params": [],
        },
        "loki_logql": {
            "label": "Loki / LogQL",
            "description": "Executes a LogQL query against a Loki-compatible endpoint.",
            "when_to_use": "Deployment frequency, error rate, request latency from structured logs.",
            "required_env": ["LOKI_BASE_URL"],
            "required_params": ["base_url (or env)", "query_body (LogQL)"],
        },
        "prometheus_promql": {
            "label": "Prometheus / PromQL",
            "description": "Instant PromQL query → 0–10 via configurable score_mode (raw/ratio/inverse_ratio/threshold).",
            "when_to_use": "SLO burn-rate, availability %, error budget, alert rule coverage.",
            "required_env": ["PROMETHEUS_URL"],
            "required_params": ["base_url (or env)", "query_body (PromQL)", "score_mode"],
        },
        "postgres_sql": {
            "label": "PostgreSQL / SQL",
            "description": "SELECT returning a single numeric value; first column of first row becomes the score.",
            "when_to_use": "Warehouse queries, DORA metrics from event store, custom maturity rollups.",
            "required_env": ["DATABASE_URL"],
            "required_params": ["query_body (SELECT)"],
        },
        "sonarqube_rest": {
            "label": "SonarQube REST",
            "description": "Pulls component measures (coverage, bugs, vulnerabilities, security_rating).",
            "when_to_use": "SAST coverage gate, code smell aging, security rating.",
            "required_env": ["SONARQUBE_URL", "SONARQUBE_TOKEN"],
            "required_params": ["base_url (or env)", "project_key"],
        },
        "snyk_rest": {
            "label": "Snyk REST",
            "description": "Aggregates open vulnerabilities from a Snyk org or project; penalties map to 0–10.",
            "when_to_use": "SCA and container vulnerability posture per product.",
            "required_env": ["SNYK_TOKEN", "SNYK_ORG_ID"],
            "required_params": ["org_id (or env)", "project_id (optional)"],
        },
        "trivy_json": {
            "label": "Trivy JSON",
            "description": "Parses a Trivy `--format json` report from HTTP URL or local file path.",
            "when_to_use": "Container and filesystem scan posture; CI artifact-based scoring.",
            "required_env": [],
            "required_params": ["report_url or report_path"],
        },
        "github_rest": {
            "label": "GitHub REST",
            "description": "Token check + optional rate-limit probe; v1 wires GraphQL queries for DORA signals.",
            "when_to_use": "Deployment frequency, PR age, branch protection, secret scanning status.",
            "required_env": ["GITHUB_TOKEN"],
            "required_params": ["token (or env)"],
        },
    }
    out = []
    for cid in list_connector_ids():
        m = meta_map.get(cid, {})
        out.append({
            "id": cid,
            "label": m.get("label", cid),
            "description": m.get("description", ""),
            "when_to_use": m.get("when_to_use", ""),
            "required_env": m.get("required_env", []),
            "required_params": m.get("required_params", []),
        })
    return out
