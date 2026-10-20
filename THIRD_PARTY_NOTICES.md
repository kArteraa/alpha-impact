# THIRD_PARTY_NOTICES

Сторонние компоненты, модели и смоделированные интеграции проекта Alpha Impact. Точные версии — в `uv.lock` и `package-lock.json`. Новая зависимость = строка здесь (см. «Definition of done» в `AGENTS.md`).

## Бэкенд (Python, `backend/pyproject.toml`)

| Пакет | Лицензия | Назначение |
|---|---|---|
| fastapi | MIT | HTTP-вход gateway |
| uvicorn[standard] | BSD-3-Clause | ASGI-сервер |
| pydantic | MIT | схемы контрактов, JSON Schema |
| pydantic-settings | MIT | настройки из окружения |
| SQLAlchemy[asyncio] | MIT | доступ к PostgreSQL |
| asyncpg | Apache-2.0 | драйвер PostgreSQL |
| alembic | MIT | миграции |
| pgvector (python) | MIT | тип vector для SQLAlchemy |
| httpx | BSD-3-Clause | HTTP-клиент к LLM-шлюзу и тестовый клиент |
| PyYAML | MIT | каталог продуктов и шаблоны планов |
| python-multipart | Apache-2.0 | формы в FastAPI |
| onnxruntime | MIT | локальный запуск модели эмбеддингов (CPU) |
| tokenizers | Apache-2.0 | токенизатор модели эмбеддингов |
| numpy | BSD-3-Clause | входы модели и нормировка векторов |

Dev: pytest (MIT), pytest-asyncio (Apache-2.0), pytest-cov (MIT), ruff (MIT), mypy (MIT), import-linter (BSD-2-Clause), types-PyYAML (Apache-2.0).

## Фронт (npm workspaces, `frontend/package.json`)

| Пакет | Лицензия | Назначение |
|---|---|---|
| react, react-dom | MIT | UI |
| react-router | MIT | маршрутизация макета Альфа-Бизнеса |
| vite, @vitejs/plugin-react | MIT | сборка приложения, библиотеки и расширения |
| typescript | Apache-2.0 | типы |
| vitest, happy-dom, @testing-library/react | MIT | тесты рендера |
| @playwright/test | Apache-2.0 | e2e |
| json-schema-to-typescript | MIT | типы фронта из `shared/contracts/openapi` |
| oxlint | MIT | линтер из шаблона create-vite |
| @types/react, @types/react-dom, @types/node | MIT | типы |

## Инфраструктура

| Компонент | Лицензия | Назначение |
|---|---|---|
| PostgreSQL 16 | PostgreSQL License | хранилище |
| pgvector (расширение, образ `pgvector/pgvector:pg16`) | PostgreSQL License | индекс новостей |
| uv (образ `ghcr.io/astral-sh/uv`) | MIT / Apache-2.0 | установка зависимостей в Docker |
| Docker Compose | Apache-2.0 | запуск одной командой |
| tesseract (rus+eng) | Apache-2.0 | OCR отчётов банка (задача AH-9) |

## Модели (генерация — только из allow-list кейса, эмбеддинги — локальная e5 по исключению из `AGENTS.md`; всё через `apps/services/llm`)

| Модель | Лицензия по карточке модели | Задача |
|---|---|---|
| Gemma 4 26B A4B | Gemma Terms of Use | разметка новостей и текста страниц |
| GLM-5.3-Flash | MIT | план и черновик карточки, критик |
| Qwen3.6 35B A3B | Apache-2.0 | извлечение утверждений из отчётов, уточняющий вопрос |
| DeepSeek-V4.1-Flash | MIT | резерв |
| Qwen3-VL-30B-A3B | Apache-2.0 | резерв (сканы) |
| Kimi-K2.6 | Modified MIT | резерв |
| multilingual-e5-small (`intfloat`, ONNX) | MIT | эмбеддинги: дубли и индекс новостей; локально, скачивается при сборке образа |

Доступ к моделям — через единый API-ключ кейса; условия использования — по правилам хакатона.

## Смоделированные интеграции (прототип, не боевые системы банка)

- Сессия интернет-банка: `POST /auth/mock` с cookie-сессией вместо реальной аутентификации Альфа-Бизнеса.
- Формы операций (платёж, депозит, кредит): макет в `frontend/application`, данные не уходят в банковские системы.
- Данные компаний, платежей и связей: синтетические csv кейса (Приложение 1), не коммитятся (`data/raw/`).
- Аналитика банка: материалы Приложения 2, обрабатываются OCR локально.
- RSS деловых СМИ: только для индекса новостей; тексты не перепубликуются, хранится ссылка на источник.
