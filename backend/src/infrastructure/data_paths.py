"""Resolve gitignored local workspace paths (catalog + bindings)."""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "application.properties").exists():
            return p
    return None


def resolve_data_base() -> Path:
    env = os.environ.get("VOLOMATRIX_DATA_BASE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    root = find_repo_root()
    if root:
        return (root / "local" / "demo-data").resolve()
    return (Path.cwd() / "local" / "demo-data").resolve()


def catalog_path() -> Path:
    return resolve_data_base() / "catalog.json"


def bindings_path() -> Path:
    return resolve_data_base() / "bindings.json"
