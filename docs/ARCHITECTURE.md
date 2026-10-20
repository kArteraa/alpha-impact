# ARCHITECTURE

Монолит на Python с изолированными сервисами внутри: один процесс, один `main.py`, один DI-контейнер, но каждый сервис живёт в своём пакете, знает только свои таблицы и общается с остальными исключительно через контракты из `shared/contracts`.

## Дерево репозитория

```
alfa-insight/
  backend/                     Python-монолит; uv, pytest, alembic запускаются из этой папки
    main.py                    composition root (FastAPI app factory + DI wiring)
    pyproject.toml  uv.lock    зависимости бэкенда
    alembic.ini  Dockerfile
    apps/services/
      gateway/                 HTTP-вход: POST /interpret, /profile, /feedback, /trace/{id}; auth из мок-сессии, права user→client, лимиты, кэш, журнал
      profile/                 профилировщик: пакетная сборка паспорта клиента, группа, правки пользователя; порт ProfileService
      counterparty/            агрегаты по графу платежей; порт CounterpartyService
      news/                    RSS-парсер, дедупликация, разметка факторов, индекс (pgvector); порты NewsService и PageContextService
      house_view/              OCR отчётов, извлечение утверждений, версии/supersede; порт HouseViewService
      interpreter/             агент (план, вызовы инструментов, черновик), критик; порт Interpreter
      whatif/                  арифметика: нагрузка по ставке, сравнение сроков депозита, курс; порт WhatIfService
      products/                каталог правил «ситуация → продукт» (YAML); порт ProductRulesService
      llm/                     LLM-шлюз: маршрутизация по разрешённым моделям, кэш, счётчик токенов; порт LLMGateway
      trace/                   трасса, метрики, обратная связь; порт TraceStore
    shared/
      contracts/
        schemas.py             Pydantic: ActionContext (discriminated union), InsightCard, Claim, Trace, ClientProfile, CounterpartyContext, NewsItem, HouseViewClaim, WhatIfResult, ProductOffer, InterpretRequest/Response
        ports.py               typing.Protocol для каждого сервиса
        errors.py              доменные исключения
        openapi/               экспорт схем в JSON Schema для фронта (генерируется, коммитится)
      db/
        engine.py session.py   SQLAlchemy 2 async
        models/                таблицы по сервисам (profiles, counterparties, news, house_view, traces, feedback, users)
        migrations/            Alembic
      di/
        container.py           Container: register(port, factory) / resolve(port); scope per request
        wiring.py              порядок регистрации сервисов
      config/
        settings.py            pydantic-settings: DB_URL, LLM_API_BASE, LLM_API_KEY, LLM_DAILY_BUDGET_RUB, MODEL_* , FEATURE_*
    scripts/                   gen_schemas.py, seed.py
    data/
      raw/                     три csv (не коммитятся, .gitignore) + PDF/DOCX отчётов
      seed/                    тестовые пользователи, контрагенты, остатки, портфели (коммитятся)
    tests/
      unit/                    по сервисам + test_import_boundaries.py
      integration/             контрактные тесты, БД, gateway
  frontend/                    npm workspace; npm запускается из этой папки
    package.json  Dockerfile  playwright.config.ts
    application/               React + Vite: макет Альфа-Бизнеса (главный, платёж, депозит, кредит, профиль, трасса)
    app-plugin/                React + Vite: библиотека InsightPanel + сборка расширения MV3 (content script, service worker, side panel, popup)
    tests/e2e/                 Playwright: сквозной сценарий демо
  docker-compose.yml           api, db (postgres+pgvector), front, seed
  .env.example
  THIRD_PARTY_NOTICES.md
  README.md
  docs/
    CONCEPT.md ARCHITECTURE.md CONTRACTS.md PIPELINE.md TEAM.md ECC-SETUP.md DEMO.md BOOTSTRAP-PROMPT.md
    tasks/BACKLOG.md (единый) + CLAUDE-TASKS.md GEMINI-TASKS.md CODEX-TASKS.md (как запускать в своём агенте)
  CLAUDE.md  AGENTS.md  GEMINI.md   одни и те же правила для Claude Code, Codex, Gemini CLI (менять вместе)
  .claude/
    memory/MEMORY.md
    rules/ecc/                 скопированные rules/common + rules/python + rules/typescript из ECC
    skills/task/SKILL.md       точка входа /task для Claude Code
    settings.json              hooks profile, allowed tools
  .agents/skills/task/SKILL.md  точка входа $task для Codex (копия в .codex/skills/task/)
  .gemini/commands/task.toml    точка входа /task для Gemini CLI
  .github/workflows/           backend.yml (ruff, mypy, import-linter, pytest), frontend.yml (gen:types, vitest, npm run build)
```

Пути `apps/…`, `shared/…`, `scripts/…`, `data/…`, `tests/unit`, `tests/integration` в документах и бэклоге указаны относительно `backend/`; `application/`, `app-plugin/`, `tests/e2e` — относительно `frontend/`.

## Правила изоляции

1. Сервис импортирует только себя, `shared.contracts`, `shared.config`, `shared.db` (свои репозитории). Другие сервисы — никогда.
2. Зависимость между сервисами выражается портом из `shared/contracts/ports.py` и разрешается из DI-контейнера в `main.py`. Пример: `interpreter` получает `ProfileService`, `CounterpartyService`, `NewsService`, `HouseViewService`, `WhatIfService`, `ProductRulesService`, `LLMGateway`, `TraceStore` в конструктор.
3. Каждый сервис экспортирует только `register(container: Container) -> None`.
4. Таблицы принадлежат сервису; чужие таблицы читаются только через порт владельца.
5. Проверка — `tests/unit/test_import_boundaries.py` на `import-linter` (contracts: `forbidden` между `apps.services.*`).

## Поток запроса

```
контейнер (application / extension) → POST /interpret {user_id, client_id, role, action_context}
gateway: auth → права → нормализация → ключ кэша (client, role, type, hash(context), house_view_version) → попадание? ответ
interpreter.interpret():
  1 prefilter (без LLM): кандидаты-новости по отрасли/региону контрагента или факторам клиента, утверждения house view по теме; пусто → silent
  2 plan: шаблон по типу действия + дополнение моделью; план в трассу
  3 tools: вызовы портов, единый объект контекста
  4 draft: InsightCard по шести блокам, каждый тезис {text, type, source_ref}
  5 critic: источники / bank-тезисы из house view / противоречия / «не пересказ»; до 2 кругов
  6 trace.save(); gateway кэширует; ответ
```

## Пакетный контур

`scripts.seed` запускает по порядку: загрузка csv → чистка → профили и агрегаты графа → OCR отчётов → извлечение утверждений (черновики в статусе `draft`, подтверждение в `data/seed/house_view_approved.json`) → парсинг RSS и разметка. Повторный запуск идемпотентен.

## Фронтенд

- `frontend/application` — страницы: `/` (виджет), `/payments/new`, `/deposits/new`, `/loans`, `/profile`, `/trace/:id`. Использует `@alfa-insight/plugin` из `frontend/app-plugin` как workspace-зависимость.
- `frontend/app-plugin` — экспортирует `InsightPanel`, `useInterpret(actionContext)`, типы из `shared/contracts/openapi`; второй entry собирает расширение (`manifest.json`, `content.ts`, `background.ts`, `sidepanel.tsx`, `popup.tsx`).
- Типы фронта генерируются из JSON Schema (`npm run gen:types`), руками не пишутся.

## Модели и бюджет

| Задача | Модель |
|---|---|
| Разметка новостей и текста страниц | Gemma 4 26B A4B |
| Извлечение утверждений из отчётов | Qwen3.6 35B A3B |
| План и черновик карточки | GLM-5.3-Flash (запасной Qwen3.6) |
| Критик | GLM-5.3-Flash, другой промпт |
| Уточняющий вопрос | Qwen3.6 35B A3B |

`LLM_DAILY_BUDGET_RUB` делится: 60% онлайн, 30% пакетная разметка, 10% резерв. При исчерпании — ответ из кэша или `needs_review`.

## Безопасность

- Инструменты проверяют права; `counterparty_context` отдаёт только агрегаты (тест `tests/integration/test_counterparty_no_leak.py`).
- В промпты — признаки и агрегаты; персональные данные физлиц в модель не попадают.
- Журнал вызовов: `user_id`, `client_id`, `trace_id`, модель, токены, время.
- Расширение: токен со скоупом `interpret:read`, короткий TTL; на сервер уходит текст страницы и ИНН, журнал хранит хэш текста.
- Текст страницы — недоверенные данные: инструкции внутри игнорируются, критик требует источники из базы.
