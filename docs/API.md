# HTTP API — v0 scaffold

Interactive OpenAPI: **`http://localhost:<backend.port>/docs`** where `<backend.port>` comes from **`application.properties`** (default `8000`).

Base path: **`/api/v1`**

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + `genai_mode` (`stub` or `live`) |
| GET | `/bootstrap` | Effective `backend_port`, `frontend_port`, resolved `application.properties` path, and `data_layout` (local workspace + registered connectors) |
| GET | `/products` | Portfolio list from `catalog.json` |
| GET | `/products/{product_id}/score` | Full `ProductScoreSnapshot` built from **catalog + bindings + connector plugins** |
| GET | `/products/{product_id}/dimensions/{dimension_id}` | v0 returns full snapshot; UI filters by `dimension_id` |
| POST | `/products/{product_id}/dimensions/explain` | GenAI helper (stub unless API key wired) |
| GET | `/admin/products/{product_id}/bindings` | Map of `subdimension_id → BindingSpec` persisted in `bindings.json` |
| PUT | `/admin/products/{product_id}/bindings/{subdimension_id}` | Upsert a binding (writes `bindings.json`) |
| DELETE | `/admin/products/{product_id}/bindings/{subdimension_id}` | Remove binding row |
| POST | `/admin/connectors/test` | Executes a connector against a binding payload (dry-run; returns caveats + preview) |
| GET | `/admin/connectors` | Full metadata catalog for all registered connector plugins |
| GET | `/admin/products/{product_id}/evidence` | List sub-dimension IDs that have at least one evidence record |
| GET | `/admin/products/{product_id}/evidence/{subdimension_id}?limit=20` | NDJSON log for one sub-dimension (last N runs) |

## Connectors (plugins)

Registered `connector_id` values (see `adapters/connectors/`):

- `static` — reads `parameters.score_0_10`, `evidence_sources`, `confidence` (intended for **gitignored** local demo data)
- `loki_logql` — optional live Loki calls when `LOKI_BASE_URL` / `LOKI_BEARER_TOKEN` (or binding parameters) are set
- `postgres_sql` — optional `SELECT …` when `DATABASE_URL` is set and `asyncpg` is installed
- `sonarqube_rest` — optional Sonar Web API when `SONARQUBE_URL` / `SONARQUBE_TOKEN` (+ `parameters.project_key`) are set
- `github_rest` — optional GitHub REST probe when `GITHUB_TOKEN` is set
- `placeholder` — explicit no-op wiring (actionable caveats)

## Local workspace

Default path: `<repo-root>/local/demo-data/`. Override with `VOLOMATRIX_DATA_BASE`.

Generate starter files:

```bash
python3 scripts/seed_local_demo.py
```

### POST explain body

```json
{
  "subdimension_id": "sec-sast",
  "question": "What should we improve first?",
  "context": { "dimension_title": "Security & Compliance" }
}
```

## Admin authentication

Admin routes (`/admin/*`) are guarded by `X-VeloMatrix-Admin-Key` header.
- If `VELOMATRIX_ADMIN_API_KEY` env is **not set**: routes are open (dev mode — surfaced in `/bootstrap`).
- If the env **is set**: clients must send `X-VeloMatrix-Admin-Key: <value>` or receive HTTP 403.

Set via `.env`:
```
VELOMATRIX_ADMIN_API_KEY=changeme-for-production
```

The frontend **Admin key** button stores the key in `sessionStorage` (never in source code or localStorage).

- All successful JSON responses are camelCase-friendly where Pydantic aliases are added later; v0 uses snake_case field names from Python models.
- Every future score payload should include **`caveats`** — same philosophy as Augur/Sentinel.
