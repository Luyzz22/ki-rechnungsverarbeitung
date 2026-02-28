# ============================================================================
# SBS Nexus Finance – Production Dockerfile
# ============================================================================

FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim AS production
RUN groupadd -r sbs && useradd -r -g sbs -d /app -s /sbin/nologin sbs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 libjpeg62-turbo libpng16-16 curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
WORKDIR /app
COPY . .
RUN rm -f config.yaml .env cookies.txt && \
    rm -rf _archive _archive_20260217_194225 _old_code backup_* web/_archive
RUN mkdir -p /app/exports /app/evidence /app/uploads /app/logs && \
    chown -R sbs:sbs /app
USER sbs
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-8000}/api/v1/health || exit 1
EXPOSE ${APP_PORT:-8000}
CMD ["python", "-m", "uvicorn", "modules.rechnungsverarbeitung.src.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--log-level", "info", "--access-log"]
