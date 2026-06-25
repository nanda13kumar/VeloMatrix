#!/usr/bin/env bash
# Run Docker Compose with ports taken from application.properties (same source as apps).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
eval "$("$ROOT/scripts/emit_compose_env.py")"
exec docker compose -f "$ROOT/docker-compose.yml" --project-directory "$ROOT" "$@"
