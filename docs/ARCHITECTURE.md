# ARCHITECTURE

Монолит на Python с изолированными сервисами внутри: один процесс, один `main.py`, один DI-контейнер, но каждый сервис живёт в своём пакете, знает только свои таблицы и общается с остальными исключительно через контракты из `shared/contracts`.

## Дерево репозитория

```
alpha-impact/
  backend/                     Python-монолит; uv, pytest, alembic запускаются из этой папки
    main.py                    composition root: FastAPI, DI-контейнер, сервисы из apps/services находятся сами
    pyproject.toml  uv.lock    зависимости бэкенда
    alembic.ini  Dockerfile
    apps/services/
      gateway/                 HTTP-вход: POST /interpret, /profile, /feedback, /trace/{id}; auth из мок-сессии, права user→client, лимиты, кэш, журнал
      profile/                 профилировщик: пакетная сборка паспорта клиента, группа, правки пользователя; порт ProfileService
      counterparty/            агрегаты по графу платежей; порт CounterpartyService
      news/                    RSS-парсер, дедупликация, разметка факторов, индекс (pgvector, vector(EMBEDDING_DIMENSION)); entities — ключи industry:/region:/country:/company: в нижнем регистре, регион — в написании `REGION` из csv, страна — код alpha-2 (`country:cn`) по справочнику `shared/config/geography.py`; порты NewsService и PageContextService
      house_view/              OCR отчётов, извлечение утверждений, версии/supersede; порт HouseViewService
      interpreter/             агент (план, вызовы инструментов, черновик), критик; порт Interpreter
      whatif/                  арифметика: нагрузка по ставке, сравнение сроков депозита, курс; порт WhatIfService
      products/                каталог правил «ситуация → продукт» (YAML); порт ProductRulesService
      llm/                     LLM-шлюз: маршрутизация по разрешённым моделям, кэш, счётчик токенов, локальные эмбеддинги multilingual-e5-small (ONNX, embedder.json); порт LLMGateway
      trace/                   трасса, метрики, обратная связь; порт TraceStore
    shared/
      contracts/
        schemas.py             Pydantic: ActionContext (discriminated union), InsightCard, Claim, Trace, ClientProfile, CounterpartyContext, NewsItem, HouseViewClaim, WhatIfResult, ProductOffer, InterpretRequest/Response
        ports.py               typing.Protocol для каждого сервиса
        errors.py              доменные исключения
        openapi/               экспорт схем в JSON Schema для фронта (генерируется, коммитится)
      db/
        engine.py session.py   SQLAlchemy 2 async
        models/                таблицы по сервисам (profiles, profile_corrections, counterparty_cards, client_graphs, news, report_pages, house_view_claims, traces, feedback, users, llm_cache, llm_usage)
        migrations/            Alembic
      di/
        container.py           Container: register(port, factory) / resolve(port); scope per request; on_close / aclose — закрытие ресурсов при остановке
      config/
        settings.py            pydantic-settings: DB_URL, LLM_API_BASE, LLM_API_KEY, LLM_DAILY_BUDGET_RUB, LLM_BUDGET_RESERVE_SHARE, LLM_TIMEOUT_SECONDS, LLM_CALL_RESERVE_RUB, LLM_CACHE_TTL_SECONDS, MODEL_*, RELEVANCE_THRESHOLD, CACHE_TTL_SECONDS, EXTENSION_TOKEN_TTL_SECONDS, NEWS_RSS_URLS
        industries.py          справочник отраслей: ОКВЭД → отраслевой класс по industries.yaml, общий для profile и counterparty
        clients.py             какие клиенты обслуживаются: файл компаний и порог выручки крупного клиента (clients.yaml), общий для profile и counterparty
        geography.py           справочник для разметки новостей: субъекты РФ — написание REGION из csv и названия, из которых выбирает модель: привычное и у республик официальное (regions.yaml; 8 субъектов, которых нет в csv, — в своём написании) и страны с кодом alpha-2, названием по-русски и по-английски и написанием FTS_COUNTRY_NAME (countries.yaml); name_key — ключ без регистра и лишних пробелов, ё → е
        embedding.py           EMBEDDING_DIMENSION (384) — длина вектора e5: её сверяет llm, её берёт колонка pgvector новостей
    scripts/                   gen_schemas.py, seed.py, ingest_reports.py, ingest_news.py, reannotate_news.py, download_embedder.py (модель эмбеддингов в models/, только стандартная библиотека)
    models/                    скачанная модель эмбеддингов (не коммитится, .gitignore)
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
  docker-compose.yml           db, db_test (профиль test), api, front, seed (профиль seed); запуск — docker compose up -d --build
  .env.example
  THIRD_PARTY_NOTICES.md
  README.md
  docs/
    CONCEPT.md ARCHITECTURE.md CONTRACTS.md DEMO.md   продукт, устройство, контракты, демо
    PIPELINE.md                процесс задачи для любого агента
    BACKLOG.md TEAM.md         задачи AH-1…AH-53; кто и в каком порядке их делает
    DECISIONS.md DATA.md       правила и оглавление журнала решений; факты о данных
    decisions/                 журнал решений: по файлу на участника
    design/                    дизайн: токены, принципы, скриншоты экранов и панели
    SUMMARY.md                 суть, цели и текущее состояние на одной странице
  AGENTS.md                    правила для всех агентов — единственный источник
  CLAUDE.md  GEMINI.md         только импорт AGENTS.md
  .claude/skills/{task,setup}/  /task и /setup в Claude Code → docs/PIPELINE.md
  .claude/settings.json        разрешённые команды для Claude Code
  .agents/skills/{task,setup}/  $task и $setup в Codex → docs/PIPELINE.md
  .gemini/commands/             /task и /setup в Gemini CLI → docs/PIPELINE.md
  .github/workflows/           backend.yml (ruff, mypy, import-linter, модель эмбеддингов из кэша, pytest), frontend.yml (gen:types, vitest, npm run build)
```

Пути `apps/…`, `shared/…`, `scripts/…`, `data/…`, `tests/unit`, `tests/integration` в документах и бэклоге указаны относительно `backend/`; `application/`, `app-plugin/`, `tests/e2e` — относительно `frontend/`.

## Правила изоляции

Сами правила — в `AGENTS.md`, раздел «Service isolation»; здесь — как они устроены.

- Зависимость между сервисами выражается портом из `shared/contracts/ports.py` и разрешается из DI-контейнера. Пример: `interpreter` получает `ProfileService`, `CounterpartyService`, `NewsService`, `HouseViewService`, `WhatIfService`, `ProductRulesService`, `LLMGateway`, `TraceStore` в конструктор.
- Сервис экспортирует только `register(container: Container) -> None`. Сервис — пакет в `apps/services/`: `main.py` находит его сам и вызывает `register` с контейнером, где уже есть `Settings`, `AsyncEngine` и `async_sessionmaker`; общие файлы при добавлении сервиса не правятся.
- Проверка — `tests/unit/test_import_boundaries.py` запускает `import-linter` с контрактами из `backend/pyproject.toml`: `independence` между `apps.services.*`, `forbidden` на `shared.db.migrations`, `layers` — `shared` не зависит от сервисов.

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

`scripts.seed` запускает по порядку: пользователи → загрузка csv → чистка → профили и агрегаты графа; ключ LLM ему не нужен. Новости собирает отдельная команда `scripts.ingest_news` (`docker compose --profile seed run --build --rm -e LLM_TIMEOUT_SECONDS=30 seed python -m scripts.ingest_news` — при 8 с часть ответов прокси не успевает, а таймаут оставляет в `llm_usage` резерв), ей нужен ключ LLM: ленты из `NEWS_RSS_URLS` → новости за `max_age_days` → отсев уже известных (хэш заголовка, адрес) → эмбеддинг e5 → дубль, если у одной из `dedup_candidates` ближайших новостей за ±`dedup_window_hours` косинус ≥ `dedup_threshold` и те же числа и месяцы (повторы числа не считаются) → разметка Gemma: регион и код страны — только из справочника `shared/config/geography.py`, Россия — не регион и не страна → `news` (`apps/services/news/config.yaml`). Недоступная лента и ошибка модели или эмбеддинга на новости не останавливают прогон, исчерпанный бюджет останавливает; повторный запуск размечает только новые новости. После смены промпта или справочника индекс переразмечает `scripts.reannotate_news` (`docker compose --profile seed run --build --rm --no-deps -e LLM_TIMEOUT_SECONDS=30 seed python -m scripts.reannotate_news`): заново размечает каждую новость и обновляет `entities` и `factors`, ошибка на новости оставляет старую разметку. `NewsService.search` берёт новости с `since` по пересечению факторов или по отрасли, региону и стране (регион и страна — по справочнику из любого их написания: «Татарстан» и «Республика Татарстан», «ОАЭ» и «ae»; места вне справочника нет и в индексе) и ранжирует по сумме силы совпавших факторов плюс число совпавших полей; `annotate` размечает вставленный текст без записи в индекс (запись — AH-40). OCR отчётов банка и извлечение утверждений — отдельная команда `scripts.ingest_reports` (`docker compose --profile seed run --rm -e LLM_TIMEOUT_SECONDS=120 seed python -m scripts.ingest_reports` — пакетному извлечению нужен таймаут больше интерактивного): ей нужны tesseract (есть в образе backend) и ключ LLM; страницы распознаются один раз (кэш по хэшу картинки в `report_pages`), утверждения пишутся черновиками `draft` в `house_view_claims` (отчёт по стали — `expired`), подтверждение — в `data/seed/house_view_approved.json` (AH-14). Повторный запуск идемпотентен.

## Фронтенд

- `frontend/application` — страницы: `/` (персональная лента: виджет и полный список событий), `/payments/new`, `/deposits/new`, `/loans`, `/profile`, `/trace/:id`. Использует `@alpha-impact/plugin` из `frontend/app-plugin` как workspace-зависимость.
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
| Эмбеддинги: дубли и индекс новостей | multilingual-e5-small локально (ONNX, префикс `query: `), не тратит бюджет |

Для `extract` и `followup` шлюз отключает рассуждения через `reasoning_off_tasks` в `apps/services/llm/models.yaml`: запрос содержит `reasoning: {enabled: false}`, этот режим входит в ключ кэша. `followup` остаётся на Qwen3.6 с общим интерактивным таймаутом `LLM_TIMEOUT_SECONDS=8`; рассуждения остальных задач не отключаются (AH-56).

Онлайн- и пакетные вызовы тратят общий дневной пул `LLM_DAILY_BUDGET_RUB × (1 − LLM_BUDGET_RESERVE_SHARE)`; 10% — резерв, не тратится; деление на онлайн и пакет пока не делается. Перед вызовом модели шлюз под advisory-блокировкой Postgres проверяет остаток и резервирует `LLM_CALL_RESERVE_RUB` строкой в `llm_usage`, после ответа резерв заменяется фактическим расходом — стоимостью из ответа прокси (`usage.cost`, рубли; ею же прокси списывает лимит ключа) — или снимается; параллельные вызовы api и seed не проходят лимит вместе. `models.yaml` — только allow-list моделей, цен в нём нет: прокси их не публикует. Эмбеддинги считает локальная модель (`embedder.json`, файлы — в `backend/models`, скачиваются при сборке образа): без HTTP, без резерва и без строк в `llm_usage`. Кэш ответов и эмбеддингов живёт `LLM_CACHE_TTL_SECONDS`, просроченные записи удаляются при записи в кэш. При исчерпании шлюз поднимает `BudgetExceeded`, ответы из кэша отдаются и дальше, вызывающий отвечает `needs_review`. Ошибки шлюза — `BudgetExceeded`, `ModelUnavailable` (HTTP-ошибка, таймаут, обрыв соединения или битое тело ответа 200 — не JSON, нет `choices` / `usage`, `content` не строка, счётчик токенов не целое ≥ 0 или в `usage` нет `cost`; расход записывается по `usage.cost`, если он есть, при `usage` без корректного конечного `cost` и при таймауте (прокси мог списать вызов) в `llm_usage` остаётся резерв; для `embed` — нет файлов локальной модели), `ModelOutputInvalid` (пустой ответ или не по схеме), `UsageNotRecorded` (ответ получен и закэширован, но расход не записан — в `llm_usage` остаётся резерв), `CacheNotWritten` (ответ получен и расход записан фактом, но запись в кэш не удалась; для `embed` — вектор посчитан, но не закэширован) — подклассы `DomainError`. Длина вектора не равна `EMBEDDING_DIMENSION` — `EmbeddingDimensionMismatch` (`ValueError`, ошибка конфигурации, а не `DomainError`).

## Безопасность

- Инструменты проверяют права; `counterparty_context` отдаёт только агрегаты (тест `tests/integration/test_counterparty_no_leak.py`).
- В промпты — признаки и агрегаты; персональные данные физлиц в модель не попадают.
- Журнал вызовов: `user_id`, `client_id`, `trace_id`, модель, токены, время.
- Расширение: токен со скоупом `interpret:read`, короткий TTL; на сервер уходит текст страницы и ИНН, журнал хранит хэш текста.
- Текст страницы — недоверенные данные: инструкции внутри игнорируются, критик требует источники из базы.
