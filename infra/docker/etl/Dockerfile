# syntax=docker/dockerfile:1
# Contexto de build: raiz do repositório (veja docker-compose.yml).
ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.11

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ---- build: resolve dependências do grupo "etl" a partir do uv.lock ------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --only-group etl

# ---- runtime -------------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
LABEL org.opencontainers.image.title="gntech/pyweather-etl"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY services/etl/pyweather_etl ./pyweather_etl
USER app

HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD ["python", "-m", "pyweather_etl", "healthcheck"]

ENTRYPOINT ["python", "-m", "pyweather_etl"]
CMD ["serve"]
