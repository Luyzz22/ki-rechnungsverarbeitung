#!/bin/bash
# ============================================================================
# SBS Nexus Finance – Phase 0 Deploy Script
# ============================================================================
# Copy-paste this entire script into your server terminal.
# Repo: /var/www/invoice-app
# ============================================================================

set -e
REPO="/var/www/invoice-app"
cd "$REPO"

echo "🚀 Phase 0: Foundation & Security – Deploying to $REPO"
echo "======================================================="

# ═══════════════════════════════════════════════════════════════
# 0.1 SECRETS: Clean config.yaml
# ═══════════════════════════════════════════════════════════════

echo "🔒 [0.1] Cleaning secrets from config.yaml..."

cat > config.yaml << 'CFGEOF'
version: "4.1"

ai:
  mode: "hybrid"
  primary_model: "gpt-4o"
  primary_provider: "openai"
  fallback_model: "claude-sonnet-4-20250514"
  fallback_provider: "anthropic"
  complexity_threshold: 0
  temperature: 0
  max_retries: 3
  timeout: 30

processing:
  parallel_processing: true
  max_workers: 4
  batch_size: 100
  chunk_size: 3500
  input_dir: test_rechnungen
  max_pdfs_per_run: 1000
  max_file_size_mb: 50

ocr:
  language: "deu"
  dpi: 300

paths:
  input_directory: "test_rechnungen"
  output_directory: "output"

export:
  formats:
    - xlsx
    - csv
  create_datev: true
  create_dashboard: true

datev:
  enabled: true

dashboard:
  output_dir: "output/charts"
  auto_generate: true
  theme: "dark"

notifications:
  email:
    enabled: true
    smtp_server: "${SMTP_SERVER:-smtp.gmail.com}"
    smtp_port: 587
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from_address: "${SMTP_FROM_ADDRESS}"
    to_addresses: "${NOTIFICATION_RECIPIENTS}"

validation:
  enabled: true
  required_fields:
    - rechnungsnummer
    - datum
    - betrag_brutto

logging:
  level: INFO

features:
  ocr_fallback: true
  datev_export: true
  dashboard: true
CFGEOF

cp config.yaml config.yaml.example
echo "  ✅ config.yaml cleaned + config.yaml.example created"

# ═══════════════════════════════════════════════════════════════
# .env.example
# ═══════════════════════════════════════════════════════════════

cat > .env.example << 'ENVEOF'
# ============================================================================
# SBS Nexus Finance – Environment Variables
# ============================================================================
# Copy to .env and fill in your values. NEVER commit .env.
# ============================================================================

# --- Database (PostgreSQL) ---
DATABASE_URL=postgresql+psycopg://sbs_user:CHANGE_ME@localhost:5432/sbs_nexus
POSTGRES_USER=sbs_user
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=sbs_nexus

# --- Application ---
APP_ENV=development
APP_SECRET_KEY=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32
APP_PORT=8000
APP_HOST=0.0.0.0
LOG_LEVEL=INFO

# --- AI / LLM ---
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# --- Email / SMTP ---
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=
NOTIFICATION_RECIPIENTS=luis@schenk.com,andreas@schenk.com

# --- DATEV ---
DATEV_EXPORT_DIR=./exports/datev
DATEV_DEFAULT_SKR=SKR03

# --- GoBD / Compliance ---
GOBD_RETENTION_YEARS=10
GOBD_EVIDENCE_DIR=./evidence

# --- OAuth (Google) ---
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# --- Resend (Production Email) ---
RESEND_API_KEY=
RESEND_FROM_ADDRESS=luis@sbsdeutschland.de

# --- n8n Webhooks ---
N8N_WEBHOOK_BASE_URL=

# --- KoSIT Validator ---
KOSIT_VALIDATOR_URL=http://kosit-validator:8080
KOSIT_VALIDATOR_TIMEOUT=30
ENVEOF

echo "  ✅ .env.example created"

# ═══════════════════════════════════════════════════════════════
# 0.2 REPO HYGIENE: Remove junk files + update .gitignore
# ═══════════════════════════════════════════════════════════════

echo "🧹 [0.2] Removing junk files..."
rm -f 0 "0:" "19.5:" "365:" "=" "," avg_month cookies.txt \
  "ervice - Invoice Processing Web Application" database_numbered.txt 2>/dev/null || true

cat > .gitignore << 'GIEOF'
# Environment & Secrets
.env
.env.*
*.env
.env.new
.env.local
.env.production

# Virtual Environment
venv/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/

# Documents & Uploads
*.pdf
*.xlsx
*.xls
*.csv
*.docx
*.doc

# Images
*.jpg
*.jpeg
*.png
*.gif
*.bmp
*.ico
*.svg
*.webp

# Temporary & Cache
*.log
*.tmp
*.temp
*.bak
*.backup
*.swp
*.swo
*~
nohup.out

# Output & Batch Files
output/
outputs/
batch_*
temp_*
tmp_*

# Logs
logs/
*.log.*
log_*

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
Desktop.ini

# IDE
.vscode/
.idea/
*.sublime-project
*.sublime-workspace
.project
.pydevproject
.settings/

# Testing
.tox/
.nox/
.hypothesis/
pytestdebug.log

# Jupyter
.ipynb_checkpoints
*.ipynb

# Database
*.db
*.sqlite
*.sqlite3

# Temp directories
/tmp/
/temp/
/cache/

# --- Custom exceptions ---
!web/static/sbs-logo-new.png
.env

# --- Enterprise hygiene ---
web/*.bak-*
web/templates/*.bak-*
backups/*.db.gz
*.bak-*
.codex/

# --- Secrets & Config with secrets ---
config.yaml

# --- Docker ---
docker-compose.override.yml

# --- Alembic ---
alembic/versions/__pycache__/

# --- Evidence / Exports ---
evidence/
exports/
GIEOF

echo "  ✅ Junk removed + .gitignore updated"

# ═══════════════════════════════════════════════════════════════
# 0.3 DEPENDENCIES
# ═══════════════════════════════════════════════════════════════

echo "📦 [0.3] Updating dependencies..."

cat > requirements.txt << 'REQEOF'
# ============================================================================
# SBS Nexus Finance – Python Dependencies
# ============================================================================

# --- Web Framework ---
fastapi>=0.115.0,<1.0
uvicorn[standard]>=0.32.0,<1.0
starlette>=0.40.0,<1.0
python-multipart>=0.0.12
jinja2>=3.1.0,<4.0
aiofiles>=24.0

# --- Database ---
sqlalchemy>=2.0.30,<3.0
psycopg[binary]>=3.2.0,<4.0
alembic>=1.14.0,<2.0

# --- Data & Parsing ---
pydantic>=2.10.0,<3.0
pydantic-settings>=2.6.0,<3.0
pandas>=2.2.0,<3.0
numpy>=1.26.0,<2.0
openpyxl>=3.1.0,<4.0
PyPDF2>=3.0.0,<4.0
python-dateutil>=2.9.0
PyYAML>=6.0
lxml>=5.0.0,<6.0

# --- AI / LLM ---
openai>=2.3.0,<3.0
anthropic>=0.40.0,<1.0

# --- HTTP ---
httpx>=0.28.0,<1.0

# --- Auth & Security ---
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0
python-dotenv>=1.0.0

# --- Email ---
aiosmtplib>=3.0.0,<4.0

# --- Monitoring & Logging ---
structlog>=24.0.0
rich>=14.0.0

# --- PDF/Document ---
pillow>=11.0.0
python-pptx>=1.0.0

# --- Utilities ---
pytz>=2025.1
tqdm>=4.67.0
REQEOF

cat > requirements-dev.txt << 'DEVEOF'
# ============================================================================
# SBS Nexus Finance – Development Dependencies
# ============================================================================
-r requirements.txt

# --- Testing ---
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0
httpx

# --- Linting & Formatting ---
ruff>=0.8.0

# --- Type Checking ---
mypy>=1.13.0

# --- Security ---
bandit>=1.8.0
DEVEOF

echo "  ✅ requirements.txt + requirements-dev.txt created"

# ═══════════════════════════════════════════════════════════════
# 0.4 + 0.5 DOCKER
# ═══════════════════════════════════════════════════════════════

echo "🐳 [0.4] Creating Docker infrastructure..."

cat > Dockerfile << 'DKEOF'
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
    rm -rf _archive _archive_20260217_194225 _old_code backup_*  web/_archive
RUN mkdir -p /app/exports /app/evidence /app/uploads /app/logs && \
    chown -R sbs:sbs /app
USER sbs
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-8000}/api/v1/health || exit 1
EXPOSE ${APP_PORT:-8000}
CMD ["python", "-m", "uvicorn", "modules.rechnungsverarbeitung.src.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--log-level", "info", "--access-log"]
DKEOF

mkdir -p docker/kosit-validator
cat > docker/kosit-validator/Dockerfile << 'KSEOF'
# KoSIT Validator – Docker Sidecar
FROM eclipse-temurin:21-jre-alpine
WORKDIR /validator
ARG KOSIT_VERSION=1.5.0
ARG XRECHNUNG_CONFIG_VERSION=2024-06-20
RUN apk add --no-cache curl unzip && \
    curl -fsSL -o validator.zip \
      "https://github.com/itplr-kosit/validator/releases/download/v${KOSIT_VERSION}/validator-${KOSIT_VERSION}-distribution.zip" && \
    unzip -q validator.zip && rm validator.zip && \
    curl -fsSL -o xrechnung-config.zip \
      "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/release-${XRECHNUNG_CONFIG_VERSION}/validator-configuration-xrechnung_3.0.2_${XRECHNUNG_CONFIG_VERSION}.zip" && \
    unzip -q xrechnung-config.zip -d xrechnung-config && rm xrechnung-config.zip && \
    apk del curl unzip
RUN addgroup -S kosit && adduser -S kosit -G kosit && chown -R kosit:kosit /validator
USER kosit
EXPOSE 8080
CMD ["java", "-jar", "validationtool-1.5.0-standalone.jar", \
     "-s", "xrechnung-config/scenarios.xml", "-D", "-H", "0.0.0.0", "-P", "8080"]
KSEOF

cat > docker-compose.yml << 'DCEOF'
# ============================================================================
# SBS Nexus Finance – Docker Compose
# ============================================================================

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-sbs_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dev_password_change_me}
      POSTGRES_DB: ${POSTGRES_DB:-sbs_nexus}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "${DB_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-sbs_user} -d ${POSTGRES_DB:-sbs_nexus}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - sbs-internal

  app:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-sbs_user}:${POSTGRES_PASSWORD:-dev_password_change_me}@db:5432/${POSTGRES_DB:-sbs_nexus}
      APP_ENV: ${APP_ENV:-development}
      APP_SECRET_KEY: ${APP_SECRET_KEY:-dev-secret-change-in-production}
      APP_PORT: "8000"
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      KOSIT_VALIDATOR_URL: http://kosit-validator:8080
      SMTP_SERVER: ${SMTP_SERVER:-}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USERNAME: ${SMTP_USERNAME:-}
      SMTP_PASSWORD: ${SMTP_PASSWORD:-}
      RESEND_API_KEY: ${RESEND_API_KEY:-}
    volumes:
      - ./uploads:/app/uploads
      - ./exports:/app/exports
      - ./evidence:/app/evidence
    ports:
      - "${APP_PORT:-8000}:8000"
    networks:
      - sbs-internal

  kosit-validator:
    build:
      context: ./docker/kosit-validator
      dockerfile: Dockerfile
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:8080/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - sbs-internal

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-sbs_user}:${POSTGRES_PASSWORD:-dev_password_change_me}@db:5432/${POSTGRES_DB:-sbs_nexus}
    command: ["python", "-m", "alembic", "upgrade", "head"]
    networks:
      - sbs-internal
    profiles:
      - migrate

volumes:
  pgdata:
    driver: local

networks:
  sbs-internal:
    driver: bridge
DCEOF

echo "  ✅ Dockerfile + docker-compose.yml + KoSIT Dockerfile created"

# ═══════════════════════════════════════════════════════════════
# 0.6 ALEMBIC
# ═══════════════════════════════════════════════════════════════

echo "🗂️  [0.6] Setting up Alembic migrations..."

cat > alembic.ini << 'ALEOF'
[alembic]
script_location = alembic
prepend_sys_path = .

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
ALEOF

mkdir -p alembic/versions

cat > alembic/env.py << 'AENVEOF'
"""Alembic environment configuration for SBS Nexus Finance."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

from shared.db.session import Base
from modules.rechnungsverarbeitung.src.invoices.db_models import (
    Invoice, InvoiceEvent,
)

config = context.config

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sbs_user:dev_password_change_me@localhost:5432/sbs_nexus",
)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
AENVEOF

cat > alembic/script.py.mako << 'MAKOEOF'
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
MAKOEOF

cat > alembic/versions/001_initial.py << 'MIGEOF'
"""001 – Initial schema: invoices + invoice_events

Revision ID: 001_initial
Revises:
Create Date: 2026-02-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False, server_default="invoice"),
        sa.Column("file_name", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("uploaded_by", sa.String(128), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("source_system", sa.String(128), nullable=False, server_default="sbs-nexus"),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_document_id", "invoices", ["document_id"], unique=True)
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "invoice_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status_from", sa.String(), nullable=True),
        sa.Column("status_to", sa.String(), nullable=True),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_events_tenant_id", "invoice_events", ["tenant_id"])
    op.create_index("ix_invoice_events_document_id", "invoice_events", ["document_id"])


def downgrade() -> None:
    op.drop_table("invoice_events")
    op.drop_table("invoices")
MIGEOF

echo "  ✅ Alembic setup complete (alembic.ini + env.py + 001_initial migration)"

# ═══════════════════════════════════════════════════════════════
# 0.7 CI/CD + PYPROJECT.TOML
# ═══════════════════════════════════════════════════════════════

echo "⚙️  [0.7] Setting up CI/CD + tooling..."

cat > pyproject.toml << 'PPEOF'
[project]
name = "sbs-nexus-finance"
version = "0.1.0"
description = "KI-gestützte E-Rechnungsverarbeitung für den deutschen Mittelstand"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 120
src = ["modules", "shared"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "S", "UP", "SIM"]
ignore = ["E501", "S101", "B008"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S105", "S106"]
"alembic/**/*.py" = ["E402"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests", "modules/rechnungsverarbeitung/tests"]
pythonpath = ["."]
addopts = "-v --tb=short"
PPEOF

mkdir -p .github/workflows
cat > .github/workflows/tests.yml << 'CIEOF'
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.13"

jobs:
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      - run: pip install ruff mypy
      - run: ruff check .
      - run: ruff format --check .

  test:
    name: Tests
    runs-on: ubuntu-latest
    needs: quality
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: sbs_nexus_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://test_user:test_password@localhost:5432/sbs_nexus_test
      APP_ENV: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: python -m alembic upgrade head
      - run: python -m pytest modules/rechnungsverarbeitung/tests/ -v --tb=short

  security:
    name: Security
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install bandit
      - run: bandit -r modules/ shared/ -ll --skip B101

  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [quality, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t sbs-nexus:${{ github.sha }} .
      - run: docker run --rm sbs-nexus:${{ github.sha }} python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
CIEOF

echo "  ✅ pyproject.toml + CI/CD pipeline created"

# ═══════════════════════════════════════════════════════════════
# BONUS: shared/settings.py + shared/db/session.py + __init__.py
# ═══════════════════════════════════════════════════════════════

echo "🏗️  [Bonus] Creating app infrastructure..."

# __init__.py files
touch shared/__init__.py
touch shared/db/__init__.py
touch shared/tenant/__init__.py
touch modules/__init__.py
touch modules/rechnungsverarbeitung/__init__.py
touch modules/rechnungsverarbeitung/src/__init__.py
touch modules/rechnungsverarbeitung/src/api/__init__.py
touch modules/rechnungsverarbeitung/src/invoices/__init__.py
touch modules/rechnungsverarbeitung/src/invoices/services/__init__.py
touch modules/rechnungsverarbeitung/src/invoices/scripts/__init__.py

# shared/settings.py
cat > shared/settings.py << 'SETEOF'
"""Application settings loaded from environment variables."""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://sbs_user:dev_password_change_me@localhost:5432/sbs_nexus"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""
    resend_from_address: str = "luis@sbsdeutschland.de"
    datev_export_dir: str = "./exports/datev"
    datev_default_skr: str = "SKR03"
    gobd_retention_years: int = 10
    gobd_evidence_dir: str = "./evidence"
    kosit_validator_url: str = "http://localhost:8080"
    kosit_validator_timeout: int = 30
    google_client_id: str = ""
    google_client_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
SETEOF

# shared/db/session.py
cat > shared/db/session.py << 'DBEOF'
"""Database session management with SQLAlchemy."""
from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sbs_user:dev_password_change_me@localhost:5432/sbs_nexus",
)

engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
DBEOF

echo "  ✅ settings.py + session.py + __init__.py files created"

# ═══════════════════════════════════════════════════════════════
# UPDATE API: /api/v1 versioning
# ═══════════════════════════════════════════════════════════════

echo "🔌 [API] Updating API with versioned endpoints..."

cat > modules/rechnungsverarbeitung/src/api/main.py << 'APIEOF'
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, UploadFile, File, Header, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.tenant.context import TenantContext
from shared.db.session import get_session
from modules.rechnungsverarbeitung.src.invoices.services.invoice_processing import (
    process_invoice_upload,
)
from modules.rechnungsverarbeitung.src.invoices.db_models import Invoice, InvoiceEvent

# --- App ---
app = FastAPI(
    title="SBS Nexus Finance API",
    version="1.0.0",
    description="KI-gestützte E-Rechnungsverarbeitung für den deutschen Mittelstand",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1 = APIRouter(prefix="/api/v1", tags=["v1"])


# --- Health ---

@app.get("/api/v1/health")
async def health():
    checks: dict[str, str] = {"api": "ok"}
    try:
        with get_session() as session:
            session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {
        "status": status,
        "checks": checks,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Tenant ---

def set_tenant_from_header(x_tenant_id: str | None) -> None:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    TenantContext.set_current_tenant(x_tenant_id)


@v1.post("/invoices/upload")
async def upload_invoice(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    uploaded_by: str | None = Header(default=None, alias="X-User-ID"),
    file: UploadFile = File(...),
):
    set_tenant_from_header(x_tenant_id)
    metadata = process_invoice_upload(
        file_stream=file.file,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=uploaded_by,
    )
    return {
        "document_id": metadata.id,
        "tenant_id": metadata.tenant_id,
        "status": metadata.status,
        "file_name": metadata.file_name,
        "document_type": metadata.document_type,
    }


@v1.get("/invoices/{document_id}")
async def get_invoice(
    document_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    set_tenant_from_header(x_tenant_id)
    tenant_id = TenantContext.get_current_tenant()

    with get_session() as session:
        invoice: Invoice | None = (
            session.query(Invoice)
            .filter(Invoice.document_id == document_id, Invoice.tenant_id == tenant_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        response_data: dict[str, Any] = {
            "document_id": invoice.document_id,
            "tenant_id": invoice.tenant_id,
            "status": invoice.status,
            "file_name": invoice.file_name,
            "document_type": invoice.document_type,
            "uploaded_by": invoice.uploaded_by,
            "uploaded_at": invoice.uploaded_at.isoformat() if invoice.uploaded_at else None,
            "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
            "source_system": invoice.source_system,
        }
    return response_data


@v1.get("/invoices")
async def list_invoices(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    limit: int = 50,
    offset: int = 0,
):
    set_tenant_from_header(x_tenant_id)
    tenant_id = TenantContext.get_current_tenant()

    with get_session() as session:
        query = (
            session.query(Invoice)
            .filter(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        invoices = list(query)
        items: list[dict[str, Any]] = [
            {
                "document_id": inv.document_id,
                "tenant_id": inv.tenant_id,
                "status": inv.status,
                "file_name": inv.file_name,
                "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            }
            for inv in invoices
        ]
    return {"items": items, "limit": limit, "offset": offset}


@v1.get("/invoices/{document_id}/events")
async def get_invoice_events(document_id: str, x_tenant_id: str = Header(alias="X-Tenant-ID")):
    set_tenant_from_header(x_tenant_id)
    tenant_id = TenantContext.get_current_tenant()

    with get_session() as session:
        events = (
            session.query(InvoiceEvent)
            .filter(InvoiceEvent.document_id == document_id, InvoiceEvent.tenant_id == tenant_id)
            .order_by(InvoiceEvent.created_at.asc())
            .all()
        )
        primitive_events = [
            {
                "id": ev.id,
                "tenant_id": ev.tenant_id,
                "document_id": ev.document_id,
                "event_type": ev.event_type,
                "status_from": ev.status_from,
                "status_to": ev.status_to,
                "actor": ev.actor,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "metadata": ev.details or {},
            }
            for ev in events
        ]
    return JSONResponse(content=primitive_events)


app.include_router(v1)
APIEOF
