# Data model — conceptual & API shapes

Authoritative runtime schemas are **Pydantic models** in `backend/src/domain/schemas.py` (also exposed as OpenAPI at `/docs`).

## Core entities

### Product

Logical service or application line (`ProductSummary`).

### Dimension

High-level maturity pillar (e.g. Security, DORA). Has:

- `weight` — contribution to overall **0–10** product score
- `band` — `sit` | `crawl` | `walk` | `run` derived from numeric roll-up
- `numeric_0_10` — aggregated sub-dimension score

### SubDimension

Measurable leaf with:

- `weight` ∈ [0.1, 1.0]
- `score_0_10` and `weighted_contribution`
- `evidence_sources[]`, freshness fields, `caveats[]`
- `non_negotiable` + `tradeoff_summary` for UX copy

### EvidenceRecord (ledger)

One collection event: connector, dialect, redacted payload summary, confidence.

### ProductScoreSnapshot

Versioned computed view for dashboards; includes `policy_version` for audit.

## ER-style relationships (logical)

```text
Product 1──* DimensionScore (snapshot embed)
DimensionScore 1──* SubDimensionScore
Product 1──* EvidenceRecord (via subdimension + connector)
BindingSpec *──1 SubDimension (configures ingestion)
```

PostgreSQL DDL will land under `infrastructure/migrations/` in a future PR.
