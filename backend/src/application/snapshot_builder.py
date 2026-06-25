"""Build ProductScoreSnapshot from catalog + bindings + connector plugins."""

from __future__ import annotations

from datetime import UTC, datetime

from adapters.connectors.registry import get_connector
from domain.collection import EvidenceCollectionPayload
from domain.enums import EvidenceConfidence, MaturityBand
from domain.schemas import (
    BindingSpec,
    Caveat,
    DimensionScore,
    DimensionTemplate,
    ProductBindingsFile,
    ProductScoreSnapshot,
    SubDimensionScore,
    SubDimensionTemplate,
)
from infrastructure.evidence_ledger import append_evidence
from infrastructure.file_bindings import load_bindings
from infrastructure.file_catalog import load_catalog

from application.scoring import band_from_numeric


def _merge_caveats(a: list[Caveat], b: list[Caveat]) -> list[Caveat]:
    return [*a, *b]


async def build_snapshot(product_id: str) -> ProductScoreSnapshot:
    catalog = load_catalog()
    bindings_file = load_bindings()
    now = datetime.now(tz=UTC)

    product = next((p for p in catalog.products if p.id == product_id), None)
    if not product:
        return ProductScoreSnapshot(
            product_id=product_id,
            product_name=product_id,
            overall_0_10=None,
            computed_at=now,
            policy_version=catalog.policy_version or "unset",
            dimensions=[],
            caveats=[
                Caveat(
                    code="NO_CATALOG_OR_PRODUCT",
                    title="Product not found in catalog",
                    message=(
                        "Create `local/demo-data/catalog.json` (gitignored) — run "
                        "`python scripts/seed_local_demo.py` from the repo root."
                    ),
                    severity="warn",
                    remediation="Generate local workspace; set VOLOMATRIX_DATA_BASE if using a custom path.",
                    references=["README.md"],
                )
            ],
        )

    dims_out: list[DimensionScore] = []
    product_caveats: list[Caveat] = []

    for d in product.dimensions:
        dim_score, dim_caveats = await _score_dimension(
            product_id=product_id,
            template=d,
            bindings_file=bindings_file,
        )
        dims_out.append(dim_score)
        product_caveats.extend(dim_caveats)

    overall = _rollup_overall(dims_out)
    product_caveats.append(
        Caveat(
            code="WEIGHTING_MODEL",
            title="How the 0–10 is computed",
            message=(
                "Product score = Σ (dimension.numeric_0_10 × dimension.weight). "
                "Each dimension.numeric is the weighted mean of sub-dimension scores (by sub-weight). "
                "Dimension band (sit/crawl/walk/run) maps from that numeric via policy thresholds."
            ),
            severity="info",
            remediation="Tune weights in catalog.json; keep Σ dimension.weight = 1.0 per product.",
            references=["docs/DATA_MODEL.md"],
        )
    )

    return ProductScoreSnapshot(
        product_id=product.id,
        product_name=product.name,
        overall_0_10=round(overall, 2) if overall is not None else None,
        computed_at=now,
        policy_version=catalog.policy_version,
        dimensions=dims_out,
        caveats=product_caveats,
    )


async def _score_dimension(
    *,
    product_id: str,
    template: DimensionTemplate,
    bindings_file: ProductBindingsFile,
) -> tuple[DimensionScore, list[Caveat]]:
    caveats: list[Caveat] = []
    subs: list[SubDimensionScore] = []
    bindings_for_product = bindings_file.bindings.get(product_id, {})

    for sub in template.subdimensions:
        binding = bindings_for_product.get(sub.id)
        collected = await _collect_sub(product_id, binding, sub)
        w = sub.weight
        score = collected.score_0_10
        weighted = (score * w) if score is not None else None
        subs.append(
            SubDimensionScore(
                id=sub.id,
                title=sub.title,
                description=sub.description,
                weight=w,
                score_0_10=score,
                weighted_contribution=round(weighted, 4) if weighted is not None else None,
                confidence=collected.confidence,
                non_negotiable=sub.non_negotiable,
                tradeoff_summary=sub.tradeoff_summary,
                importance_rationale=sub.importance_rationale,
                weight_rationale=sub.weight_rationale,
                guide_overview=sub.guide_overview,
                guide_signals=sub.guide_signals,
                last_evidence_at=collected.last_evidence_at,
                next_check_at=collected.next_check_at,
                evidence_sources=collected.evidence_sources,
                caveats=collected.caveats,
            )
        )

    numeric = _weighted_mean_subs(subs)
    band = band_from_numeric(numeric) if numeric is not None else MaturityBand.SIT

    if not template.subdimensions:
        caveats.append(
            Caveat(
                code="DIM_NO_SUBS",
                title="Dimension has no sub-dimensions in catalog",
                message=f"`{template.id}` defines no sub-rows — numeric score is policy-only.",
                severity="info",
                remediation="Add subdimensions in catalog.json for drill-down and evidence.",
                references=[],
            )
        )

    return (
        DimensionScore(
            id=template.id,
            title=template.title,
            description=template.description,
            weight=template.weight,
            band=band,
            numeric_0_10=round(numeric, 2) if numeric is not None else None,
            dimension_importance=template.dimension_importance,
            subdimensions=subs,
            caveats=caveats,
        ),
        [],
    )


async def _collect_sub(
    product_id: str,
    binding: BindingSpec | None,
    sub: SubDimensionTemplate,
) -> EvidenceCollectionPayload:
    if binding is None:
        now = datetime.now(tz=UTC)
        return EvidenceCollectionPayload(
            score_0_10=None,
            confidence=EvidenceConfidence.UNKNOWN,
            evidence_sources=[],
            caveats=[
                Caveat(
                    code="NO_BINDING",
                    title="No datasource binding",
                    message=(
                        f"Sub-dimension `{sub.id}` has no entry in bindings.json — "
                        "scores cannot be computed from external systems."
                    ),
                    severity="warn",
                    remediation="Admin → Bindings: add connector (start with `static` for local scores).",
                    references=["docs/API.md"],
                )
            ],
            last_evidence_at=now,
            next_check_at=now,
            connector_notes="no_binding",
        )

    connector = get_connector(binding.connector_id)
    payload = await connector.collect(product_id=product_id, binding=binding)
    append_evidence(
        product_id=product_id,
        subdimension_id=sub.id,
        connector_id=binding.connector_id,
        payload=payload,
    )
    return payload


def _weighted_mean_subs(subs: list[SubDimensionScore]) -> float | None:
    nums: list[tuple[float, float]] = []
    for s in subs:
        if s.score_0_10 is None:
            continue
        nums.append((s.score_0_10, s.weight))
    if not nums:
        return None
    return sum(x * w for x, w in nums) / sum(w for _, w in nums)


def _rollup_overall(dims: list[DimensionScore]) -> float | None:
    parts: list[tuple[float, float]] = []
    for d in dims:
        if d.numeric_0_10 is None:
            continue
        parts.append((d.numeric_0_10, d.weight))
    if not parts:
        return None
    return sum(x * w for x, w in parts) / sum(w for _, w in parts)
