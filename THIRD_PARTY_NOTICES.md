# THIRD_PARTY_NOTICES

Сторонние компоненты, модели и смоделированные интеграции проекта Alpha Impact. Точные версии — в `uv.lock` и `package-lock.json`. Новая зависимость = строка здесь.

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
| pypdf | BSD-3-Clause | страницы-картинки отчётов банка из PDF |
| Pillow | MIT-CMU | перекодирование страниц отчётов для OCR; сборка анимации README из кадров Playwright |
| Tesseract OCR (системный пакет `tesseract-ocr`, `tesseract-ocr-rus`) | Apache-2.0 | распознавание текста отчётов банка |

Dev: pytest (MIT), pytest-asyncio (Apache-2.0), pytest-cov (MIT), ruff (MIT), mypy (MIT), import-linter (BSD-2-Clause), types-PyYAML (Apache-2.0).

## Фронт (npm workspaces, `frontend/package.json`)

| Пакет | Лицензия | Назначение |
|---|---|---|
| react, react-dom | MIT | UI |
| react-router | MIT | маршрутизация макета Альфа-Бизнеса |
| vite, @vitejs/plugin-react | MIT | сборка приложения, библиотеки и расширения |
| typescript | Apache-2.0 | типы |
| @types/chrome | MIT | типы API расширений Chrome |
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
| образ `python:3.12-slim` (Python) | PSF-2.0 | основа образа бэкенда |
| образ `node:22-alpine` (Node.js) | MIT | основа образа фронта |
| GitHub Actions: `actions/checkout`, `actions/setup-node`, `actions/cache`, `astral-sh/setup-uv` | MIT | CI |

## Модели (генерация — только из allow-list кейса, эмбеддинги — локальная e5: у ключа кейса нет модели эмбеддингов; всё через `apps/services/llm`)

| Модель | Лицензия по карточке модели | Задача |
|---|---|---|
| Gemma 4 26B A4B | Gemma Terms of Use | разметка новостей и текста страниц |
| GLM-5.3-Flash | MIT | критик карточки |
| Qwen3.6 35B A3B | Apache-2.0 | извлечение утверждений банка из страниц отчётов |
| DeepSeek-V4.1-Flash | MIT | план и черновик карточки, уточняющий вопрос |
| Qwen3-VL-30B-A3B | Apache-2.0 | резерв (сканы) |
| Kimi-K2.6 | Modified MIT | резерв |
| multilingual-e5-small (`intfloat`, ONNX) | MIT | эмбеддинги: дубли и индекс новостей; локально, скачивается при сборке образа |

Доступ к моделям — через прокси моделей кейса (`LLM_API_BASE`) по единому API-ключу кейса; условия использования — по правилам хакатона. Лицензии моделей указаны по их карточкам на момент выбора; перед публикацией их стоит сверить с карточками ещё раз.

## Смоделированные интеграции (прототип, не боевые системы банка)

- Сессия интернет-банка: `POST /auth/mock` с cookie-сессией вместо реальной аутентификации Альфа-Бизнеса.
- Формы операций (платёж, депозит, кредит): макет в `frontend/application`, данные не уходят в банковские системы.
- Данные компаний, платежей и связей: синтетические csv кейса (Приложение 1), не коммитятся (`data/raw/`).
- Аналитика банка: материалы Приложения 2, обрабатываются OCR локально.

## Внешние источники и сервисы (настоящие, не смоделированные)

- Прокси моделей кейса (`LLM_API_BASE`): получает все промпты — признаки и агрегаты компании, тексты новостей и вставленных страниц, страницы отчётов банка для извлечения утверждений; идентификаторы клиентов и данные физлиц из `df_Fid_Uid_link` в промпты не попадают.
- RSS деловых СМИ — ленты Коммерсанта, Ведомостей и Интерфакса; точный список — `NEWS_RSS_URLS` в `.env.example`. Только для индекса новостей: тексты не перепубликуются, в карточке — ссылка на источник.
- Страницы сайтов в расширении — деловые СМИ, сервисы проверки контрагентов, площадки закупок и курсы валют из `PAGE_DOMAINS` (`frontend/app-plugin/extension/config.ts`). После входа в расширение текст распознанной страницы уходит в API Alpha Impact, оттуда — в модели через прокси кейса, и сохраняется в индексе новостей как вставленная новость (`manual`). Автопоказ управляет только плашкой на странице; открытая боковая панель разбирает каждую распознанную вкладку. Страница сервиса проверки, где первый ИНН — 12-значный (человек или ИП), не распознаётся; 12-значные ИНН, записанные подряд, в тексте заменяются на «ИНН скрыт». ФИО руководителей и учредителей на странице компании остаются в тексте.
