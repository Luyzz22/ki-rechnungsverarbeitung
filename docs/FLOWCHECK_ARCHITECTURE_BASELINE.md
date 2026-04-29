# FlowCheck+ – Architecture Baseline

> **Zweck:** Repository‑weite Bestandsaufnahme als Grundlage für den weiteren Aufbau von FlowCheck+ / Finance Control Layer.
> **Status:** Read‑only Analyse (keine Codeänderungen).
> **Erstellt:** 2026‑04‑29
> **Verfasser:** Principal Engineer (Analyse, automatisiert).
> **Quellen:** `web/app.py`, `modules/rechnungsverarbeitung/**`, `database.py`, `einvoice*.py`, `datev*.py`, `audit.py`, `approval.py`, `rbac.py`, `llm_router.py`, `finance_copilot.py`, `api_nexus.py`, `Dockerfile`, `docs/architecture/erechnung-hub_baseline.md`, `docs/erechnung/gap_analysis.md`, `docs/adr/*`.

> **Hinweis zu Unsicherheiten:** Markiert mit „⚠️ Unsicher". Stichprobenartig validiert; kein vollständiger statischer Lauf gegen alle ~120 Python‑Dateien. Aussagen zu Compliance, GoBD, BEG IV, GDPR sind aus dem Code abgeleitet und juristisch zu validieren.

---

## 1. Executive Summary

Das Repository ist heute eine **hybride zweischichtige FastAPI‑Anwendung** im Übergang von einem monolithischen Legacy‑Stack zu einem modularen Hub‑Stack:

- **Legacy‑Layer** (`web/app.py` mit ~7000 Zeilen / ~195 Routen, SQLite via `database.py`): Produkt „SBS KI‑Rechnungsverarbeitung", komplett mit Auth, RBAC, Org‑Management, Upload, Approval, DATEV‑Export, MBR‑Generator, Stripe‑Billing, Multi‑Product‑Subscriptions, OAuth (Google/Microsoft), 2FA, Webhooks, Rate Limiting und Audit‑Trail.
- **Modular‑Layer** (`modules/rechnungsverarbeitung/src/api/main.py` mit ~50 Routen, PostgreSQL via SQLAlchemy/Alembic, Tenant‑Context): „SBS Nexus Finance API v1.2.0", deterministische State Machine, hash‑chained Audit Trail, GoBD Evidence Package, KoSIT‑Validator, idempotenter DATEV‑Export, JWT Auth, MultiTenancy.

Die laut `Dockerfile` produktiv gestartete App ist die modulare API (`modules.rechnungsverarbeitung.src.api.main:app`), während operativ laut `AGENTS.md`/`CLAUDE.md` und Code‑Pfaden weiterhin der Legacy‑Stack auf `app.sbsdeutschland.com` aktiv ist. ⚠️ Unsicher, welche der beiden Apps an welchem Endpunkt tatsächlich läuft – formal sind beide gepflegt.

**Daraus ergibt sich für FlowCheck+ als Finance Control Layer:**

1. Die zentralen Domain‑Bausteine für FlowCheck+ existieren bereits im Modular‑Layer (State Machine, AuditChain, GoBDEvidence, KoSITValidator, DATEV‑Adapter, AIExtractionService, ERechnungHubService).
2. Die zentralen Marketing‑/Vertrags‑/Self‑Service‑Bausteine (Login, Organisation, Billing, Multi‑Tenant, OAuth, RBAC, MBR) existieren primär im Legacy‑Layer.
3. **Risiko 1:** Datenmodell‑Drift (SQLite‑`invoices` vs. PostgreSQL‑`invoices`/`invoice_events`) – ein gemeinsames Schema fehlt.
4. **Risiko 2:** Mehrfach implementierte Bausteine (XRechnung, DATEV, Auth, RBAC, AI‑Extraktion) erhöhen die Pflegekosten und das Compliance‑Risiko.
5. **Chance:** Der Modular‑Layer ist die natürliche Heimat für FlowCheck+ (deterministische Pipeline, audit‑first, mandantensicher) und deckt ADRs zu Validation/DATEV/Storage bereits ab (`docs/adr/*`).

---

## 2. Aktuelle Architektur

### 2.1 Drei FastAPI‑Einstiegspunkte

| Entry Point | Datei | Größe | Stack | Status |
|---|---|---|---|---|
| Minimal Bridge | `main.py` | 43 Z. | FastAPI + Mounts (`budget_router`, `invoice_router`) | ⚠️ Unsicher, ob noch produktiv genutzt |
| **Legacy Monolith** | `web/app.py` | 7021 Z. | FastAPI, SQLite, Jinja2 (HTML), Stripe, OAuth, Sessions | Aktiv (Domain `app.sbsdeutschland.com`) |
| **Modular API** | `modules/rechnungsverarbeitung/src/api/main.py` | 1619 Z. | FastAPI, SQLAlchemy, JWT, Tenant‑Header, Alembic | Aktiv laut `Dockerfile` (`CMD …main:app`) |

### 2.2 Architekturkarte (Ist‑Stand, vereinfacht)

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Nginx (HTTPS, app.sbsdeutschland.com)           │
└──────────────┬───────────────────────────────────────┬─────────────────┘
               │                                       │
        ┌──────▼──────┐                       ┌────────▼────────┐
        │ Legacy App  │                       │  Modular API    │
        │ web/app.py  │                       │  modules/.../   │
        │ Sessions    │                       │  api/main.py    │
        │ Jinja2      │                       │  JWT            │
        │ HTML‑UI     │                       │  X‑Tenant‑ID    │
        └──┬───────┬──┘                       └────┬────────────┘
           │       │                               │
   ┌───────▼─┐  ┌──▼──────┐                  ┌─────▼─────────────┐
   │ SQLite  │  │ Stripe  │                  │ PostgreSQL        │
   │ invoices│  │ OAuth   │                  │ invoices /        │
   │ users   │  │ SendGrid│                  │ invoice_events    │
   │ jobs ...│  │ IMAP    │                  │ (Alembic)         │
   └─────────┘  └─────────┘                  └───────────────────┘
                     │                               │
              ┌──────┴──────┐               ┌────────┴──────────┐
              │ LLM Router  │               │ AIExtractionSvc   │
              │ GPT‑4o +    │               │ Gemini Flash +    │
              │ Claude 4.5  │               │ Claude (Fallback) │
              └─────────────┘               │ KoSIT Validator   │
                                            │ AuditChain        │
                                            │ GoBDEvidence      │
                                            │ DatevExport (idmp)│
                                            └───────────────────┘
```

### 2.3 Deployment & Build

- **Dockerfile** (`Dockerfile`): Multi‑Stage Python 3.13‑slim, Healthcheck auf `/api/v1/health`, läuft als User `sbs`, Startbefehl Modular‑API.
- **docker‑compose.yml**: Services `db` (Postgres 16), `app` (FastAPI), `kosit-validator` (Java/Docker), `migrate` (Alembic).
- **Alembic** (`alembic.ini`, `alembic/versions/001_initial.py`): einzige Migration legt `invoices` + `invoice_events` (Postgres) an.
- **Hosting laut `AGENTS.md`/`CLAUDE.md`**: Server `207.154.200.239`, systemd‑Service `invoice-app.service`, SQLite‑DB `/var/www/invoice-app/invoices.db` – das beschreibt den **Legacy‑Stack**, nicht den Container. ⚠️ Unsicher, ob beide parallel laufen oder das Dockerfile noch nicht produktiv ist.

---

## 3. Hauptmodule

### 3.1 Legacy‑Domain‑Module (Repo‑Root)

| Datei | Zeilen | Verantwortung |
|---|---|---|
| `web/app.py` | 7021 | Hauptanwendung (Routes, HTML‑Templates, Session‑Auth, Stripe, OCR‑Job‑Pipeline) |
| `database.py` | 2250 | SQLite Persistenz, Schema‑Init, Statistik, User‑/Subscription‑Funktionen |
| `api_nexus.py` | 1993 | Nexus‑Gateway‑API (`/api/nexus/*`), Webhooks, Notifications |
| `llm_router.py` | 978 | Hybrid GPT‑4o + Claude Sonnet 4.5 + Vision‑Fallback |
| `datev.py` | 854 | DATEV EXTF/CSV Export Enterprise (SKR03/SKR04), `DatevCsvExporter`, `DatevExportConfig` |
| `einvoice.py` | 740 | XRechnung 3.0 (CII) Generator, `XRechnungGenerator`, `validate_xrechnung` |
| `approval.py` | 658 | Multi‑Level‑Approval, Status‑Workflow, Approval Rules |
| `finance_copilot.py` | 534 | Regelbasierter Finance Copilot (kein LLM) |
| `rbac.py` | 431 | 5‑Rollen‑Modell (owner/admin/manager/member/viewer), Permission‑Decorators |
| `einvoice_import.py` | 412 | E‑Rechnungs‑Importer (CII + UBL), `EInvoiceImporter`, `extract_xml_from_pdf` |
| `budget_routes.py` | 392 | Budget‑Dashboard‑Routen, Excel‑Export |
| `datev_exporter.py` | 266 | Älterer DATEV‑Exporter (CSV ASCII) – Duplikat zu `datev.py` |
| `audit.py` | 175 | Einfacher Audit‑Logger (`log_audit`, `AuditAction`) |
| `two_factor.py` | 212 | TOTP via `pyotp`, QR‑Code, Backup‑Codes |
| `api_keys.py` | 226 | API‑Key‑Generierung, SHA‑256‑Hashing, Rate‑Limit pro Key |

### 3.2 Modulare Domain (`modules/rechnungsverarbeitung/src/`)

| Pfad | Verantwortung |
|---|---|
| `api/main.py` | „SBS Nexus Finance API v1.2.0", JWT‑Auth, X‑Tenant‑ID‑Header, ~50 Endpunkte |
| `auth/jwt_auth.py` | JWT (access/refresh), bcrypt Password Hashing, `UserAuth`, `get_current_user` |
| `auth/rate_limiter.py` | `slowapi`‑basierter Rate Limiter |
| `invoices/db_models.py` | SQLAlchemy Models `Invoice` + `InvoiceEvent` (Postgres mit JSONB) |
| `invoices/models.py` | `InvoiceDocumentMetadata` Dataclass (canonical Metadaten) |
| `invoices/services/invoice_processing.py` | Upload‑Pipeline (`process_invoice_upload`): klassifizieren → validieren → KI‑Extraktion |
| `invoices/services/erechnung_hub.py` | Format‑Erkennung (XRechnung/ZUGFeRD/PDF), canonical schema, Validation Hook |
| `invoices/services/kosit_validator.py` | EN16931 / XRechnung Validierung, optional KoSIT‑Binary via Subprocess |
| `invoices/services/xrechnung_generator.py` | Neuer XRechnung Generator (UBL‑basiert) |
| `invoices/services/state_machine.py` | Deterministische `InvoiceStateMachine` mit `TRANSITION_TABLE` |
| `invoices/services/audit_chain.py` | SHA‑256 Hash‑Chain (`AuditChain`, `_compute_hash`) |
| `invoices/services/gobd_evidence.py` | ZIP‑Evidence‑Package mit Manifest + Hash‑Verifikation |
| `invoices/services/datev_export.py` | Idempotenter DATEV‑CSV‑Adapter (`DatevExportService`) |
| `invoices/services/ai_extraction.py` | KI‑Extraktion mit Gemini 2.5 Flash (primary) + Claude Sonnet (Fallback) |
| `invoices/services/duplicate_detection.py` | Tenant‑aware Duplicate Detection |
| `invoices/services/anomaly_detection.py` | Anomalie‑Heuristiken |
| `invoices/services/file_storage.py` | Persistente Ablage `/var/www/invoice-app/storage/invoices/{tenant}/{doc}/{file}` |
| `invoices/services/finance_copilot.py` | Finance Copilot v2 (Tenant‑Aware) |
| `invoices/services/email_ingestion.py` | Email‑Inbox Parser |
| `invoices/services/llama_index_service.py` | LlamaIndex Integration (optional) |

### 3.3 Querschnitts‑Module (`shared/`)

| Datei | Verantwortung |
|---|---|
| `shared/settings.py` | `pydantic-settings` Konfiguration (`DATABASE_URL`, `OPENAI_API_KEY`, `KOSIT_VALIDATOR_URL`, `GOBD_RETENTION_YEARS=10`) |
| `shared/db/session.py` | SQLAlchemy Engine + Session Factory + `Base` |
| `shared/tenant/context.py` | `TenantContext` via `contextvars.ContextVar` (default `"default-tenant"`) |

### 3.4 Reporting & Analytik

| Datei | Verantwortung |
|---|---|
| `mbr/generator.py` + `mbr/data.py` + `mbr/llm.py` + `mbr/pptx_renderer.py` | Monthly Business Review (PPTX, 7 Slides, optional LLM) |
| `analytics_service.py` | `get_finance_snapshot` (Aggregationen, Top Vendors, VAT) |
| `spend_analytics.py` | Predictive Spend Alerts, `spend_budgets`, `spend_alerts`, `spend_snapshots` |
| `budget_service.py` | Monatsbudgets, Ist‑/Soll‑Werte, Alerts |
| `dashboard_widgets.py` | Konfigurierbare Dashboard‑Widgets |
| `cost_tracker.py` | LLM‑Kosten‑Tracking |

---

## 4. FastAPI‑Routen und Entry Points

> Quelle: Grep auf `@app.*`, `@v1.*`, `@router.*`. Aufgrund der Code‑Größe nur thematische Cluster mit Beispielzeilen.

### 4.1 Legacy `web/app.py` – ~195 Routen (Auswahl)

**Marketing/Public** (`web/app.py:214–248`, `:6514–6517`)

- `GET /landing`, `/sicherheit`, `/compliance`, `/avv`, `/api`, `/referenzen`
- `GET /e-rechnung-2025`, `/e-rechnung`, `/xrechnung`, `/zugferd`

**Auth/User** (`:2046–2247`)

- `GET/POST /login`, `/register`, `/logout`, `/password-reset/*`
- `GET /api/user`, `/api/2fa/{setup,verify,disable,status}` (`:2420–2474`)
- OAuth: `web/routes_oauth.py` → `/auth/google`, `/auth/google/callback`, `/auth/microsoft`, `/auth/microsoft/callback`

**Job‑Pipeline** (`:271–687`)

- `POST /api/upload` – Datei‑Upload, Subscription‑Check, Rate Limit, Job‑Anlage
- `POST /api/process/{job_id}` – KI‑Verarbeitung
- `GET /api/status/{job_id}`, `/api/results/{job_id}`, `/api/download/{job_id}/{format}`
- `GET /results/{job_id}` (HTML), `/job/{job_id}` (HTML)

**Approvals** (`:5552–5825`)

- `GET /approvals`, `/approvals/my`, `/approvals/rules` (HTML)
- `POST /api/approvals/{invoice_id}/{approve,reject,assign,comment}`
- `POST /api/approvals/bulk-approve`
- `GET/POST/PUT/DELETE /api/approvals/rules`

**DATEV/Export** (`:5846–6022`, `:3690–3725`, `:1520`)

- `POST /api/datev/export`, `GET /api/datev/download/{filename}`, `/api/datev/preview`
- `GET /api/job/{job_id}/export/{xrechnung,zugferd,zip,comprehensive}`
- `POST /api/export/sepa`, `/api/job/{job_id}/export/sepa`

**Kontierung & Budget** (`:6087–6270`, `:1078`, plus `budget_routes.py`)

- `POST /api/kontierung/{vorschau,suggest,save}`, `GET /api/kontierung/{konten,historie}`
- `GET /budget`, `/budget/jahr` (`budget_routes.py:54–84`)

**Zahlungen** (`:6306–6474`)

- `GET /zahlungen`, `/api/zahlungen/{dashboard,offene,skonto-chancen,statistik,export/sepa}`
- `POST /api/zahlungen/{analysieren,status}`

**Audit & Admin** (`:1362–1502`, `:4811`)

- `GET /admin`, `/admin/users`, `/audit-log`
- `GET /api/audit-log`
- `POST/PUT /api/admin/users{,/{user_id}{,/toggle}}`

**Subscriptions/Billing** (`:2819–3332`)

- `POST /api/checkout/create-session`, `/api/stripe/webhook`, `/api/subscription/cancel`
- `POST /api/billing/portal`

**Reports & Copilot** (`:6902–7016`, `:4185`, `:4511`)

- `GET /mbr` (HTML), `GET /mbr/monthly.pptx` (`:993` – generiert PPTX, `require_login`)
- `GET /api/analytics/finance-snapshot`
- `POST /api/copilot/finance/query` (`finance_copilot.generate_finance_answer`)
- `GET /spend-analytics`, `GET /api/internal/spend/{overview,alerts,forecast,budgets,supplier/{name}}`

**Integrationen** (`:6557–6635`)

- `GET /integrations`, `POST /api/integrations/{test,save,sync}`

**Webhooks/API‑Keys** (`:2335–2415`)

- CRUD für `/api/keys` und `/api/webhooks`

**Nexus‑Gateway** (`api_nexus.py`, falls importiert)

- `POST /api/nexus/process-invoice`, `/api/nexus/classify-document`
- `GET /api/nexus/health`
- ⚠️ Unsicher, ob in `web/app.py` aktuell `app.include_router(nexus_router)` steht (Importversuch ist vorhanden, Inklusion nicht eindeutig).

### 4.2 Modulare API `modules/.../api/main.py` – ~50 Routen

Alle unter Prefix `/api/v1`, mit Header `X-Tenant-ID` Pflicht (außer Health/Auth). Zeilenangaben aus `main.py`:

- **Health:** `GET /api/v1/health` (`:160`).
- **Auth:** `POST /auth/token` (`:1353`), `/auth/refresh` (`:1361`), `GET /auth/me` (`:1369`), `POST /auth/forgot-password` (`:1594`).
- **Users/RBAC:** `POST /users/{register,login,invite}`, `GET /users/{profile,team}`, `PUT /users/role`, `DELETE /users/{user_id}` (`:1393–1594`).
- **Invoices Lifecycle:**
  - `POST /invoices/upload` (`:182`), `/invoices/upload-batch` (`:403`).
  - `GET /invoices` (`:724`), `/invoices/{document_id}` (`:761`), `/invoices/{document_id}/file` (`:206`).
  - `POST /invoices/{document_id}/transition` (`:788`), `/validate` (`:1060`), `/kontierung` (`:1150`).
  - `GET /invoices/{document_id}/{transitions,events,chain/verify}` (`:851–901`).
  - `POST /invoices/{document_id}/evidence` (`:923`).
- **E‑Rechnung:**
  - `POST /invoices/{document_id}/generate-xrechnung` (`:229`), `/validate-xrechnung` (`:360`).
  - `POST /invoices/{document_id}/generate-zugferd` (`:509`).
- **DATEV:**
  - `POST /invoices/{document_id}/datev-export` (`:989`), `/invoices/datev-batch` (`:1233`).
  - `GET /export/datev-zip` (`:630`).
- **Duplikate / Anomalien:**
  - `GET /invoices/{document_id}/{duplicate-check,anomaly-check,mark-duplicate,skonto-check}` (`:435–541`).
- **Reports:**
  - `GET /export/{csv,excel}` (`:479,494`), `/audit-log` (`:661`), `/export-history` (`:694`).
  - `GET /analytics/{supplier-scorecard,dashboard}` (`:605,1335`).
- **Budget:**
  - `GET /budget/{kategorien,summary,monat}`, `POST /budget/set` (`:276–356`).
- **Email/Billing:**
  - `POST /email/poll`, `GET /email/status` (`:1436–1442`).
  - `GET /billing/{plans,subscription,usage}`, `POST /billing/{checkout,portal,webhook}` (`:1466–1543`).
- **Copilot:** `POST /copilot/chat` (`:1312`).

---

## 5. Datenbanktabellen und Datenhaltung

### 5.1 Zwei parallele Datenbanken

| | Legacy | Modular |
|---|---|---|
| **Engine** | SQLite | PostgreSQL 16 (`docker-compose.yml`) |
| **Pfad/URL** | `INVOICE_DB_PATH=/var/www/invoice-app/invoices.db` (`database.py:17`) | `DATABASE_URL=postgresql+psycopg://…` (`shared/settings.py:17`) |
| **Migrations** | DDL inline via `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE … ADD COLUMN` | `alembic/versions/001_initial.py` |
| **Schema‑Owner** | `database.py`, `budget_service.py`, `spend_analytics.py`, `multi_product_subscriptions.py`, `web/app.py` (Demo/Copilot/Integrations), `api_nexus.py` (notifications/webhooks) | `modules/.../db_models.py` |

### 5.2 Legacy‑Tabellen (SQLite)

Aus `database.py` (Hauptmodul):

- **`jobs`** (`:51`) – Upload‑Jobs (`job_id`, `created_at`, `status`, `total_files`, `successful`, `failed_count`, `total_amount`, `total_netto`, `total_mwst`, `exported_files`, `upload_path`, `failed_list`, `user_id`).
- **`invoices`** (`:71`) – Extrahierte Rechnungen, später um `content_hash`, `source_format`, `einvoice_raw_xml`, `einvoice_profile`, `einvoice_valid`, `einvoice_validation_message`, `confidence` ergänzt (`save_invoices` `:207`).
- **`corrections`** (`:532`), **`supplier_patterns`** (`:546`) – Lerndatensatz für Korrekturen.
- **`email_inbox_config`** (`:852`), **`email_processed`** (`:870`) – IMAP‑Inbox Konfiguration (Klartext‑Passwörter ⚠️ Risiko).
- **`users`** (`:965` und `:1079`) – ⚠️ **Tech Debt:** zweimal definiert, beide CREATE‑Statements werden ausgeführt (idempotent). Spalten via spätere `ALTER TABLE`: `is_admin`, `totp_enabled`, `totp_secret`, `totp_secret_pending`, `totp_backup_codes`, `oauth_provider`, `oauth_id`, `oauth_email`, `current_org_id`.
- **`subscriptions`** (`:1193`) – Plan‑Limits, Stripe‑IDs.

Aus weiteren Modulen:

- `audit_log` – referenziert in `audit.py:81`, ⚠️ Schema nicht in Repo aufzufinden (vermutlich extern via SQL/Migration angelegt).
- `roles`, `user_roles` – RBAC, Init in `rbac.py:284–306`.
- `approval_history`, plus `assigned_to`, `approved_by`, `rejected_by`, `payment_status` auf `invoices` – `approval.py`.
- `api_keys` – referenziert in `api_keys.py:73`, Schema nicht im Repo. ⚠️ Unsicher.
- `webhooks` – `api_nexus.py:1398`.
- `notifications` – `api_nexus.py:1008`.
- `budget_kategorien`, `monats_budgets`, `budget_ist_werte`, `budget_alerts` – `budget_service.py:46–98`.
- `spend_budgets`, `spend_alerts`, `spend_snapshots` – `spend_analytics.py:46–94`.
- `product_subscriptions` – `multi_product_subscriptions.py:131`.
- `kontierung_historie` – referenziert in `budget_routes.py:222`, Schema nicht im Repo. ⚠️ Unsicher.
- `demo_usage`, `copilot_demo_usage`, `integrations` – `web/app.py:1777,5331,6537`.
- `scheduled_reports`, `notification_log` – `migration_notifications.sql:24,46`.
- `rate_limit_usage` – `web/rate_limiter.py:39`.
- `maintenance_requests` – `smart_maintenance.py:551`.

### 5.3 Modulare Tabellen (PostgreSQL)

Aus `alembic/versions/001_initial.py` und `modules/.../db_models.py`:

- **`invoices`** – `id`, `document_id` (UUID, unique), `tenant_id`, `document_type` (XRechnung/ZUGFeRD/PDF), `file_name`, `mime_type`, `uploaded_by`, `uploaded_at`, `processed_at`, `source_system`, `status`, `supplier`, `total_amount`, `currency`, `tax_amount`, `invoice_number`, `invoice_date`, `due_date`. Erweiterungen wie `extracted_data` werden via `text("UPDATE …")` in `invoice_processing.py:152` geschrieben – ⚠️ nicht alle Spalten sind in Alembic deklariert.
- **`invoice_events`** – `id`, `tenant_id`, `document_id`, `event_type`, `status_from`, `status_to`, `actor`, `created_at`, `details` (JSONB).
- Weitere Postgres‑Tabellen (`budget_kategorien`, `monats_budgets`) werden im API‑Code (`api/main.py:283`) als bestehend angenommen, sind aber **nicht in der Alembic‑Migration**. ⚠️ Unsicher, wo das Schema lebt.

### 5.4 Datei‑/Storage‑Layer

- Legacy: lokales Upload‑Verzeichnis `web/uploads/` (`web/app.py:205`), DATEV‑Output `output/`, MBR `pptx_templates/` + Output via `python-pptx`.
- Modular: `FileStorageService` legt unter `STORAGE_ROOT=/var/www/invoice-app/storage/invoices/{tenant_id}/{document_id}/{filename}` ab (`file_storage.py:16`).
- Evidence Packages: `gobd_evidence.GoBDEvidenceService`, Default `./evidence/` (`shared/settings.py:29`).

---

## 6. E‑Rechnung / XRechnung / ZUGFeRD / KoSIT

### 6.1 Generatoren

| Komponente | Quelle | Format |
|---|---|---|
| Legacy XRechnung Generator | `einvoice.py` (`XRechnungGenerator`, `generate_xrechnung`) | CII / EN16931 (Profile `urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0`) |
| Legacy ZUGFeRD Embedder | `zugferd.py` (`create_zugferd_pdf`) | PDF/A‑3 + eingebettetes `factur-x.xml` (via `pikepdf`) |
| Modularer XRechnung Generator | `modules/.../services/xrechnung_generator.py` (`XRechnungGenerator`) | UBL‑basiert (laut Imports und Endpoint `:229`) – ⚠️ Genauer Output (UBL vs. CII) ist im Code zu prüfen, der Endpoint nennt nur `application/xml` |

### 6.2 Importer / Parser

- `einvoice_import.py` (`EInvoiceImporter`) erkennt CII (`urn:un:unece:uncefact:…:CrossIndustryInvoice`) und UBL (`urn:oasis:names:specification:ubl:…:Invoice-2`), inklusive ZUGFeRD/Factur‑X PDF‑Anhang über `pikepdf`. Felder: Rechnungsnummer, Datum, Aussteller/Empfänger, IBAN/BIC, MwSt, Brutto/Netto, Positionen.
- `modules/.../services/erechnung_hub.py` (`ERechnungHubService.detect_invoice_format`) macht Magic‑Bytes‑Klassifikation (`xrechnung`, `zugferd`, `pdf_other`, `xml_other`, `unknown`) und `build_canonical_invoice` (Mapping auf `CanonicalInvoice` mit `seller`/`buyer`/`line_items`/`total_*`).

### 6.3 KoSIT Validierung

- **Modular**: `modules/.../services/kosit_validator.py` (`KoSITValidator`).
  - Stage 1: lxml‑basierte Well‑Formedness + Pflichtfeld‑Checks (`BT-1, BT-2, BT-3, BT-5, BT-10, …`).
  - Stage 2 (optional): KoSIT Java Validator als Subprocess (`binary="kosit-validator"`, `timeout_seconds=10`, `config_version="xrechnung-3.0.1"`).
  - Persistiert `ValidationResult` mit `valid`, `error_count`, `warnings`, `info`.
- **Docker‑Service** `kosit-validator` ist in `docker-compose.yml:53` deklariert (Build aus `docker/kosit-validator/Dockerfile`).
- **ADR**: `docs/adr/adr-erechnung-validation.md` legt KoSIT als Primär‑Engine fest, native Vorvalidierung als Fallback hinter Feature‑Flag `ERECHNUNG_VALIDATION_ENGINE`.
- **Legacy**: `einvoice.py:635 validate_xrechnung` ist eine **eigene Heuristik** (Pflichtfeld‑String‑Suche), kein KoSIT‑Aufruf.

### 6.4 Endpunkte

- Legacy: `GET /api/job/{job_id}/export/xrechnung` (`web/app.py:3690`), `…/zugferd` (`:3725`).
- Modular:
  - `POST /api/v1/invoices/{document_id}/generate-xrechnung`
  - `POST /api/v1/invoices/{document_id}/validate-xrechnung`
  - `POST /api/v1/invoices/{document_id}/generate-zugferd`

### 6.5 Pipeline‑Integration (Modular)

`process_invoice_upload` (`invoice_processing.py:24`):

1. SHA‑256 vom Payload, FileStorage write.
2. Event `upload_received → uploaded`.
3. `ERechnungHubService.detect_invoice_format`.
4. Bei strukturierten Formaten (`xrechnung|zugferd|xml_other`): `validate_structured_invoice` → Status `validated|validation_failed`.
5. KI‑Extraktion (`AIExtractionService.extract`) → Status `suggested`.

---

## 7. DATEV‑kompatibler Export

> **Begriff im README:** „DATEV‑kompatibler Export" – kein Zertifikat, kein Hersteller‑Stempel. Aussagen zu DATEV bitte juristisch und steuerlich validieren.

### 7.1 Drei Implementierungen

| Implementierung | Datei | Charakter |
|---|---|---|
| Enterprise EXTF v700 | `datev.py` (`DatevCsvExporter`, `DatevBuchung`, `DatevExportConfig`) | DATEV EXTF Buchungsstapel v700, SKR03/SKR04, Kostenstellen, Belegfeld 1+2, Beleglink, Festschreibung, EU‑USt‑ID. Encoding `cp1252`. |
| Legacy ASCII v300 | `datev_exporter.py` (`export_to_datev`) | Kürzere Variante, EXTF v300, ruft `auto_accounting.suggest_account` für Konto‑Vorschläge auf. |
| Idempotent‑Adapter | `modules/.../services/datev_export.py` (`DatevExportService`, `DatevBookingRecord`, `DatevExportResult`) | Gleicher `document_id` → gleicher Output (`export_hash`), batch_id, GoBD‑Metadaten. |

### 7.2 ADR

`docs/adr/adr-datev-integration.md` priorisiert MVP **EXTF/CSV‑Export** mit Idempotency‑Key, Retry, Dead‑Letter‑Logging; Buchungsdatenservice‑Adapter parallel vorbereiten.

### 7.3 Konto‑Vorschläge

- `auto_accounting.py` (SKR03/SKR04 Mapping, Keyword‑Scoring) – einfacher rule‑based Engine.
- `kontierung_service.py` (`SKR03_ACCOUNTS`) verbindet Auto‑Kontierung mit DATEV‑Export, lernt aus `kontierung_historie` (Schema nicht im Repo, ⚠️ Unsicher).
- `category_ai.py` nutzt Anthropic Claude für Kategorie‑Vorschläge auf Basis vorhandener Kategorien‑Tabelle.
- Modular: `POST /api/v1/invoices/{document_id}/kontierung` (`api/main.py:1150`) – ⚠️ Implementierung im Detail nicht inspiziert.

### 7.4 Endpunkte

- Legacy: `POST /api/datev/export`, `GET /api/datev/download/{filename}`, `/api/datev/preview` (`web/app.py:5882–6022`).
- Modular: `POST /api/v1/invoices/{id}/datev-export`, `POST /api/v1/invoices/datev-batch`, `GET /api/v1/export/datev-zip`.

### 7.5 SEPA‑Pendant

`sepa_export.py` erzeugt SEPA Credit Transfer XML (SCT) mit IBAN/BIC‑Validierung – relevant für Zahlungsausgang, kein DATEV‑Belegtransfer.

---

## 8. KI‑/LLM‑Nutzung

### 8.1 Legacy LLM Router (`llm_router.py`)

- Provider: **OpenAI GPT‑4o** (`gpt-4o-2024-08-06`) und **Anthropic Claude Sonnet 4.5** (`claude-sonnet-4-5-20250929`).
- Routing per Komplexitätsscore (`pick_provider_model`, Threshold `ai.complexity_threshold` aus `config.yaml`, Default 40).
- Prompts: Sehr ausführliche, deutschsprachige Expert‑Prompts (`SYSTEM_PROMPT_OPENAI`, `SYSTEM_PROMPT_CLAUDE`) mit harten Regeln zu Aussteller/Empfänger/Steuernummer/USt‑IdNr.
- Vision‑Fallback: `extract_with_vision` konvertiert PDF (`pdf2image` 150 DPI) zu Bild und ruft GPT‑4o Vision.
- Confidence‑basiertes Re‑Routing (`extract_invoice_data_with_fallback`): Text < 200 Zeichen oder confidence < 0.5 → Vision.

### 8.2 Modulare AI Extraction (`ai_extraction.py`)

- **Primary**: Google Gemini 2.5 Flash (multimodal, Bilder + PDFs).
- **Fallback**: Anthropic Claude Sonnet.
- **Optional**: LlamaIndex (`llama_index_service.py`) für mehrseitige Dokumente.
- Antwort‑Schema: `supplier`, `invoice_number`, `invoice_date`, `due_date`, `total_amount_net`, `tax_amount`, `total_amount_gross`, `currency`, `tax_rate`, `line_items`, `iban`, `payment_reference`.

### 8.3 Kategorisierung & Copilots

- `category_ai.py:predict_category` nutzt Claude für Kategorie‑Klassifikation, mit Lerneffekt aus `learned_categories` (Schema ⚠️ Unsicher).
- `finance_copilot.py` ist ausdrücklich **regelbasiert** ohne LLM (Aussage in Datei‑Docstring) – „deterministisch, auditierbar, schnell" – Intent‑Klassifikation per Keywords.
- Modularer Copilot: `POST /api/v1/copilot/chat` (`api/main.py:1312`) – ⚠️ Konkrete LLM‑Anbindung im Detail nicht geprüft.

### 8.4 Kosten & Budget

- `cost_tracker.py` protokolliert LLM‑API‑Kosten.
- `mbr/llm.py` (Narrative‑Generierung mit `MBR_LLM_MODEL`, Default `gpt-4o-2024-08-06`) hat Fallback `MBR_USE_LLM=0` (laut `AGENTS.md` Pflicht‑Feature).

---

## 9. Audit Logging

### 9.1 Legacy Audit (`audit.py`)

- Tabelle `audit_log` mit Spalten `user_id`, `user_email`, `action`, `resource_type`, `resource_id`, `details`, `ip_address`, `user_agent`.
- `AuditAction`‑Konstanten: `auth.login`, `job.created`, `invoice.exported`, `export.datev`, `api_key.created`, …
- `get_audit_logs(user_id, action, resource_type, limit, offset)` und `get_audit_stats(days)` aggregieren.
- Endpunkt: `GET /api/audit-log` (`web/app.py:4811`).
- Approval‑Trail: `approval.py` schreibt zusätzlich in `approval_history` und ruft `log_audit`.

### 9.2 Modulare AuditChain (GoBD‑first)

- `modules/.../services/audit_chain.py`:
  - Genesis‑Hash `"0"*64`.
  - Jeder Eintrag enthält `previous_hash` und `entry_hash` über alle Felder (`document_id`, `tenant_id`, `sequence_number`, `event_type`, `status_from`, `status_to`, `actor`, `timestamp`, `details`, `previous_hash`).
  - `chain.verify()` re‑computed alle Hashes → Tamper‑Detection.
- Persistenz: SQLAlchemy‑Tabelle `invoice_events` (Postgres, JSONB für `details`).
- Endpunkte: `GET /api/v1/invoices/{document_id}/events`, `/chain/verify`.
- GoBD‑Anker: `audit_chain.py:7` Doc‑String nennt explizit „Nachvollziehbarkeit, Unveränderbarkeit, Vollständigkeit".

### 9.3 GoBD Evidence Package

- `gobd_evidence.py` (`GoBDEvidenceService`, `EvidenceArtifact`, `EvidenceManifest`):
  - ZIP mit Originaldokument, Audit‑Chain (JSON), Validation‑Report, Manifest mit SHA‑256‑Hashes pro Datei.
  - `gobd_retention_years=10` (`shared/settings.py:28`), Retention‑Until im Manifest.
- Endpunkt: `POST /api/v1/invoices/{document_id}/evidence` (`api/main.py:923`).

> ⚠️ **GoBD/BEG IV:** ADR `docs/adr/adr-erechnung-storage-archiving.md` nennt 8 Jahre für Buchungsbelege (BEG IV ab 2025), die Konfiguration steht aber auf 10 (`gobd_retention_years`). Konflikt bitte juristisch klären.

---

## 10. Approval / Human‑in‑the‑Loop

### 10.1 Legacy `approval.py`

- Status‑Enum `InvoiceStatus` (`pending → assigned → in_review → approved | rejected | on_hold → paid`).
- `ApprovalManager.update_status` mit Audit‑Trail in `approval_history`.
- `ApprovalRule` Dataclass (Schwellbeträge, `required_role`, `auto_approve`, `priority`).
- Endpunkte: `/approvals`, `/approvals/my`, `/approvals/rules`, REST‑APIs für Approve/Reject/Assign/Comment/Bulk (`web/app.py:5552–5825`).
- Frontend: `web/templates/approvals.html`, `approvals_my.html`, `approval_rules.html`.

### 10.2 Modulare State Machine (`state_machine.py`)

- `InvoiceStatus`: `uploaded`, `classified`, `validated`, `validation_failed`, `suggested`, `approved`, `exported`, `archived`, `rejected`.
- `TRANSITION_TABLE` mit deterministischen Regeln, terminalen Zuständen (`archived`, `rejected`) und `requires_actor` für Approval/Reject/Manual‑Override.
- `transition()` raised `TransitionError` bei ungültigen Sprüngen.
- Endpunkt: `POST /api/v1/invoices/{document_id}/transition` (gibt `from_status`, `to_status`, `event_type` zurück).
- Frontend (Next.js, in Repo!): `src/app/dashboard/freigaben/page.tsx` zeigt FlowCheck+‑Style‑Freigabe‑UI mit Schwellbeträgen (€0–100 auto, €100–500 Editor, €500–5k Admin, > €5k Vier‑Augen‑Prinzip) – nutzt `https://app.sbsdeutschland.com/api/erechnung/invoices` und Bearer + `X-Tenant-ID`.
  - ⚠️ Der genannte API‑Pfad `/api/erechnung/*` matcht weder Legacy noch Modular‑Routen direkt – vermutlich vorgesehene Reverse‑Proxy‑Pfadabbildung. Bitte verifizieren.

---

## 11. Security / Auth / RBAC / 2FA

### 11.1 Authentifizierung

| Methode | Quelle | Persistenz |
|---|---|---|
| Email/Password (Session) | `web/app.py:2056` (`POST /login`), Hashing per `hashlib.sha256` (⚠️ Tech Debt: in `database.py:993` und `:1109` SHA‑256 ohne Salt) | SQLite `users` |
| Email/Password (JWT/bcrypt) | `modules/.../auth/jwt_auth.py` | Postgres + bcrypt |
| Google OAuth | `web/routes_oauth.py:18` | Spalten `oauth_*` in `users` |
| Microsoft OAuth | `web/routes_oauth.py:72` | dito |
| 2FA (TOTP) | `two_factor.py` (pyotp + qrcode + Backup‑Codes) | Spalten `totp_*` in `users` |
| API Keys | `api_keys.py` (Prefix `sbs_`, SHA‑256‑Hash) | Tabelle `api_keys` |
| Nexus‑Gateway Static Key | `api_nexus.py:20` (`NEXUS_API_KEY`, **Default fällt auf `"sbs_nexus_secret_2026"` zurück** ⚠️ Security‑Risiko in Code) | – |

### 11.2 RBAC (`rbac.py`)

- Rollen: `owner`, `admin`, `manager`, `member`, `viewer` mit konkreter Permission‑Matrix (gespiegelt in `AGENTS.md`).
- Permissions als Konstanten (`Permission.INVOICE_UPLOAD`, `EXPORT_DATEV`, `BUDGET_EDIT`, `USERS_MANAGE`, `AUDIT_VIEW`, `BILLING_MANAGE`, …).
- Decorators: `require_permission(perm)`, `require_any_permission(*perms)`, `require_admin()`.
- Templates: `get_user_permissions_for_template` liefert Boolean‑Dict für Jinja2 (`perms.can_approve`, …).
- Init in `init_rbac_tables` (`rbac.py:284`) – legt 5 Standardrollen mit JSON‑Permissions an.
- Modular hat einen eigenen, schlankeren `UserAuth` mit `role`‑String (`jwt_auth.py:44`); kein detailliertes Permission‑Modell. ⚠️ RBAC zwischen Legacy und Modular nicht identisch.

### 11.3 Sicherheitsschicht

- Security Headers via `web/app.py:180–202` Middleware (`X-Content-Type-Options`, `X-Frame-Options=SAMEORIGIN`, `Referrer-Policy=strict-origin-when-cross-origin`, `Permissions-Policy`).
- `rate_limiter.py` (Legacy): in‑memory, pro Endpoint‑Klasse (`upload`: 10/min, `auth`: 5/min, `export`: 20/min, `default`: 60/min).
- `web/rate_limiter.py`: SQLite‑Tabelle `rate_limit_usage`.
- `slowapi` (Modular) für JWT‑Routen.
- Session‑Cookie‑Auth via `starlette.middleware.sessions` (Aufrufer in `web/app.py` setzen `request.session`); `shared_auth.py` definiert SSO‑Token‑Bridge zwischen Subdomains (`COOKIE_NAME`, `create_sso_token`, `verify_sso_token`).
- Webhooks / API‑Keys mit Rate‑Limit pro Key (`api_keys.create_api_key`).
- Privacy‑Design: `SECURITY_PRIVACY_DESIGN.md` (Multi‑Tenancy, Datenminimierung, keine Roh‑PDFs in Logs, definierte Log‑Retention).

### 11.4 Bekannte Schwachstellen / Risiken

- ⚠️ **Passwörter mit ungesalzenem SHA‑256** im Legacy (`database.py:1109`).
- ⚠️ **Default Static Token** für Nexus Gateway (`api_nexus.py:20`).
- ⚠️ **Klartext IMAP‑Passwörter** in `email_inbox_config` (`database.py:858`).
- ⚠️ **Hartkodierter Pfad** in `api_nexus.py:18` und `modules/.../api/main.py:6` (`/var/www/invoice-app/.env`) – kein Container‑native Default.
- ⚠️ Fehlender CSRF‑Schutz: keine `CSRFMiddleware` in `web/app.py` sichtbar.
- ⚠️ CORS in Modular‑API auf `allow_origins=["*"]` (`api/main.py:88`) bei `allow_credentials=True` – widerspricht CORS‑Spezifikation.

---

## 12. Bestehende Enterprise‑Funktionen

| Domäne | Funktion | Quelle |
|---|---|---|
| Multi‑Tenancy | `TenantContext` (Modular), `current_org_id` + Org‑Membership (Legacy `organizations.py`) | `shared/tenant/context.py`, `organizations.py`, `web/app.py:2474–2557` |
| Multi‑Product Subscriptions | `invoice` / `contract` / `bundle` Plans, Stripe‑Integration | `multi_product_subscriptions.py`, `web/app.py:2819–3332` |
| OAuth SSO | Google + Microsoft Entra ID | `web/routes_oauth.py`, `web/oauth_config.py` |
| 2FA | TOTP + QR‑Code + Backup‑Codes | `two_factor.py` |
| RBAC | 5 Rollen + Permissions + Decorators | `rbac.py` |
| Audit Trail | Legacy zentral + Modular hash‑chained | `audit.py`, `audit_chain.py` |
| GoBD Evidence | ZIP + Manifest + Hash‑Verifikation | `gobd_evidence.py` |
| KoSIT Validierung | lxml‑Stage + Java‑Binary | `kosit_validator.py`, `docker/kosit-validator` |
| DATEV Export | EXTF v700 + Idempotent Adapter | `datev.py`, `modules/.../services/datev_export.py` |
| MBR | Monthly Business Review (PPTX, 7 Slides, LLM‑optional) | `mbr/`, `web/app.py:993,6902` |
| Email Ingestion | IMAP Inbox Cron | `email_fetcher.py`, `email_scheduler.py`, `scripts/email_poller.py` |
| Notifications | SendGrid + Slack Webhook + Scheduled Reports | `notifications.py`, `enterprise_features.py`, `migration_notifications.sql`, `scheduled_reports.py` |
| Webhooks | CRUD + Event‑Trigger (`invoice.created`, …) | `webhooks.py`, `database.py:103` |
| API Keys | sbs_‑Prefix, Rate‑Limit pro Key | `api_keys.py` |
| Approval Workflow | Multi‑Level + Rules + Bulk | `approval.py`, Templates `approvals*.html` |
| Spend Analytics | Predictive Alerts + Forecast + Snapshots | `spend_analytics.py` |
| Budget | Monatsbudget + Ist/Soll + Alerts | `budget_service.py`, `budget_routes.py` |
| Finance Copilot | Regelbasiert, deterministisch | `finance_copilot.py` |
| Billing Portal | Stripe Customer Portal | `web/app.py:5100` |
| Integrations | Lexoffice, sevDesk Stubs | `lexoffice.py`, `sevdesk.py` |
| Backup/Restore | `backup.py`, `backup.sh`, `restore.sh` | Repo‑Root |
| Sentry Monitoring | Optional via `SENTRY_DSN` | `modules/.../api/main.py:8` |

---

## 13. Kritische technische Schulden

### 13.1 Architektur‑/Code‑Hygiene

- **Doppelte Codebasen**: Legacy (`web/app.py`) und Modular (`modules/.../api/main.py`) implementieren überlappende Funktionen (Auth, Upload, DATEV, XRechnung, Audit, Copilot). Quelle der Wahrheit fehlt.
- **`web/app.py` ist 7021 Zeilen** in einer Datei – Grenzwertig wartbar; Endpunkte mischen HTML‑Rendering, Business‑Logik, Auth und SQL.
- **Backups im Repo**: `web/app.py.backup_*` (mehrere), `_archive/`, `_archive_20260217_194225/`, `_old_code/`, `backup_2025-11-18/`, `backup_20260203_162219/`. `Dockerfile:18` löscht sie zur Build‑Zeit, sie liegen aber im Source‑Tree.
- **Datei‑Zombies im Root**: `0`, `0:`, `19.5:`, `365:`, `=`, `,`, `avg_month`, `cookies.txt`, `database_numbered.txt`, `ervice - Invoice Processing Web Application` (Zeilenfragmente, vermutlich Shell‑Redirect‑Unfälle).
- **Doppelte SKR03‑Konten‑Definitionen**: `datev.py`, `auto_accounting.py`, `kontierung_service.py`, `budget_service.py` – jede mit eigenem Mapping.
- **Doppelte XRechnung‑Generatoren** und **doppelte DATEV‑Exporter** (`datev.py` vs `datev_exporter.py` vs Modular).
- **Doppelte `init_users_table`** in `database.py:959` und `:1073` – beide werden beim Import ausgeführt.
- **Inline‑Imports in Hot Paths** (`from api_nexus import …` in `database.py:103` innerhalb `init_database`, ferner viele `from x import …` mitten in Funktionen).

### 13.2 Datenmodell‑Risiken

- **SQLite und PostgreSQL parallel** (Legacy vs. Modular). Migration auf Postgres ist im Roadmap (`AGENTS.md:Roadmap → PostgreSQL Migration: PLANNED`), aber Code rechnet noch mit SQLite‑Pfad und SQLite‑spezifischer DDL (`PRAGMA table_info`).
- **Schema‑Drift**: `invoices.extracted_data`, `kontierung_historie`, `audit_log`, `api_keys` werden im Code referenziert, ohne dass sie in Alembic‑Migrationen oder in `database.py`‑`CREATE TABLE`‑Blöcken sichtbar sind. ⚠️ Vermutlich durch `ALTER TABLE` zur Laufzeit oder externe Migration.
- **Caching vs. Cache‑Invalidation**: `cache.py` + `invalidate_cache("statistics")` wird in vielen DDL‑Pfaden aufgerufen (auch in `init_database`, was funktional fragwürdig ist).

### 13.3 Sicherheits‑Schulden

- SHA‑256 Passwörter, Default‑API‑Keys, IMAP‑Klartext, fehlender CSRF‑Schutz, CORS `*` mit Credentials – siehe Abschnitt 11.4.

### 13.4 Test‑Abdeckung

- Modulare Tests existieren (`modules/rechnungsverarbeitung/tests/` – `test_api.py`, `test_database.py`, `test_erechnung_hub.py`, `test_invoice_processing_erechnung.py`, `test_kosit_validator.py`).
- Für den Legacy‑Stack (`web/app.py`, `database.py`, `audit.py`, `rbac.py`, `approval.py`, `datev.py`) sind im Repo **keine Tests sichtbar**. ⚠️ Unsicher.

### 13.5 Operative Schulden

- Kein zentrales Migrations‑Tool für SQLite (Alembic nur Postgres).
- Kein CI/CD‑Workflow im Snapshot sichtbar (`.github/workflows/tests.yml` per README erwähnt, ⚠️ Inhalt nicht im Snapshot geprüft).
- Logfile‑Pfad hartkodiert auf `/var/www/invoice-app/logs/app.log` mit Fallback `.runtime-data/logs/app.log` (`web/app.py:71`).

---

## 14. FlowCheck+ Erweiterungspunkte

> Ziel: FlowCheck+ als Finance Control Layer auf bestehenden Bausteinen aufsetzen, ohne den Legacy‑Stack zu blockieren. Empfehlung: **Modular‑Layer als Kanonisches Backend** wählen.

| FlowCheck+ Capability | Bestehender Anker | Erweiterungspfad |
|---|---|---|
| Deterministische Pipeline (received → archived) | `state_machine.InvoiceStateMachine`, `invoice_processing.process_invoice_upload` | Zusätzliche Zustände/Events (`flowcheck_review`, `flowcheck_blocked`) als Erweiterung der `TRANSITION_TABLE`; Integration in modularen Upload‑Flow. |
| Vier‑Augen‑Prinzip / Schwellbetrags‑Approval | Legacy `approval.ApprovalRule` + Frontend `src/app/dashboard/freigaben/page.tsx` | Approval‑Engine in Modular‑API portieren; Schwellbeträge aus `freigaben/page.tsx` als seed (€100/€500/€5k); Pflicht‑Actor + Doppelaktor in State Machine. |
| Hash‑Chain Audit + Evidence | `audit_chain.AuditChain`, `gobd_evidence.GoBDEvidenceService` | FlowCheck+‑Events (Approval, Override, Comment, FlowCheck‑Score) als zusätzliche `event_type`s in chain logging. |
| KoSIT‑Compliance Tooling | `kosit_validator.KoSITValidator`, `docker-compose.yml:kosit-validator` | „FlowCheck+ Compliance Score" aus `ValidationResult.error_count/warning_count` ableiten und persistieren. |
| Idempotenter DATEV‑Export | `modules/.../services/datev_export.DatevExportService` | „Export‑Sperre" durch FlowCheck+ Approval‑Flag, Idempotenzschlüssel pro Run, Retry‑Policy laut ADR. |
| Spend Control / Budget Guards | `spend_analytics.py`, `budget_service.py`, `analytics_service.get_finance_snapshot` | Pre‑Approval‑Hook: bei Budget‑Überschreitung Status `validation_failed` oder zusätzliche Approval‑Stufe erzwingen. |
| Finance Copilot | `finance_copilot.py` (regelbasiert), `mbr/llm.py` (LLM optional) | Antworten an `audit_chain` koppeln (Quelle, KPI‑Snapshot, Zeitfenster) → auditierbarer Copilot. |
| Anomalie‑Erkennung | `modules/.../services/anomaly_detection.py`, `duplicate_detection.py` | Score in `invoice_events.details` schreiben, Approval‑Trigger. |
| Tenant‑Isolation | `shared/tenant/context.TenantContext`, `Invoice.tenant_id` | Pflicht‑Header in allen FlowCheck+‑Routen, Cross‑Tenant‑Leaks via Tests verifizieren. |
| Frontend Dashboard | `src/app/dashboard/freigaben/page.tsx`, `src/app/dashboard/spend/page.tsx` | Direkt als FlowCheck+ Frontend ausbauen, Auth/JWT der Modular‑API binden. |
| Reporting/MBR | `mbr/generator.generate_presentation` (`MBR_USE_LLM=0` Pflicht, laut `AGENTS.md`) | „FlowCheck+ Monthly Compliance Report" als zweite PPTX‑Variante; Wiederverwendung der Template‑Engine. |
| Notifications | `notifications.py`, `sendgrid_mailer.py`, Slack‑Webhook | Approval‑Eskalation und Anomalie‑Alerts an Slack/Email. |
| Webhooks/Integrations | `webhooks.py`, `lexoffice.py`, `sevdesk.py` | Outbound‑Events `flowcheck.invoice.{approved,blocked,exported}`. |

### 14.1 Konkrete Schnittstellen, an denen FlowCheck+ andocken kann

- **Eingang**: `process_invoice_upload` (`invoice_processing.py:24`) – nach `format_classified` und vor `ai_extraction_completed` lässt sich ein FlowCheck+‑Pre‑Hook einfügen.
- **Approval**: `POST /api/v1/invoices/{document_id}/transition` (`api/main.py:788`) – einziger Punkt, der State Machine Transitions auslöst.
- **Audit**: Jeder Eintrag durchläuft `audit_chain.append`; FlowCheck+ kann eigene `event_type` reservieren (`flowcheck_*`).
- **Export**: `POST /api/v1/invoices/{document_id}/datev-export` (`api/main.py:989`) – ideal, um FlowCheck+ Pflicht‑Approval zu prüfen.

---

## 15. Empfohlene Implementierungsreihenfolge

> Reihenfolge mit Ziel „minimaler Risikoaufwand, maximaler Compliance‑Mehrwert". Alle Schritte sind additiv; keine Refaktorierung des Legacy‑Stacks ist Voraussetzung.

1. **Schritt 1 – Fundament fixieren (1–2 Sprints)**
   - Schema‑Drift schließen: alle realen Postgres‑Tabellen in Alembic‑Migrationen aufnehmen (`invoices.extracted_data`, `budget_kategorien`, `monats_budgets`, `kontierung_historie`, `audit_log`, `api_keys`).
   - Kanonisches Schema `CanonicalInvoice` (`erechnung_hub.py:36`) in `db_models.py` als persistente JSONB‑Spalte fest verdrahten.
   - FlowCheck+ Tenant‑Pflicht‑Tests (`pytest`) für alle modularen Routen.

2. **Schritt 2 – State Machine erweitern (1 Sprint)**
   - `TRANSITION_TABLE` um FlowCheck+‑Stufen ergänzen: `validated → flowcheck_screening`, `flowcheck_screening → suggested|flowcheck_blocked`, `suggested → flowcheck_dual_review` (für Beträge ≥ Schwellwert).
   - Pflicht‑Actor + Pflicht‑Co‑Actor (Vier‑Augen) in `transition()` durchsetzen.
   - Audit‑Events `flowcheck_score_assigned`, `flowcheck_blocked`, `flowcheck_override` an `AuditChain` koppeln.

3. **Schritt 3 – FlowCheck+ Score Service (1 Sprint)**
   - Service kombiniert `KoSITValidator.error_count`, `DuplicateDetectionService`, `AnomalyDetectionService`, Budget‑Checks (`budget_service`/`spend_analytics`), Skonto‑Frist, Lieferanten‑Reputation.
   - Schreibt Score + Erklärungs‑JSON in `invoice_events.details`.
   - Endpunkt `GET /api/v1/invoices/{document_id}/flowcheck-score`.

4. **Schritt 4 – Approval‑Engine konsolidieren (1–2 Sprints)**
   - `approval.ApprovalRule` (Legacy) und `state_machine` zu einer einzigen Engine in der modularen API verschmelzen.
   - Schwellwerte aus `src/app/dashboard/freigaben/page.tsx` als initiale Seed‑Konfiguration übernehmen.
   - Endpunkte `POST /api/v1/approvals/{document_id}/{approve,reject,assign,comment,override}`.

5. **Schritt 5 – Export‑Hardening (1 Sprint)**
   - DATEV‑Export blockiert, solange FlowCheck+‑Status ≠ `approved`.
   - Idempotency‑Key + Retry‑Policy aus ADR `adr-datev-integration.md` umsetzen.
   - Evidence Package (`gobd_evidence`) automatisch beim Übergang `exported → archived`.

6. **Schritt 6 – Frontend FlowCheck+ Cockpit (1–2 Sprints)**
   - `src/app/dashboard/freigaben/page.tsx` und `src/app/dashboard/spend/page.tsx` produktiv machen, JWT/Tenant binden.
   - Neue Sub‑Page „FlowCheck+ Score Detail" (Score‑Komponenten, Audit‑Chain‑Auszug, Evidence‑Download).

7. **Schritt 7 – Reporting & Alerts (1 Sprint)**
   - „FlowCheck+ Monthly Compliance Report" als zweite Variante neben MBR.
   - Slack/Email‑Alert‑Routing für Anomalie/Block.
   - Outbound‑Webhooks `flowcheck.invoice.*`.

8. **Schritt 8 – Migration Legacy → Modular (laufend)**
   - Public Routes (`/landing`, `/sicherheit`, `/compliance`, …) bleiben Legacy.
   - Domain‑APIs (`/api/upload`, `/api/datev/*`, `/approvals`) Schritt für Schritt durch Reverse‑Proxy auf Modular umlenken.
   - Legacy‑Tests einführen, bevor Routen abgeschaltet werden.

9. **Schritt 9 – Sicherheits‑Cleanup (parallel)**
   - Passwörter auf bcrypt migrieren, Default‑Static‑Tokens entfernen, IMAP‑Credentials in Vault, CORS schärfen, CSRF einführen.
   - Dieser Schritt ist nicht FlowCheck+‑spezifisch, aber Voraussetzung für jede Compliance‑Aussage.

10. **Schritt 10 – Compliance‑Validierung (laufend)**
    - GoBD/BEG IV Retention (8 vs. 10 Jahre) konsolidieren (`shared/settings.py:28` vs. ADR).
    - DSB / Steuerberater‑Review aller Aussagen in Marketing‑Pages (`web/static/landing/*.html`).
    - KoSIT‑Test‑Suite (`xrechnung-testsuite`) als Fixture in CI integrieren (laut ADR).

---

## Anhang A – Wichtige Konstanten und Konfigurationsschlüssel

| Schlüssel | Quelle | Default |
|---|---|---|
| `INVOICE_DB_PATH` | `database.py:17` | `/var/www/invoice-app/invoices.db` |
| `DATABASE_URL` | `shared/settings.py:17` | `postgresql+psycopg://localhost:5432/sbs_nexus` |
| `KOSIT_VALIDATOR_URL` | `shared/settings.py:30` | `http://localhost:8080` |
| `GOBD_EVIDENCE_DIR` | `shared/settings.py:29` | `./evidence` |
| `GOBD_RETENTION_YEARS` | `shared/settings.py:28` | `10` (⚠️ vs. 8 laut ADR) |
| `DATEV_DEFAULT_SKR` | `shared/settings.py:27` | `SKR03` |
| `MBR_TEMPLATE_PATH` | `mbr/generator.py:11` | `pptx_templates/mbr_template.pptx` |
| `MBR_LLM_MODEL` | `mbr/generator.py:12` | `gpt-4o-2024-08-06` |
| `JWT_SECRET_KEY` | `modules/.../auth/jwt_auth.py:21` | `secrets.token_hex(32)` (⚠️ wechselt bei Restart) |
| `NEXUS_API_KEY` | `api_nexus.py:20` | `sbs_nexus_secret_2026` (⚠️ Default Token) |
| Rate Limits | `rate_limiter.py:79` | upload 10/min, auth 5/min, export 20/min, default 60/min |

## Anhang B – Offene Fragen / Verifikationsbedarf

1. Welche der zwei FastAPI‑Apps läuft auf `app.sbsdeutschland.com`? Beide? Dann an welchen Pfaden?
2. Wer verwaltet das Schema von `audit_log`, `api_keys`, `kontierung_historie` (außerhalb von Alembic und `database.py`)?
3. Frontend `src/app/dashboard/freigaben/page.tsx` ruft `https://app.sbsdeutschland.com/api/erechnung/*` – wo ist dieser Pfad gemappt?
4. `MBR_USE_LLM=0`‑Fallback ist laut `AGENTS.md` Pflicht – im Code (`mbr/generator.py:54`) implementiert; Test‑Coverage ⚠️ unsicher.
5. Konflikt 8 Jahre vs. 10 Jahre Retention (BEG IV vs. `gobd_retention_years`).
6. Tatsächlich aktive Auth‑Schicht für FlowCheck+ Frontend: Sessions, JWT, beides?
7. Welche der Integrationen (Lexoffice, sevDesk, Stripe) sind bereits produktiv im Einsatz, welche sind Stubs?

---

*Ende des Baseline‑Dokuments. Änderungen am Code sind explizit nicht vorgenommen worden.*
