"""
Load key=value pairs from application.properties (Java-style; # comments).

Ports are read from this file only (with in-code defaults when a key is absent).
Resolution order:
  1. Path in env APPLICATION_PROPERTIES (recommended in Docker).
  2. Walk upward from cwd, then from this file's location, looking for application.properties.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000


def _parse_properties(content: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        k = key.strip()
        v = value.strip()
        if k:
            out[k] = v
    return out


def _search_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.environ.get("APPLICATION_PROPERTIES", "").strip()
    if env_path:
        paths.append(Path(env_path).expanduser().resolve())

    cwd = Path.cwd().resolve()
    for start in (cwd, Path(__file__).resolve().parent):
        p = start
        for _ in range(10):
            paths.append(p / "application.properties")
            if p.parent == p:
                break
            p = p.parent

    seen: set[Path] = set()
    unique: list[Path] = []
    for item in paths:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


@lru_cache
def load_application_properties() -> dict[str, str]:
    for candidate in _search_paths():
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError:
                continue
            return _parse_properties(text)
    return {}


def get_backend_port() -> int:
    raw = load_application_properties().get("backend.port")
    if raw is None or raw == "":
        return DEFAULT_BACKEND_PORT
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_BACKEND_PORT


def get_frontend_port() -> int:
    raw = load_application_properties().get("frontend.port")
    if raw is None or raw == "":
        return DEFAULT_FRONTEND_PORT
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_FRONTEND_PORT


def get_properties_file_path() -> str | None:
    for candidate in _search_paths():
        if candidate.is_file():
            return str(candidate)
    return None
