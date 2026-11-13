FROM postgres:18-alpine

LABEL org.opencontainers.image.title="gntech/pyweather-database" \
      org.opencontainers.image.description="PostgreSQL do projeto pyweather"

# Scripts executados apenas na primeira inicialização do volume de dados.
COPY infra/docker/database/init/ /docker-entrypoint-initdb.d/

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" || exit 1
