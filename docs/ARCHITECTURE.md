# VeloMatrix — system architecture

This document mirrors the root `README.md` with extra implementation detail for contributors.

## Layering (hexagonal)

| Layer | Responsibility |
|-------|------------------|
| `api/` | HTTP routes, validation, DTO mapping — **no business rules** |
| `application/` | Use cases: scoring orchestration, product roll-ups |
| `domain/` | Entities, enums, ports (interfaces), shared Pydantic schemas |
| `adapters/` | Connectors (GitHub, Sonar, Loki, …), GenAI stub/live |
| `infrastructure/` | Persistence, queues, secrets (PostgreSQL in a later milestone) |

## Connector plugin model (planned)

Each connector implements a small internal protocol:

1. `health()` — credentials + reachability
2. `execute(binding)` — run `QueryDialect` + template
3. `normalize()` — map vendor JSON to `EvidenceRecord`

Bindings (admin-configured) live outside vendor code; adapters stay thin.

## Async jobs (planned)

Scheduled collection pushes rows into an **evidence ledger**; scoring reads the latest evidence + **policy version** and emits an immutable `ProductScoreSnapshot`.

See sequence diagrams in `README.md`.
