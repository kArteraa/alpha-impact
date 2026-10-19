# BOOTSTRAP-PROMPT — промпт для Claude Code: скелет проекта, Jira, ветки, контракты

Перед запуском: в пустой папке лежат `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `docs/` (CONCEPT, ARCHITECTURE, CONTRACTS, PIPELINE, TEAM, ECC-SETUP, DEMO, tasks/), `.claude/`, `.agents/`, `.gemini/` из этого набора; настроены `gh auth login` на GitHub-аккаунт с правом создавать репозитории в нужной организации и MCP-сервер Atlassian (Jira) с правами на проект `AH`; установлен ECC по `docs/ECC-SETUP.md`. Замените `<org>`, `<repo>`, `<jira-site>` и имена участников.

Скопируйте текст ниже в Claude Code одним сообщением.

---

Ты бутстрапишь репозиторий проекта **alfa-insight** для хакатона Альфа-Банка. Прочитай целиком `CLAUDE.md`, `docs/CONCEPT.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/PIPELINE.md`, `docs/TEAM.md`, `docs/ECC-SETUP.md` и `docs/tasks/BACKLOG.md`. Они — источник истины; ничего из них не переписывай, кроме случаев, которые явно названы ниже.

Работай строго по пайплайну из `CLAUDE.md`: сначала `/ecc:plan` в plan mode по шагам A–I ниже, остановись и дождись моего подтверждения, затем выполняй шаги по одному, после каждого — проверка и коммит. Коммиты — естественный язык, списком, без префиксов и без Co-Authored-By. Если какой-то инструмент недоступен (gh, MCP Jira, docker) — остановись и скажи, что именно, не обходи.

Что НЕ делать: не писать бизнес-логику сервисов (только заглушки, удовлетворяющие портам), не вызывать LLM, не добавлять зависимости сверх списка в шаге B, не придумывать контракты сверх `docs/CONTRACTS.md`, не менять структуру из `docs/ARCHITECTURE.md`, не создавать дефолты и фолбэки без вопроса.

## A. Репозиторий и защищённые ветки

1. `git init`, первый коммит на `main`: `README.md` (название, одна строка назначения, ссылка на `docs/CONCEPT.md`), `.gitignore` (Python, Node, `.env`, `data/raw/`), `LICENSE` (MIT), файлы из этого набора как есть.
2. `gh repo create <org>/<repo> --private --source . --push`.
3. Создать `dev` от `main`, запушить.
4. Защитить обе ветки через `gh api` (`PUT repos/<org>/<repo>/branches/<branch>/protection`):
   - `main`: PR обязателен, 1 approving review, required status check `ci`, `enforce_admins: false`, `allow_force_pushes: false`, `allow_deletions: false`, `required_linear_history: true`.
   - `dev`: PR обязателен, 0 approving reviews, required status check `ci`, `allow_force_pushes: false`, `allow_deletions: false`.
   Покажи мне итоговый JSON защиты обеих веток и остановись, если API вернул ошибку.
5. Дальше вся работа — в ветке `chore/AH-2-bootstrap` от `dev`.

## B. Скелет и инструменты (задача AH-2)

Дерево — ровно как в `docs/ARCHITECTURE.md`. Python 3.12, менеджер зависимостей `uv` (`pyproject.toml` + `uv.lock`).

Зависимости бэкенда (и только они): `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy[asyncio]>=2`, `asyncpg`, `alembic`, `pgvector`, `httpx`, `pyyaml`, `python-multipart`. Dev: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `import-linter`, `httpx` (тестовый клиент), `testcontainers[postgres]` или compose-профиль `test` — выбери одно и обоснуй в плане.

Настройки: `ruff` (line-length 100, правила E,F,I,UP,B), `mypy --strict` для `shared/`, обычный для `apps/`; `pytest` с `asyncio_mode = auto`; `import-linter` контракт `forbidden` между всеми `apps.services.*` и контракт `layers`: `apps.services` → `shared`.

`Makefile`: `up` (docker compose up -d --build), `down`, `seed` (python -m scripts.seed), `check` (lint + typecheck + test + front:test + front:build), `test`, `lint`, `e2e` (playwright против compose), `gen:schemas`.

`docker-compose.yml`: `db` (postgres:16 + pgvector, healthcheck), `api` (Dockerfile, `uvicorn main:app`, зависит от db healthy, `alembic upgrade head` при старте), `front` (vite preview application), `seed` (профиль `seed`). `.env.example` со всеми переменными из `shared/config/settings.py`.

Фронт: `npm` workspace в корне (`package.json (workspaces)` с `apps/front/*`), `apps/front/application` и `apps/front/app-plugin` — `npm create vite@latest` (react-ts), в `app-plugin` два entry (library + extension) через vite config; `vitest` в обоих; `@playwright/test` в корне; скрипт `npm run gen:types` — `json-schema-to-typescript` из `shared/contracts/openapi/*.json` в `apps/front/app-plugin/src/types/`.

CI: `.github/workflows/ci.yml` с job `ci`: uv sync, ruff, mypy, import-linter, pytest (с postgres service), npm ci, vitest, npm run build. Имя job должно быть ровно `ci` — на него ссылается защита веток.

## C. Контракты (задача AH-3)

Реализуй `shared/contracts/schemas.py`, `ports.py`, `errors.py` дословно по `docs/CONTRACTS.md`. Порты — `typing.Protocol` с `@runtime_checkable`. Скрипт `scripts/gen_schemas.py` экспортирует JSON Schema каждой схемы в `shared/contracts/openapi/<Name>.json`; закоммить сгенерированные файлы и добавь тест, который падает, если они расходятся с кодом. Тесты: round-trip каждой схемы, дискриминация `ActionContext` по всем восьми типам, инварианты (`Claim` без `source_ref` невалиден).

## D. shared: config, db, di, main.py (задачи AH-4, AH-5, AH-6)

- `shared/config/settings.py`: `DB_URL`, `LLM_API_BASE`, `LLM_API_KEY`, `LLM_DAILY_BUDGET_RUB=500`, `MODEL_ANNOTATE`, `MODEL_EXTRACT`, `MODEL_INTERPRET`, `MODEL_CRITIC`, `MODEL_FOLLOWUP`, `RELEVANCE_THRESHOLD`, `CACHE_TTL_SECONDS`, `EXTENSION_TOKEN_TTL_SECONDS`, `NEWS_RSS_URLS`.
- `shared/db`: async engine, session factory, Alembic с первой миграцией: `CREATE EXTENSION IF NOT EXISTS vector`, таблицы `users`, `user_clients`, `traces`, `feedback`.
- `shared/di/container.py`: `Container.register(port, factory, scope="app"|"request")`, `resolve(port)`, `validate(required_ports)`; `wiring.py` вызывает `register(container)` каждого сервиса и затем `validate` по всем портам из `ports.py` — незарегистрированный порт валит старт с перечислением недостающих.
- `main.py`: `create_app() -> FastAPI`, `/health`, монтирование роутера gateway, DI через `app.state.container` и зависимость `get_container`.
- `tests/unit/test_import_boundaries.py` на import-linter.

## E. Сервисы-заглушки

Для каждого сервиса из `docs/ARCHITECTURE.md` (`gateway`, `profile`, `counterparty`, `news`, `house_view`, `interpreter`, `whatif`, `products`, `llm`, `trace`): пакет с `__init__.py` (`register(container)`), `service.py` с классом, реализующим свой порт (все методы — `raise NotImplementedError` с именем задачи из `docs/tasks`, которая его реализует), `tests/unit/<service>/test_contract.py` (`isinstance(impl, Port)` через runtime_checkable). `gateway` — исключение: реализуй `/health`, `POST /auth/mock` и `GET /clients` на таблицах `users`/`user_clients`, остальные роуты — 501 с именем задачи.

## F. Фронт-заглушки

`application`: роутинг по `docs/ARCHITECTURE.md`, страницы-пустышки с заголовками, API-клиент с cookie, экран входа, вызывающий `POST /auth/mock`. `app-plugin`: `InsightPanel` с тремя состояниями на моковых данных и типами из `npm run gen:types`; `application` подключает его как workspace-зависимость. Vitest smoke-тесты на рендер.

## G. .claude, память, ECC

- `.claude/memory/MEMORY.md` из набора — оставить, добавить запись `project` о выбранном варианте тестовой БД (шаг B).
- `.claude/settings.json` из набора.
- Скопировать `rules/common`, `rules/python`, `rules/typescript` из клона ECC в `.claude/rules/ecc/` (команды в `docs/ECC-SETUP.md`).
- Скопировать `.agents/skills/task/` в `.codex/skills/task/` (у Codex два места поиска скиллов); `.gemini/commands/task.toml` оставить как есть.
- `THIRD_PARTY_NOTICES.md`: все зависимости из шага B с лицензиями, tesseract, модели из allow-list, смоделированные интеграции (сессия интернет-банка, формы операций).

## H. Jira через MCP

Проект `AH` (Kanban) на `<jira-site>`. Через MCP-инструменты Atlassian:

1. Проверь, что проект пустой (ни одного issue). Если нет — остановись и спроси.
2. Создай в указанном порядке, чтобы ключи совпали с файлами: сначала эпик `AH-1`, затем задачи `AH-2…AH-11` по порядку номеров, затем эпик `AH-12`, задачи `AH-13…AH-20`, эпик `AH-21`, задачи `AH-22…AH-33`, эпик `AH-34`, задачи `AH-35…AH-42`, эпик `AH-43`, задачи `AH-44…AH-47`. Номера, которых нет в файлах (например AH-17), пропускать нельзя — создай для них задачу `AH-<n> · резерв` и сразу закрой её со статусом Done, чтобы нумерация не сдвинулась.
3. Для каждой задачи: summary = `AH-<n> · <название>` из `BACKLOG.md`; description = поля «Что сделать» и «Готово, когда» дословно; parent = эпик; assignee = участник из поля «Ответственный» (имена ниже); labels `p0`–`p3` по `docs/CONCEPT.md` (платёж, профиль, контракты, gateway, interpreter, критик, трасса, README — `p0`; депозит, кредит, виджет, house view, новости, регрессия — `p1`; расширение, живая новость, роли, followup — `p2`; остальное — `p3`); component = сервис или `front-application` / `front-plugin` / `shared` / `infra`; due date = день задачи, отсчитывая от даты старта `<дата старта>`; связи `blocks` по полю «Зависит от».
4. После создания выгрузи список `key | summary | assignee | labels | due | blockedBy` в `docs/tasks/JIRA-MAP.md` и сверь с `BACKLOG.md`: 47 issue, ключи совпадают. Если ключи не совпали — не удаляй ничего, запиши маппинг в `JIRA-MAP.md` и остановись.
5. Соответствие «Участник N → аккаунт Jira»: Участник 1 = `<аккаунт 1>`, Участник 2 = `<аккаунт 2>`, Участник 3 = `<аккаунт 3>`, Участник 4 = `<аккаунт 4>` (см. роли в `docs/TEAM.md`).

## I. Проверка и сдача шага

`make up` на чистом клоне поднимает api и db, `/health` отвечает; `make check` зелёный; `npm run build` в обоих фронт-пакетах зелёный; import-linter зелёный; JSON Schema совпадают с кодом; все тесты заглушек зелёные. Покажи вывод `make check`, список коммитов и дерево репозитория. Открой PR `chore/AH-2-bootstrap → dev` с описанием по шагам A–H и ссылкой на `AH-2`, переведи `AH-2` в Review. **Остановись перед push и спроси меня.**

---

## После бутстрапа — как стартует каждая задача

```
/task "Выполни задачу AH-7"        # Claude Code
$task Выполни задачу AH-7          # Codex
/task Выполни задачу AH-7          # Gemini CLI
```
Агент читает задачу в `docs/tasks/BACKLOG.md`, создаёт ветку `feat/AH-7-profiles` от свежего `dev`, пишет план и ждёт подтверждения. Дальше — пайплайн из `docs/PIPELINE.md`, одинаковый для всех трёх.
