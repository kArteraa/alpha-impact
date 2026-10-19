.PHONY: up down seed check test lint typecheck e2e gen\:schemas front\:test front\:build

.env:
	cp .env.example .env

up: .env
	docker compose up -d --build

down:
	docker compose down

seed: .env
	uv run --env-file .env python -m scripts.seed

check: lint typecheck test front\:test front\:build

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy --strict shared
	uv run mypy apps main.py scripts tests
	uv run lint-imports

test: .env
	docker compose --profile test up -d --wait db_test
	uv run --env-file .env pytest

e2e: .env
	docker compose up -d --build --wait
	npx playwright test

gen\:schemas:
	uv run python -m scripts.gen_schemas
	npm run gen:types

front\:test:
	npm test

front\:build:
	npm run build
