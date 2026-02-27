# SBS Nexus Finance – E‑Rechnungs‑Hub Baseline (Phase 0)

## 1) Repo-Kontext & Tech-Stack

- **Monolithischer Hauptdienst:** `web/app.py` (FastAPI) mit sehr vielen Endpunkten (Upload, Auth, Org, Audit, Export, MBR, Billing).  
- **Neuer modularer API-Pfad:** `modules/rechnungsverarbeitung/src/api/main.py` (tenant-aware Upload/List/Get/Events).  
- **Datenhaltung:**
  - Legacy: SQLite (`database.py`, `web/app.py`) mit `invoices.db`.
  - Modular: SQLAlchemy Session in `shared/db/session.py` (PostgreSQL-URL als Default).
- **Auth/RBAC:** Session-basierte Auth + Rollen/Org-Endpunkte in `web/app.py`; zusätzliche Tenant-Context-Mechanik in `shared/tenant/context.py`.
- **Test-Setup:** Pytest im Modulpfad `modules/rechnungsverarbeitung/tests`.
- **Migration-Setup:** Kein klarer Alembic- oder Flyway-Stack gefunden; Schemaänderungen sind teils direkt in Python/SQL-Skripten.

## 2) Architekturkarte (Ist)

## 2.1 Module/Services
- **Web/API Layer:**
  - `web/app.py` als zentrale Runtime.
  - `modules/rechnungsverarbeitung/src/api/main.py` als neuerer API-Entry.
- **Invoice Processing:**
  - `modules/rechnungsverarbeitung/src/invoices/services/invoice_processing.py` (Upload-Lifecycle mit Event-Logging, Placeholder-Verarbeitung).
  - Legacy-Verarbeitung/Extraktion in Root-Modulen (`database.py`, OCR/Parsing-Utilities).
- **E-Rechnung:**
  - `einvoice_import.py` (Import/Parsing XRechnung/ZUGFeRD/CII/UBL-ähnlich).
  - `einvoice.py` (XRechnung-Generierung).
- **DATEV:**
  - `datev.py` (EXTF/CSV + XML-orientierte Exportlogik, Konfigmodelle).
  - `datev_exporter.py` (zusätzlicher DATEV-Exporter, ältere Variante).
- **Audit/Compliance:**
  - `audit.py` + Audit-Endpunkte in `web/app.py`.
- **Analytics/MBR:**
  - `mbr/*` + MBR-Endpoint in `web/app.py`.

## 2.2 Auth/RBAC & Tenant-Modell
- Session-Login (`/login`, `require_login`) in `web/app.py`.
- Organisations-/Mitglieder-Endpunkte (`/api/organizations/*`) vorhanden.
- Tenant-Isolation im modularen Pfad via `X-Tenant-ID` Header + `TenantContext`.
- **Risiko:** Architektur ist hybrid (session/user_id + tenant_id) und dadurch fehleranfällig bei zukünftigen Cross-Module-Flows.

## 2.3 Invoice-Pipeline (Ist)
1. Upload (`/api/upload` bzw. `/invoices/upload`).
2. Speicherung von Job/Invoice-Metadaten.
3. Extraktion/Klassifizierung (teils placeholder, teils legacy OCR/Parser).
4. Export (DATEV, SEPA, ZIP, XRechnung/ZUGFeRD Export-Endpunkte).
5. Audit-Events vorhanden, aber nicht als einheitliche Event-Sourcing-Kette.

## 2.4 Storage, Queue/Worker, Audit, Integrationslayer
- **Storage:** primär lokale DB + Dateipfade.
- **Queue/Worker:** keine klare dedizierte Queue (Celery/RQ/Kafka nicht sichtbar).
- **Audit:** vorhanden, aber verteilt und teilweise endpoint-nah statt domänenzentral.
- **Integrationen:** DATEV, Email-Konfiguration, Webhooks/Keys vorhanden.

## 3) Reuse-Bausteine für E‑Rechnungs‑Hub MVP

- **Invoice Ingestion:** Upload-Endpoints und Metadatenpersistenz vorhanden.
- **OCR/Extraktion:** vorhandene Parser-/Extraktionsmodule plus E-Invoice Parser (`einvoice_import.py`).
- **Kontierungsvorschläge:** `auto_accounting.py` inkl. Rule-based + optional LLM-Fallback.
- **Approval/Workflow:** Basale Workflows/Statusübergänge vorhanden, aber fragmentiert.
- **DATEV Export:** Substanzielle Exportlogik in `datev.py` vorhanden.
- **Audit Logging:** `audit.py` + Audit-API in `web/app.py`.
- **Archiv/Export:** ZIP/Comprehensive Export-Endpunkte als Basis für Evidence Package.

## 4) Regulatorischer Referenzrahmen (für E‑Rechnung-Hub)

- **Definition E-Rechnung ab 01.01.2025:** strukturierte Formate; PDF dann „sonstige Rechnung“ (BMF FAQ).  
- **Übergangsregeln bis 31.12.2026/2027 inkl. <=800.000 € und EDI-Übergang:** BMF FAQ + IHK.  
- **Zulässige Formate:** XRechnung + ZUGFeRD >=2.0.1 (ohne MINIMUM/BASIC-WL) laut BMF FAQ.  
- **Aufbewahrung:** 8 Jahre für Buchungsbelege ab 01.01.2025 (BEG IV, BGBl. 2024 I Nr. 323), andere Dokumente teils 10 Jahre (IHK/BGBl).

Referenzen:
- BMF FAQ E-Rechnung: https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
- IHK Überblick: https://www.ihk.de/ (regionale IHK-Seiten zur E-Rechnungspflicht)
- BGBl BEG IV: https://www.bgbl.de/
