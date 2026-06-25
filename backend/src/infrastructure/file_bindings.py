"""Load / persist bindings.json (connector wiring per product × sub-dimension)."""

from __future__ import annotations

import json
from pathlib import Path

from domain.schemas import BindingSpec, ProductBindingsFile

from infrastructure.data_paths import bindings_path


def load_bindings() -> ProductBindingsFile:
    path = bindings_path()
    if not path.exists():
        return ProductBindingsFile()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProductBindingsFile.model_validate(data)


def save_bindings(bindings: ProductBindingsFile, path: Path | None = None) -> None:
    p = path or bindings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bindings.model_dump_json(indent=2), encoding="utf-8")


def upsert_binding(product_id: str, subdimension_id: str, spec: BindingSpec) -> ProductBindingsFile:
    file = load_bindings()
    inner = file.bindings.setdefault(product_id, {})
    spec = spec.model_copy(update={"subdimension_id": subdimension_id})
    if not spec.id:
        spec = spec.model_copy(update={"id": f"{product_id}:{subdimension_id}:{spec.connector_id}"})
    inner[subdimension_id] = spec
    save_bindings(file)
    return file


def delete_binding(product_id: str, subdimension_id: str) -> ProductBindingsFile:
    file = load_bindings()
    inner = file.bindings.get(product_id)
    if inner and subdimension_id in inner:
        del inner[subdimension_id]
        if not inner:
            del file.bindings[product_id]
    save_bindings(file)
    return file
