"""Product / portfolio application service."""

from __future__ import annotations

from application.snapshot_builder import build_snapshot
from domain.schemas import ProductScoreSnapshot, ProductSummary
from infrastructure.file_catalog import load_catalog


class ProductService:
    async def list_products(self) -> list[ProductSummary]:
        catalog = load_catalog()
        return [
            ProductSummary(id=p.id, name=p.name, tier=p.tier, team=p.team) for p in catalog.products
        ]

    async def get_snapshot(self, product_id: str) -> ProductScoreSnapshot:
        return await build_snapshot(product_id)
