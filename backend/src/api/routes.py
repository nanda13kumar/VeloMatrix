"""FastAPI HTTP surface — thin adapter."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from adapters.connectors.registry import connector_metadata, get_connector, list_connector_ids
from adapters.stub_ai import StubAIExplainer
from application.product_service import ProductService
from config import get_settings
from domain.schemas import (
    BindingSpec,
    BootstrapResponse,
    ConnectorTestResult,
    DataLayoutInfo,
    HealthResponse,
    ProductScoreSnapshot,
    ProductSummary,
)
from infrastructure.data_paths import bindings_path, catalog_path, resolve_data_base
from infrastructure.evidence_ledger import list_evidence_keys, read_evidence
from infrastructure.file_bindings import delete_binding, load_bindings, upsert_binding

router = APIRouter(prefix="/api/v1")

_product_service = ProductService()
_ai = StubAIExplainer()

_ADMIN_KEY_HEADER = APIKeyHeader(name="X-VeloMatrix-Admin-Key", auto_error=False)


async def _require_admin(api_key: str | None = Security(_ADMIN_KEY_HEADER)) -> None:
    s = get_settings()
    expected = s.admin_api_key
    if not expected:
        return  # no key configured → open in dev mode (surfaced in bootstrap)
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing admin API key (X-VeloMatrix-Admin-Key).")


# ──────────────────────────────────────────────────────────────────────────────
# Public endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        status="ok",
        version="0.2.0",
        genai_mode="live" if s.anthropic_api_key else "stub",
    )


@router.get("/bootstrap", response_model=BootstrapResponse)
async def bootstrap() -> BootstrapResponse:
    s = get_settings()
    base = resolve_data_base()
    return BootstrapResponse(
        backend_port=s.backend_port,
        frontend_port=s.frontend_port,
        application_properties_path=s.application_properties_path,
        data_layout=DataLayoutInfo(
            data_base_path=str(base),
            catalog_present=catalog_path().exists(),
            bindings_present=bindings_path().exists(),
            registered_connectors=list_connector_ids(),
            admin_auth_enabled=bool(s.admin_api_key),
        ),
    )


@router.get("/products", response_model=list[ProductSummary])
async def list_products() -> list[ProductSummary]:
    return await _product_service.list_products()


@router.get("/products/{product_id}/score", response_model=ProductScoreSnapshot)
async def get_product_score(product_id: str) -> ProductScoreSnapshot:
    return await _product_service.get_snapshot(product_id)


@router.get("/products/{product_id}/dimensions/{dimension_id}", response_model=ProductScoreSnapshot)
async def get_dimension_drilldown(product_id: str, dimension_id: str) -> ProductScoreSnapshot:
    snap = await _product_service.get_snapshot(product_id)
    if not any(d.id == dimension_id for d in snap.dimensions):
        raise HTTPException(status_code=404, detail="Dimension not found for product")
    return snap


@router.post("/products/{product_id}/dimensions/explain")
async def explain_subdimension(
    product_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    sub_id = body.get("subdimension_id", "")
    question = body.get("question")
    context = body.get("context") or {}
    return await _ai.explain_subdimension(
        product_id=product_id,
        subdimension_id=str(sub_id),
        user_question=str(question) if question else None,
        context=context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Connector catalog
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/connectors")
async def list_connectors(_: None = Depends(_require_admin)) -> list[dict]:
    return connector_metadata()


# ──────────────────────────────────────────────────────────────────────────────
# Bindings CRUD (admin-guarded)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/products/{product_id}/bindings")
async def list_bindings(product_id: str, _: None = Depends(_require_admin)) -> dict[str, BindingSpec]:
    return load_bindings().bindings.get(product_id, {})


@router.put("/admin/products/{product_id}/bindings/{subdimension_id}")
async def put_binding(
    product_id: str,
    subdimension_id: str,
    body: BindingSpec,
    _: None = Depends(_require_admin),
) -> dict[str, BindingSpec]:
    upsert_binding(product_id, subdimension_id, body)
    return load_bindings().bindings.get(product_id, {})


@router.delete("/admin/products/{product_id}/bindings/{subdimension_id}")
async def remove_binding(
    product_id: str,
    subdimension_id: str,
    _: None = Depends(_require_admin),
) -> dict[str, BindingSpec]:
    delete_binding(product_id, subdimension_id)
    return load_bindings().bindings.get(product_id, {})


@router.post("/admin/connectors/test", response_model=ConnectorTestResult)
async def test_connector(body: BindingSpec, _: None = Depends(_require_admin)) -> ConnectorTestResult:
    connector = get_connector(body.connector_id)
    payload = await connector.collect(product_id="__test__", binding=body)
    has_error = any(c.severity == "error" for c in payload.caveats)
    return ConnectorTestResult(
        ok=not has_error,
        connector_id=body.connector_id,
        dry_run=True,
        message=payload.connector_notes or "completed",
        caveats=payload.caveats,
        preview={
            "score_0_10": payload.score_0_10,
            "confidence": payload.confidence.value,
            "evidence_sources": payload.evidence_sources,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Evidence ledger (read-only)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/products/{product_id}/evidence")
async def list_evidence_subdims(product_id: str, _: None = Depends(_require_admin)) -> list[str]:
    return list_evidence_keys(product_id)


@router.get("/admin/products/{product_id}/evidence/{subdimension_id}")
async def get_evidence_log(
    product_id: str,
    subdimension_id: str,
    limit: int = 20,
    _: None = Depends(_require_admin),
) -> list[dict]:
    return read_evidence(product_id, subdimension_id, limit=min(limit, 100))
