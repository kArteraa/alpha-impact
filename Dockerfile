FROM python:3.12-slim AS api
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY main.py alembic.ini ./
COPY apps/__init__.py apps/__init__.py
COPY apps/services apps/services
COPY shared shared
COPY scripts scripts
COPY data/seed data/seed
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM node:22-alpine AS front
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/front/application/package.json apps/front/application/
COPY apps/front/app-plugin/package.json apps/front/app-plugin/
RUN npm ci
COPY shared/contracts/openapi shared/contracts/openapi
COPY apps/front apps/front
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview", "--workspace", "apps/front/application", "--", "--host", "0.0.0.0", "--port", "5173"]
