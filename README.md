# alfa-insight

Аналитика в момент действия: сервис внутри Альфа-Бизнеса, который в момент платежа, депозита или кредита объясняет, что изменилось в мире относительно именно этого действия, с пометкой «факт / позиция банка / вывод AI» на каждом тезисе.

Концепция, слои и демо-сценарий — в [docs/CONCEPT.md](docs/CONCEPT.md).

## Запуск

```
make up        # db (postgres + pgvector) и api; http://localhost:8000/health, фронт http://localhost:5173
make check     # ruff, mypy, import-linter, pytest (нужен Docker: тестовая БД — профиль test), vitest, npm run build
make seed      # тестовые пользователи из data/seed
```

Переменные окружения — `.env.example` (`make up` копирует его в `.env`, если файла нет). Структура и правила — `docs/ARCHITECTURE.md`, задачи — `docs/tasks/BACKLOG.md`.
