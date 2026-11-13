ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

LABEL org.opencontainers.image.title="gntech/pyweather-mock-openweather" \
      org.opencontainers.image.description="Mock determinístico da OpenWeather para smoke tests"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY infra/docker/mock-openweather/server.py .
USER app

EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=2s --retries=10 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2)"]

CMD ["python", "server.py"]
