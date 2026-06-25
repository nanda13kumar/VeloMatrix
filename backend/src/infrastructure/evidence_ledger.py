"""File-based evidence ledger — NDJSON append log under local/demo-data/evidence/."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from domain.collection import EvidenceCollectionPayload


def _ledger_dir() -> Path:
    from infrastructure.data_paths import resolve_data_base

    return resolve_data_base() / "evidence"


def _entry_path(product_id: str, subdimension_id: str) -> Path:
    safe_pid = product_id.replace("/", "_").replace("\\", "_")
    safe_sid = subdimension_id.replace("/", "_").replace("\\", "_")
    return _ledger_dir() / f"{safe_pid}__{safe_sid}.ndjson"


def append_evidence(
    *,
    product_id: str,
    subdimension_id: str,
    connector_id: str,
    payload: EvidenceCollectionPayload,
) -> None:
    """Append one collected evidence record to the NDJSON log (fire-and-forget)."""
    path = _entry_path(product_id, subdimension_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "product_id": product_id,
            "subdimension_id": subdimension_id,
            "connector_id": connector_id,
            "score_0_10": payload.score_0_10,
            "confidence": payload.confidence.value,
            "evidence_sources": payload.evidence_sources,
            "connector_notes": payload.connector_notes,
            "caveats": [c.model_dump() for c in payload.caveats],
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass  # ledger write failures must never block score computation


def read_evidence(
    product_id: str,
    subdimension_id: str,
    *,
    limit: int = 20,
) -> list[dict]:
    """Read the last `limit` records for a sub-dimension."""
    path = _entry_path(product_id, subdimension_id)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict] = []
    for line in reversed(lines[-limit * 2:]):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(records) >= limit:
            break
    return records


def list_evidence_keys(product_id: str) -> list[str]:
    """List sub-dimension IDs that have at least one evidence record."""
    ledger_dir = _ledger_dir()
    if not ledger_dir.exists():
        return []
    prefix = product_id.replace("/", "_").replace("\\", "_") + "__"
    keys = []
    for p in sorted(ledger_dir.glob(f"{prefix}*.ndjson")):
        sid = p.stem[len(prefix):]
        keys.append(sid)
    return keys
