"""Load / persist catalog.json (policy + product dimension templates)."""

from __future__ import annotations

import json
from pathlib import Path

from domain.schemas import CatalogRoot

from infrastructure.data_paths import catalog_path


def load_catalog() -> CatalogRoot:
    path = catalog_path()
    if not path.exists():
        return CatalogRoot()
    data = json.loads(path.read_text(encoding="utf-8"))
    return CatalogRoot.model_validate(data)


def save_catalog(catalog: CatalogRoot, path: Path | None = None) -> None:
    p = path or catalog_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
