# syntax=docker/dockerfile:1
# Contexto de build: raiz do repositório (veja docker-compose.yml).
ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.11

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ---- build: resolve dependências do grupo "api" a partir do uv.lock ------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --only-group api

# ---- runtime -------------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
LABEL org.opencontainers.image.title="gntech/pyweather-api"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY services/api/pyweather_api ./pyweather_api
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uvicorn", "pyweather_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
