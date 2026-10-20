# alfa-insight

Аналитика в момент действия: сервис внутри Альфа-Бизнеса, который в момент платежа, депозита или кредита объясняет, что изменилось в мире относительно именно этого действия, с пометкой «факт / позиция банка / вывод AI» на каждом тезисе.

Концепция, слои и демо-сценарий — в [docs/CONCEPT.md](docs/CONCEPT.md).

## Запуск

Все команды — из корня репозитория.

```
docker compose up -d --build    # db (postgres + pgvector), api и front: http://localhost:8000/health, http://localhost:5173
docker compose down
```

Настройки берутся из `.env.example`; свои значения (например, ключ LLM) — в `.env` в корне: `cp .env.example .env`. Этот же `.env` нужен командам, которые запускаются с хоста:

```
cd backend && uv run --env-file ../.env python -m scripts.seed                              # тестовые пользователи из backend/data/seed
cd backend && uv run python -m scripts.gen_schemas && cd ../frontend && npm run gen:types   # JSON Schema и типы фронта из контрактов
docker compose up -d --build --wait && cd frontend && npm run e2e                           # e2e (Playwright)
```

Проверка перед коммитом (ruff, mypy, import-linter, pytest, vitest, сборка) — раздел «Проверка» в [docs/PIPELINE.md](docs/PIPELINE.md).

Репозиторий разделён на `backend/` (Python-монолит: `uv`, `pytest`, `alembic` запускаются оттуда) и `frontend/` (npm workspace: `application`, `app-plugin`, Playwright). Структура — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), правила для агентов — [AGENTS.md](AGENTS.md), процесс задачи — [docs/PIPELINE.md](docs/PIPELINE.md), задачи — [docs/BACKLOG.md](docs/BACKLOG.md).
