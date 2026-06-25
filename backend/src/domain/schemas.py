"""Pydantic schemas shared by API and domain services."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from domain.enums import EvidenceConfidence, MaturityBand, QueryDialect


class Caveat(BaseModel):
    code: str
    message: str
    severity: str = "info"  # info | warn | error
    title: str = ""
    remediation: str = ""
    references: list[str] = Field(default_factory=list)


class SubDimensionScore(BaseModel):
    id: str
    title: str
    description: str
    weight: float = Field(ge=0.1, le=1.0)
    score_0_10: float | None = None
    weighted_contribution: float | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.UNKNOWN
    non_negotiable: bool = False
    tradeoff_summary: str = ""
    importance_rationale: str = ""
    weight_rationale: str = ""
    guide_overview: str = ""
    guide_signals: list[str] = Field(default_factory=list)
    last_evidence_at: datetime | None = None
    next_check_at: datetime | None = None
    evidence_sources: list[str] = Field(default_factory=list)
    caveats: list[Caveat] = Field(default_factory=list)


class DimensionScore(BaseModel):
    id: str
    title: str
    description: str
    weight: float = Field(ge=0.0, le=1.0, description="Roll-up weight toward product 0–10")
    band: MaturityBand
    numeric_0_10: float | None = None
    dimension_importance: str = ""
    subdimensions: list[SubDimensionScore] = Field(default_factory=list)
    caveats: list[Caveat] = Field(default_factory=list)


class ProductScoreSnapshot(BaseModel):
    product_id: str
    product_name: str
    overall_0_10: float | None
    computed_at: datetime
    policy_version: str
    dimensions: list[DimensionScore]
    caveats: list[Caveat] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    id: str
    product_id: str
    subdimension_id: str
    connector_id: str
    dialect: QueryDialect
    collected_at: datetime
    next_scheduled_at: datetime | None
    summary: str
    raw_redacted: dict[str, Any] = Field(default_factory=dict)
    confidence: EvidenceConfidence = EvidenceConfidence.MEDIUM


class ProductSummary(BaseModel):
    id: str
    name: str
    tier: str = "standard"
    team: str | None = None


class BindingSpec(BaseModel):
    """Admin: how a sub-dimension is fed by a datasource (connector plugin)."""

    id: str = ""
    subdimension_id: str = ""
    connector_id: str
    dialect: QueryDialect
    query_body: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = "0 */6 * * *"
    filters: dict[str, Any] = Field(default_factory=dict)


class ConnectorTestResult(BaseModel):
    ok: bool
    connector_id: str
    dry_run: bool = True
    message: str
    caveats: list[Caveat] = Field(default_factory=list)
    preview: dict[str, Any] = Field(default_factory=dict)


class ProductBindingsFile(BaseModel):
    """On-disk shape for bindings.json."""

    version: str = "1"
    bindings: dict[str, dict[str, BindingSpec]] = Field(default_factory=dict)


class SubDimensionTemplate(BaseModel):
    """Policy/catalog row — static copy merged with connector evidence at snapshot time."""

    id: str
    title: str
    description: str
    weight: float = Field(ge=0.1, le=1.0)
    non_negotiable: bool = False
    tradeoff_summary: str = ""
    importance_rationale: str = ""
    weight_rationale: str = ""
    guide_overview: str = ""
    guide_signals: list[str] = Field(default_factory=list)


class DimensionTemplate(BaseModel):
    id: str
    title: str
    description: str
    weight: float = Field(ge=0.0, le=1.0)
    dimension_importance: str = ""
    subdimensions: list[SubDimensionTemplate] = Field(default_factory=list)


class CatalogProduct(BaseModel):
    id: str
    name: str
    tier: str = "standard"
    team: str | None = None
    dimensions: list[DimensionTemplate] = Field(default_factory=list)


class CatalogRoot(BaseModel):
    policy_version: str = "unset"
    products: list[CatalogProduct] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    genai_mode: str  # stub | live


class DataLayoutInfo(BaseModel):
    """Tells the UI where policy lives (local workspace is gitignored by default)."""

    data_base_path: str
    catalog_present: bool
    bindings_present: bool
    registered_connectors: list[str] = Field(default_factory=list)
    admin_auth_enabled: bool = False


class BootstrapResponse(BaseModel):
    """Resolved local configuration (ports come only from application.properties)."""

    backend_port: int
    frontend_port: int
    application_properties_path: str | None = None
    data_layout: DataLayoutInfo | None = None
