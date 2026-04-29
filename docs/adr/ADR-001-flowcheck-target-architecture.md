# ADR-001: FlowCheck+ Zielarchitektur

> **Status:** Accepted
> **Datum:** 2026-04-29
> **Autor:** Principal Engineer, FlowCheck+ / Finance Control Layer
> **Scope:** Repository `ki-rechnungsverarbeitung` (FastAPI Legacy + Modular Stack)
> **Vorgänger-Dokumente:** `docs/FLOWCHECK_ARCHITECTURE_BASELINE.md`, `docs/architecture/erechnung-hub_baseline.md`, `docs/erechnung/gap_analysis.md`, `docs/adr/adr-erechnung-validation.md`, `docs/adr/adr-datev-integration.md`, `docs/adr/adr-erechnung-storage-archiving.md`

---

## 1. Titel

**FlowCheck+ wird auf der modularen API-Schicht (`modules/rechnungsverarbeitung/`) aufgebaut. Der Legacy-Monolith (`web/app.py`) bleibt stabil, wird aber nicht weiter als Zielarchitektur ausgebaut.**

---

## 2. Status

**Accepted** – ab 2026-04-29 verbindlich für alle FlowCheck+ Arbeitspakete.

Frühere Iterationen (Baseline, Gap-Analyse, drei bestehende ADRs zu Validation, DATEV und Storage/Archiving) bilden die Grundlage. Diese Entscheidung verdichtet sie zu einer übergeordneten Zielarchitektur.

---

## 3. Kontext

Die Architektur-Baseline (`docs/FLOWCHECK_ARCHITECTURE_BASELINE.md`) hat zwei parallel gepflegte Schichten in diesem Repository nachgewiesen:

### 3.1 Legacy-Monolith
- Datei: `web/app.py` (~7000 Zeilen, ~195 Routen)
- Persistenz: SQLite (`database.py`, `invoices.db`, mehrere SQLite-Datenbanken)
- Auth: Sessions + ungesalzenes SHA-256 für Passwörter, OAuth (Google/Microsoft) und 2FA verfügbar
- UI: Jinja2-HTML, produktnah, Marketing- und Self-Service-Pfade
- Stripe Billing, Multi-Product Subscriptions, MBR (PPTX), Webhooks, Email-Ingestion (IMAP)
- Aktiv im Betrieb laut `AGENTS.md`/`CLAUDE.md` auf `app.sbsdeutschland.com`

### 3.2 Modulare API
- Datei: `modules/rechnungsverarbeitung/src/api/main.py` (~50 Routen)
- Persistenz: PostgreSQL via SQLAlchemy + Alembic (`alembic/versions/001_initial.py`)
- Auth: JWT (`modules/.../auth/jwt_auth.py`, bcrypt) + API-Key
- Multi-Tenancy: `shared/tenant/context.TenantContext` (ContextVar) + `X-Tenant-ID`-Header
- Compliance-Bausteine bereits vorhanden:
  - Deterministische State Machine (`state_machine.InvoiceStateMachine`, `TRANSITION_TABLE`)
  - Hash-Chain Audit Trail (`audit_chain.AuditChain`, SHA-256, Genesis-Hash, `verify()`)
  - GoBD Evidence Package (`gobd_evidence.GoBDEvidenceService`)
  - KoSIT-Validator (`kosit_validator.KoSITValidator`, lxml + Java-Binary, Docker-Service)
  - Idempotenter DATEV-Adapter (`datev_export.DatevExportService`)
  - AI Extraction Service (`ai_extraction.AIExtractionService`, Gemini + Claude)
- Per `Dockerfile` als Container-Entrypoint definiert

### 3.3 Befund
- Beide Schichten implementieren überlappende Funktionen (Auth, RBAC, Upload, DATEV-Export, XRechnung, Audit, Copilot).
- Doppelte Codepfade erhöhen Pflegekosten, fragmentieren das Audit-Trail und blockieren ein einheitliches Compliance-Statement.
- Gleichzeitig ist der Legacy-Stack produktiv und enthält Funktionen (Stripe Billing, Marketing-Seiten, Self-Service-UI, MBR-Generator), die nicht in einem Schritt portiert werden können.
- FlowCheck+ als „Finance Control Layer" verlangt deterministische Pipelines, lückenlose Audit-Chain, Tenant-Isolation und kontrollierbares LLM-Verhalten – Eigenschaften, die im Modular-Layer bereits angelegt sind, im Legacy-Layer aber nur teilweise.

### 3.4 Treiber
- **Compliance:** GoBD, BEG IV (E-Rechnungspflicht ab 2025), DSGVO – belegfähige Hash-Chain und Evidence-Package nur im Modular-Layer.
- **Skalierbarkeit:** PostgreSQL + Alembic vs. SQLite-Hot-DDL.
- **Sicherheit:** bcrypt + JWT vs. SHA-256-Sessions.
- **Wartbarkeit:** Zwei kanonische Schemata, drei DATEV-Implementierungen, zwei XRechnung-Generatoren, doppelte `init_users_table` in `database.py` – das ist auf Dauer nicht tragbar.
- **Kommerziell:** FlowCheck+ ist ein Enterprise-Differenzierungsfeature; Enterprise-Kunden erwarten Mandantenfähigkeit, Audit-Evidence und Policy-Kontrolle.

---

## 4. Entscheidung

1. **Zielarchitektur für FlowCheck+ ist die modulare API** unter `modules/rechnungsverarbeitung/`.
2. **Alle neuen FlowCheck+ Kernkomponenten werden in der modularen Schicht entwickelt:**
   - **Control Engine** – orchestriert die deterministische Invoice-Pipeline (Eingang → Format-Klassifikation → Validierung → KI-Extraktion → FlowCheck+ Score → Approval → Export → Archivierung). Aufsetzpunkt: `invoice_processing.process_invoice_upload` und `state_machine.InvoiceStateMachine`.
   - **Policy Engine** – konfigurierbare Regeln (Schwellbeträge, Lieferanten-Whitelist, Budget-Guards, Compliance-Pflichten). Liest aus `budget_service`, `spend_analytics`, `kosit_validator` und schreibt Policy-Verstöße in den Audit-Chain.
   - **Approval Engine** – Multi-Level inkl. Vier-Augen-Prinzip, Schwellbeträge (z. B. €100/€500/€5k aus `src/app/dashboard/freigaben/page.tsx`), Pflicht-Co-Actor in `state_machine.transition()`.
   - **Audit Evidence** – ausschließlich `audit_chain.AuditChain` + `gobd_evidence.GoBDEvidenceService`. Kein paralleles Audit-Schema mehr.
   - **Tenant-Kontext** – ausschließlich über `shared/tenant/context.TenantContext` und `X-Tenant-ID`-Header. Jede neue Route muss tenant-aware sein.
   - **LLM Gateway** – einheitlicher Eintrittspunkt für alle LLM-Aufrufe (Extraction, Klassifikation, Copilot). Konsolidiert `llm_router.py`, `category_ai.py`, `ai_extraction.py` und `mbr/llm.py` hinter einer einzigen Schnittstelle in der modularen Schicht (Provider-Routing, Retry, Cost-Tracking, Audit-Logging, deterministisches Fallback).
3. **Legacy-Stack (`web/app.py` und SQLite-`database.py`) bleibt produktiv stabil**, wird aber **nicht weiter als Zielarchitektur ausgebaut.**
   - Sicherheits- und Bugfixes erlaubt.
   - Keine neuen Domain-Features in `web/app.py`.
   - Keine neuen Tabellen ohne Migrationspendant in der modularen Schicht.
4. **Inkrementelle Migration, kein Big-Bang.** Routen werden einzeln auf den Modular-Layer umgezogen, der Legacy-Stack bleibt während der Migration funktionsfähig.
5. **UI- und Marketing-Routen** (`/landing`, `/sicherheit`, `/compliance`, `/avv`, `/api`, `/referenzen`, `/e-rechnung*`, `/xrechnung`, `/zugferd`) dürfen unverändert im Legacy-Stack verbleiben, bis ein dediziertes Frontend (Next.js, vgl. `src/app/dashboard/`) den Vertrieb übernimmt.
6. **Sicherheitslücken mit hohem Risiko (z. B. ungesalzenes SHA-256 für Passwörter in `database.py`, Default-Token `sbs_nexus_secret_2026` in `api_nexus.py`, Klartext-IMAP-Credentials, CORS `*` mit `allow_credentials=True`) dürfen unabhängig von dieser Migrationsstrategie sofort gepatcht werden.** Sicherheit hat Vorrang vor Architekturreinheit.

### 4.1 Was bleibt im Legacy-Stack (vorerst)
- Marketing-Pages und Public-Trust-Seiten (`/landing`, `/sicherheit`, `/compliance`, `/avv`, `/api`, `/referenzen`).
- Stripe Billing UI und Customer Portal (`/api/checkout/*`, `/api/billing/portal`, `/api/stripe/webhook`).
- MBR-Generator (`mbr/`, `GET /mbr/monthly.pptx`) bis zur Modular-Portierung.
- OAuth-Login-Flows (`web/routes_oauth.py`) – werden später hinter eine gemeinsame Auth-Bridge gestellt.
- Demo-Endpunkte und HTML-Dashboards für Bestandskunden.

### 4.2 Was zwingend in die modulare Schicht gehört
- Invoice-Eingang und alle Status-Transitions.
- DATEV-Export inkl. Idempotenz und Retry (`modules/.../services/datev_export.py`).
- Audit-Trail und Evidence-Pakete.
- KoSIT-Validierung und XRechnung/ZUGFeRD-Generierung.
- LLM-Aufrufe.
- FlowCheck+ Score, Policy-Auswertung, Approval-Engine.
- Outbound-Webhooks für FlowCheck+ Events.

---

## 5. Konsequenzen

### 5.1 Positiv
- **Eine Quelle der Wahrheit** für Compliance-relevante Bausteine (Audit-Chain, Evidence, KoSIT).
- **Mandantenfähigkeit** ist von Anfang an gegeben (TenantContext, `tenant_id`-Spalten, Header-Pflicht).
- **Belegfähigkeit für Enterprise-Kunden** – jeder Statuswechsel wird hash-chain-gesichert protokolliert.
- **Sicherheit** durch bcrypt, JWT, parametrierte SQL über SQLAlchemy.
- **Erweiterbarkeit** – Control/Policy/Approval/LLM-Gateway sind in der modularen Schicht klar trennbar.
- **Operationelle Klarheit** – `Dockerfile` und `docker-compose.yml` zeigen bereits den Container-First-Pfad.

### 5.2 Negativ / Aufwand
- **Doppelte Pflege während der Migrationsphase** – Bugfixes müssen ggf. an zwei Stellen einfließen, solange eine Funktion noch im Legacy-Stack lebt.
- **Datenmodell-Konsolidierung** notwendig (SQLite-`invoices` ↔ Postgres-`invoices` + `invoice_events`). Ein- und Auslesepfade müssen während der Migration eindeutig sein.
- **Frontend-Komplexität** – sowohl Jinja2-Legacy-UI als auch Next.js-Frontend (`src/app/`) müssen zeitweise nebeneinander bestehen.
- **Test-Lücke im Legacy** – im Modular-Layer existieren Tests (`modules/rechnungsverarbeitung/tests/`), im Legacy-Layer kaum. Vor jeder Route-Migration muss ein Smoke-Test abgesichert sein.
- **Schulungsaufwand** – Entwickler müssen den Unterschied „neu = modular" / „nur Wartung = legacy" verinnerlichen.

### 5.3 Auswirkungen auf bestehende ADRs
- `adr-erechnung-validation.md` (KoSIT primary): bleibt gültig und wird im Modular-Layer umgesetzt.
- `adr-datev-integration.md` (EXTF/CSV MVP, idempotent): bleibt gültig, gilt nur für `modules/.../services/datev_export.py`. Legacy-`datev.py` und `datev_exporter.py` werden nicht mehr funktional erweitert.
- `adr-erechnung-storage-archiving.md` (Hash-Chain, Evidence-ZIP, Retention): wird in der Modular-Schicht durch `audit_chain.py` und `gobd_evidence.py` umgesetzt; die Konfiguration `gobd_retention_years` (`shared/settings.py`) ist Single Source of Truth.

---

## 6. Was wir ab jetzt nicht mehr tun

- **Keine neuen Domain-Features in `web/app.py`.** Domain bedeutet hier: Rechnung, Approval, DATEV, KoSIT, Kontierung, Budget, Audit, Score, Policy.
- **Keine neuen Tabellen in `database.py` oder `*.db`** ohne entsprechende Alembic-Migration und Datenmodell in `modules/.../db_models.py`.
- **Keine neuen LLM-Aufrufe direkt aus Legacy-Modulen** (`llm_router.py`, `category_ai.py`, `mbr/llm.py`). Neue LLM-Funktionen gehen über das LLM-Gateway in der modularen Schicht.
- **Keine neuen DATEV-Exporter** neben `modules/.../services/datev_export.py`. Die bestehenden Implementierungen (`datev.py`, `datev_exporter.py`) werden nur noch im Wartungsmodus betrieben.
- **Keine neuen XRechnung/ZUGFeRD-Generatoren** neben `modules/.../services/xrechnung_generator.py`. Legacy-`einvoice.py` und `zugferd.py` werden eingefroren.
- **Keine neuen Auth-Pfade** außerhalb von `modules/.../auth/jwt_auth.py`. Sessions in `web/app.py` werden weiter unterstützt, aber nicht erweitert.
- **Kein direkter SQL-Zugriff auf Postgres aus Legacy-Modulen.** Cross-Layer-Zugriff nur über klar versionierte API-Calls.
- **Kein Speichern sensibler Daten im Klartext** (z. B. IMAP-Passwörter in `email_inbox_config`). Neue Sekrete werden über Secret-Storage referenziert.
- **Keine Erweiterungen der RBAC-Logik in `rbac.py` (Legacy)** – neue Permissions werden im modularen Auth-Modell deklariert und über Adapter abgebildet.
- **Keine neuen Endpunkte ohne Tenant-Kontext** (`X-Tenant-ID` oder gleichwertiger Pflicht-Mechanismus).

---

## 7. Was wir ab jetzt tun

- **FlowCheck+ Features ausschließlich modular umsetzen.** Neue Endpunkte unter `/api/v1/...` in `modules/.../api/main.py`.
- **State Machine als einzigen Kanal für Statuswechsel** verwenden (`state_machine.transition()`), inklusive aller FlowCheck+-Stufen (`flowcheck_screening`, `flowcheck_blocked`, `flowcheck_dual_review`).
- **Audit-Chain für jeden FlowCheck+-Event schreiben.** `event_type`-Konvention `flowcheck.<bereich>.<aktion>` (z. B. `flowcheck.score.assigned`, `flowcheck.policy.violated`, `flowcheck.approval.dual_required`).
- **Evidence-Paket beim Übergang in `archived` oder `exported` automatisch erzeugen.**
- **Tenant-Pflicht-Tests** für jede neue Route schreiben (Cross-Tenant-Leak-Tests).
- **LLM-Gateway als Single Entry Point** für jede KI-Funktion verwenden – mit deterministischem Fallback (`MBR_USE_LLM=0`-Pattern), Cost-Tracking und Audit-Eintrag.
- **Postgres + Alembic als Single Source of Truth** für neue Datenmodelle. Jede neue Spalte / Tabelle erhält eine Alembic-Migration (kein `ALTER TABLE` zur Laufzeit).
- **Frontend-Neuentwicklungen** in der Next.js-App (`src/app/`) gegen die modulare API entwickeln.
- **Sicherheitsdefizite priorisiert beheben** (Passwort-Hashing, Default-Tokens, CORS, IMAP-Credentials, CSRF). Diese Patches sind **nicht migrationsabhängig**.
- **Reverse-Proxy-Pfade einplanen** – z. B. `app.sbsdeutschland.com/api/erechnung/*` (vom bestehenden Frontend-Stub `src/app/dashboard/freigaben/page.tsx` adressiert) künftig auf die modulare API mappen.
- **Dokumentation aktualisieren**: Jede Route-Migration zieht eine Aktualisierung in `docs/FLOWCHECK_ARCHITECTURE_BASELINE.md` und ggf. einen neuen ADR nach sich.

---

## 8. Migrationsprinzipien

1. **Inkrementell, route-orientiert.** Jede Migration umfasst eine logische Route oder einen Endpoint-Cluster, nicht den ganzen Stack.
2. **Strangler-Fig-Muster.** Neue Implementierung in der modularen Schicht bauen, hinter einem Reverse-Proxy / Feature-Flag aktivieren, Legacy-Pfad erst entfernen, wenn Smoke-Tests + Audit-Logs bestätigen, dass die neue Route stabil ist.
3. **Kein Datenverlust.** Vor jeder Migration: Backup (`backup.py`, `backup.sh`) + dokumentierter Restore-Pfad. Schema-Änderungen ausschließlich via Alembic.
4. **Compliance-Erhalt.** Jeder migrierte Endpoint muss mindestens den bisherigen Audit-Detailgrad (Legacy `audit.log_audit`) liefern. Idealerweise ergänzt um Hash-Chain-Eintrag.
5. **Tenant-First.** Bevor eine Route migriert wird, ist der Tenant-Schlüssel zu definieren (heute `current_org_id` ↔ `tenant_id`).
6. **Test-Pflicht.** Vor Route-Migration: Smoke-Test im Legacy-Stack festschreiben. Nach Migration: identischer Smoke-Test gegen die modulare API. Beides bleibt im CI bis zur Legacy-Abschaltung.
7. **Idempotenz erzwingen.** Schreiboperationen (Upload, Export, Approval) erhalten Idempotency-Keys (vgl. `adr-datev-integration.md`).
8. **Feature-Flags.** Neue FlowCheck+-Funktionen werden hinter Flags ausgerollt (`FLOWCHECK_<feature>=on|off`), Default `off` bis Akzeptanztest.
9. **Observability.** Jeder neue Code-Pfad in der modularen Schicht muss strukturiertes Logging + Sentry-Handler nutzen (`modules/.../api/main.py:8`).
10. **Ein Modul, eine Verantwortung.** Bei der Migration werden Legacy-Mehrfachimplementierungen (drei DATEV-Exporter, zwei XRechnung-Generatoren, zwei Auth-Pfade) auf je eine modulare Variante reduziert.
11. **Keine stillen Datenpfade.** Wenn ein Legacy-Pfad weiterhin schreibt (z. B. SQLite-`invoices`), muss der modulare Pfad ihn lesen oder ein dokumentiertes ETL existieren – nicht beides parallel.
12. **Backward-Kompatibilität an der API-Außenseite.** Externe Konsumenten (Webhooks, API-Keys, Customer-Integrationen) sehen die Migration nicht – Pfade bleiben stabil oder werden über versionierte Routen (`/api/v1/...`) gepflegt.

---

## 9. Risiken

| Risiko | Auswirkung | Mitigation |
|---|---|---|
| **Datenmodell-Drift** zwischen SQLite-Legacy und Postgres-Modular | Inkonsistente Reports, fehlende Audit-Spuren | Schritt 1 der Roadmap (Schema-Drift schließen, Alembic vervollständigen). Single-Write-Pfad pro Entität. |
| **Doppelte Pflege** (Bugfix in Legacy + Modular) | Höhere Wartungskosten, Drift | Klare Domain-Grenzen: neue Domain ausschließlich modular. Legacy nur Wartung. |
| **Schleichendes Wachstum von `web/app.py`** | Migrationspfad wird länger | „No new domain features in legacy"-Policy in Code-Review-Checkliste. |
| **Tenant-Isolation-Lecks** während Migration | Datenschutz- und Compliance-Risiko | Tenant-Tests Pflicht (CI), `X-Tenant-ID`-Header strikt validieren, Default-Tenant `"default-tenant"` (`shared/tenant/context.py`) im Produktivpfad ersetzen. |
| **Legacy-Auth (SHA-256, Default-Token)** in Produktion | Account-Übernahme, Datenleck | Sofort patchen, unabhängig von Migrationsphase. Migration auf bcrypt/JWT verpflichtend. |
| **Zwei Audit-Pfade** (`audit.log_audit` + `audit_chain.append`) | Lücken im Compliance-Nachweis | Jeder migrierte Endpoint schreibt mindestens in `audit_chain`. Legacy-`audit_log` wird beibehalten, bis vollständig abgelöst. |
| **LLM-Mehrfachpfade** (`llm_router.py`, `category_ai.py`, `ai_extraction.py`, `mbr/llm.py`) | Inkonsistentes Modellverhalten, doppelte Kosten, unklare Auditierbarkeit | LLM-Gateway als zentraler Eintrittspunkt; alte Pfade sukzessive auf das Gateway umlenken. |
| **Container vs. systemd Diskrepanz** (`Dockerfile` startet Modular, `AGENTS.md`/`CLAUDE.md` beschreiben Legacy via systemd) | Unklarer Produktiv-Stack | Klären, welcher Pfad live ist; ⚠️ offene Frage. Reverse-Proxy-Konfiguration explizit dokumentieren. |
| **Fehlende Tests im Legacy-Stack** | Regressionsrisiko bei Migration | Vor Migration jeweils Smoke-Tests einführen; CI-Pflicht. |
| **MBR-Generator-Abhängigkeit** (`MBR_USE_LLM=0` Pflichtfallback) | Aussagepflicht in Verträgen | Fallback bei Migration zwingend erhalten. Tests im CI (⚠️ aktuell unklar, ob abgedeckt). |
| **Stripe/Billing-Abhängigkeit im Legacy** | Umsatz-kritische Pfade | Migration nur mit Stripe-Sandbox-Test und Doppelschreibung in der Übergangsphase. |

---

## 10. Rollback / Revision

### 10.1 Rollback-Strategie pro Migrationseinheit
- Jede Route-Migration läuft hinter einem Feature-Flag (`FLOWCHECK_<feature>` oder `LEGACY_ROUTE_<route>=on`).
- Bei kritischen Fehlern: Flag flippen → Legacy-Endpoint übernimmt wieder.
- Datenpfade müssen dual-read-fähig sein (modulare API liest auch Legacy-Daten der Übergangsphase), bis das Flag nach Stabilität entfernt wird.
- Für Schema-Migrationen: jede Alembic-Migration enthält eine `downgrade`-Implementierung; Backup vor jedem `alembic upgrade head` Pflicht.

### 10.2 Revision dieses ADRs
Dieser ADR ist zu überarbeiten oder abzulösen, wenn:
- der Legacy-Stack vollständig durch die modulare Schicht abgelöst ist (dann wird ADR-001 in einen Abschluss-ADR überführt),
- ein Plattformwechsel beschlossen wird (z. B. weg von FastAPI auf einen anderen Stack),
- regulatorische Vorgaben (GoBD, BEG IV, DSGVO-Folgen) eine andere Trennung verlangen,
- eine wirtschaftliche Entscheidung (Verkauf, Spin-off) eine andere Code-Zugehörigkeit erzwingt.

### 10.3 Vollständiger Rollback (worst case)
- Falls die modulare Schicht nicht produktionsfähig ist: Legacy bleibt der primäre Pfad, modulare Routen werden auf `503` geschaltet (Feature-Flag).
- Datenkonsistenz wird über Alembic-Downgrade + SQLite-Restore (`backup.sh`/`restore.sh`) wiederhergestellt.
- ADR-Status wird auf `Superseded` gesetzt; ein neuer ADR dokumentiert den abweichenden Pfad.

---

## Offene Fragen (⚠️ markiert)

1. **Welche der zwei FastAPI-Apps läuft heute auf `app.sbsdeutschland.com`?** `Dockerfile` startet Modular, `AGENTS.md`/`CLAUDE.md` beschreiben Legacy via systemd. Bestätigung erforderlich, bevor Reverse-Proxy-Mapping definiert wird.
2. **Welcher Tenant-Schlüssel ist kanonisch?** `users.current_org_id` (Legacy) ↔ `tenant_id` (Modular). Mapping-Tabelle und Migrations-Skript bislang nicht im Repo.
3. **Wo lebt das Schema von `audit_log`, `api_keys`, `kontierung_historie`?** Diese Tabellen werden von Code referenziert, sind aber weder in `database.py` noch in Alembic vollständig deklariert (siehe Baseline §5.2).
4. **Frontend-Pfad `app.sbsdeutschland.com/api/erechnung/*`** (in `src/app/dashboard/freigaben/page.tsx`): zu welcher Backend-Schicht zeigt der Reverse-Proxy?
5. **GoBD-Retention 8 vs. 10 Jahre** (BEG IV vs. `shared/settings.py:gobd_retention_years=10`): juristische Bewertung erforderlich.
6. **MBR-LLM-Fallback** (`MBR_USE_LLM=0`): aktuell nicht eindeutig durch automatisierte Tests abgedeckt – Test-Coverage prüfen.
7. **Stripe Billing**: bleibt mittelfristig im Legacy oder migriert in ein eigenes Billing-Modul? (Beeinflusst Auth-Bridge und Webhook-Migration.)
8. **OAuth-Bridge**: wo werden Google-/Microsoft-Sessions gegen JWTs getauscht, wenn das Frontend künftig direkt gegen die modulare API spricht?

---

## Referenzen
- `docs/FLOWCHECK_ARCHITECTURE_BASELINE.md`
- `docs/architecture/erechnung-hub_baseline.md`
- `docs/erechnung/gap_analysis.md`
- `docs/adr/adr-erechnung-validation.md`
- `docs/adr/adr-datev-integration.md`
- `docs/adr/adr-erechnung-storage-archiving.md`
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `SECURITY.md`, `SECURITY_PRIVACY_DESIGN.md`
- `Dockerfile`, `docker-compose.yml`, `alembic/versions/001_initial.py`

---

*Ende ADR-001. Keine Codeänderungen, keine Dependencies, keine bestehenden Dateien angepasst.*
