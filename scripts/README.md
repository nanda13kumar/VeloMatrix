# Scripts

| Script | Purpose |
|--------|---------|
| `emit_compose_env.py` | Reads repo-root `application.properties` and prints `export BACKEND_PORT=…` / `export FRONTEND_PORT=…` for Docker Compose host mappings. |
| `docker-up.sh` | Runs `emit_compose_env.py` then `docker compose` so published ports always match the same file the apps use. |

Usage:

```bash
chmod +x scripts/docker-up.sh
./scripts/docker-up.sh up --build
```

Or manually:

```bash
eval "$(python3 scripts/emit_compose_env.py)"
docker compose up --build
```
