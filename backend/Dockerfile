FROM python:3.12-slim
WORKDIR /app
COPY scripts/__init__.py scripts/download_embedder.py scripts/
COPY apps/services/llm/embedder.json apps/services/llm/
RUN python -m scripts.download_embedder
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv PATH="/app/.venv/bin:$PATH"
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY main.py alembic.ini ./
COPY apps apps
COPY shared shared
COPY scripts scripts
COPY data/seed data/seed
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
