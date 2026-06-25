#!/usr/bin/env python3
"""Print shell `export` lines for Docker Compose host ports (from application.properties)."""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
os.environ["APPLICATION_PROPERTIES"] = str(ROOT / "application.properties")
sys.path.insert(0, str(ROOT / "backend" / "src"))

from infrastructure.application_properties import get_backend_port, get_frontend_port  # noqa: E402

if __name__ == "__main__":
    print(f"export BACKEND_PORT={get_backend_port()}")
    print(f"export FRONTEND_PORT={get_frontend_port()}")
