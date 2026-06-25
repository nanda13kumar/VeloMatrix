# Coding standards (VeloMatrix)

- **Backend:** Python 3.12+, type hints on public functions, Pydantic v2 for IO models, FastAPI routers stay thin — orchestration lives under `application/`.
- **Domain rules:** No FastAPI / HTTP imports in `domain/` or `application/` (only ports + pure logic).
- **Adapters:** One module per vendor integration; map vendor payloads to internal `EvidenceRecord` shapes.
- **Frontend:** Functional React components, single `config.js` for bootstrap, `services/api.js` for HTTP — no raw `fetch` scattered in UI.
- **UX copy:** Prefer `caveats[]` from API over hard-coded strings where possible.
- **Security:** Never commit `.env`; connectors read secrets via env or a future vault adapter.
- **Ports:** `backend.port` / `frontend.port` live only in repo-root **`application.properties`** (defaults apply if omitted). For Docker Compose host mappings, run **`scripts/docker-up.sh`** or `eval "$(python3 scripts/emit_compose_env.py)"` first.
