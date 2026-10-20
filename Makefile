.PHONY: up down seed check test lint typecheck e2e gen\:schemas front\:test front\:build

.env:
	cp .env.example .env

up: .env
	docker compose up -d --build

down:
	docker compose down

seed: .env
	cd backend && uv run --env-file ../.env python -m scripts.seed

check: lint typecheck test front\:test front\:build

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy --strict shared && uv run mypy apps main.py scripts tests && uv run lint-imports

test: .env
	docker compose --profile test up -d --wait db_test
	cd backend && uv run --env-file ../.env pytest

e2e: .env
	docker compose up -d --build --wait
	cd frontend && npx playwright test

gen\:schemas:
	cd backend && uv run python -m scripts.gen_schemas
	cd frontend && npm run gen:types

front\:test:
	cd frontend && npm test

front\:build:
	cd frontend && npm run build
