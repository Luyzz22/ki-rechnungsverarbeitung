# FlowCheck+ Security Hotfix Plan

> **Status:** Draft (read-only Analyse, keine Codeänderungen).
> **Datum:** 2026-04-29
> **Verfasser:** Principal Engineer / Security Reviewer, FlowCheck+
> **Bezug:** `docs/adr/ADR-001-flowcheck-target-architecture.md`, `docs/FLOWCHECK_ARCHITECTURE_BASELINE.md`, `SECURITY.md`, `SECURITY_PRIVACY_DESIGN.md`.
> **Scope:** ausschließlich Security-relevante Konfigurationen, Auth-Flows, Secret-Handling.
> **Hinweis:** Keine Secrets ausgegeben. Findings, die einen konkreten Klartext-Wert betreffen, verweisen lediglich auf Datei + Zeile; der Wert selbst wird nicht zitiert.

---

## Methodik

- Quellen: `web/app.py`, `modules/rechnungsverarbeitung/src/api/main.py`, `modules/rechnungsverarbeitung/src/auth/jwt_auth.py`, `modules/rechnungsverarbeitung/src/auth/rate_limiter.py`, `database.py`, `shared_auth.py`, `api_nexus.py`, `shared/settings.py`, `shared/tenant/context.py`, `web/routes_oauth.py`, `config.yaml`, `config.yaml.example`, `docker-compose.yml`, `.gitignore`, `cookies.txt`.
- Prüftiefe: Konfigurations- und Auth-Pfade plus Cross-Cuts (Logging, Secrets, Header). Keine vollständige Code-Beschau aller ~120 Python-Dateien; Aussagen zu Routen-Coverage stützen sich auf Grep-Stichproben.
- Severity-Skala: `critical` (Account-Übernahme, Mandanten-Leak, RCE), `high` (Auth-Bypass, Privilege Escalation, Compliance-Verletzung), `medium` (Defense-in-Depth-Lücken), `low` (Hygiene).
- Migrationsunabhängigkeit: Ein Fix gilt als „migrationsunabhängig", wenn er ohne Architekturentscheidung sofort umgesetzt werden kann (vgl. ADR-001 §4.6).

---

## Findings

### F-01 — Modulare API verlangt nur `X-Tenant-ID` Header, kein Auth-Nachweis

| Feld | Wert |
|---|---|
| **ID** | F-01 |
| **Severity** | **critical** |
| **Datei/Funktion** | `modules/rechnungsverarbeitung/src/api/main.py` `_require_tenant` (`:118`), Geltungsbereich: `upload_invoice` (`:182`), `download_invoice_file` (`:206`), `generate_xrechnung` (`:229`), `validate_xrechnung`, `transition` (`:788`), `datev_export` (`:989`), `audit-log` (`:661`), und ~40 weitere `/api/v1`-Routen |
| **Risiko** | Jede HTTP-Anfrage mit beliebigem `X-Tenant-ID`-Header erhält Zugriff auf den entsprechenden Mandanten. Es findet **keine Authentifizierung** und **keine Autorisierung** statt. Effektiv: vollständige Cross-Tenant-Daten- und Schreibrechte über das öffentliche Internet, sobald die App erreichbar ist. Verstoß gegen DSGVO Art. 32, GoBD-Nachvollziehbarkeit und Mandantentrennung. Nur 11 von ~50 Endpunkten verwenden `Depends(get_current_user)`. |
| **Minimaler Fix** | Pflicht-Dependency `Depends(get_current_user)` in jeder `/api/v1`-Route ergänzen und Tenant-ID **aus dem Token** ableiten (nicht aus dem Header). `_require_tenant` muss prüfen, dass `header_tenant == token.tenant_id`; Mismatch → `403`. Default `"default-tenant"` aus `shared/tenant/context.py:23` für Produktivpfad deaktivieren. |
| **Testplan** | (a) Request ohne Bearer-Token → `401`; (b) Bearer-Token Tenant A + `X-Tenant-ID: B` → `403`; (c) gültige Kombination → `200`; (d) `/api/v1/health` bleibt offen. |
| **Rollback** | Feature-Flag `FLOWCHECK_REQUIRE_AUTH=on/off`. Bei Akut-Problem auf `off` umstellen, Service bleibt funktional, Risiko persistiert. |
| **Migrationsunabhängig?** | **Ja** – Fix gehört in die modulare Schicht, ist aber unabhängig von Legacy-Migrations-Schritten möglich. |

---

### F-02 — Nexus-Gateway hat hartkodierten Default-API-Key im Code

| Feld | Wert |
|---|---|
| **ID** | F-02 |
| **Severity** | **critical** |
| **Datei/Funktion** | `api_nexus.py:20` `NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "<default literal>")`, genutzt in `verify_api_key` (`api_nexus.py:65`) für `POST /api/nexus/process-invoice` und `/classify-document` |
| **Risiko** | Wird die Env-Variable nicht gesetzt, akzeptiert die API einen öffentlich im Repo stehenden Static-Token als gültige Authentifizierung. Liefert anschließend `is_admin: True` (`api_nexus.py:67`). Verstoß gegen § „Secrets Management" in `AGENTS.md`/`CLAUDE.md`. Token wird per `Authorization`-Header **ohne `Bearer`-Prefix** verglichen, also unverschlüsselter Klartext-Vergleich. |
| **Minimaler Fix** | (a) Default-Wert entfernen, fehlender Env → `RuntimeError` beim Import; (b) Vergleich auf `secrets.compare_digest` umstellen (Timing-Attack-Schutz); (c) Default-Token rotieren und via Env-Variable bereitstellen. |
| **Testplan** | (a) Start ohne `NEXUS_API_KEY` → klarer Startfehler; (b) Request ohne Token → `401`; (c) Request mit altem Default-Token → `401`; (d) Request mit neuem Token → `200`. |
| **Rollback** | Env-Variable kann sofort zurückgesetzt werden; Default-Pfad bleibt deaktiviert. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-03 — Ungesalzenes SHA-256 Passwort-Hashing im Legacy-Pfad

| Feld | Wert |
|---|---|
| **ID** | F-03 |
| **Severity** | **critical** |
| **Datei/Funktion** | `database.py:995, 1019, 1109, 1133` (`create_user`/`verify_user` zweimal definiert), `web/app.py:1473` (`/api/admin/users` POST). Kontrast: `database.py:1731` und `modules/.../auth/jwt_auth.py:50` nutzen bcrypt. |
| **Risiko** | SHA-256 ohne Salt ist offline brute-forcebar (Rainbow Tables, GPU). Bei Datenbank-Leak werden Klartext-Passwörter in Stunden bis Sekunden rekonstruiert. Account-Übernahme inkl. Admin (`is_admin`-Spalte). |
| **Minimaler Fix** | (a) `verify_user` mit Doppelpfad: erst bcrypt prüfen (Pfeffer-Migration), bei SHA-256-Match Passwort beim nächsten Login automatisch zu bcrypt re-hashen; (b) `create_user` ausschließlich bcrypt; (c) Password-Reset (`web/app.py:4131` ruft `reset_password` mit bcrypt – bereits korrekt). |
| **Testplan** | (a) Bestandskonto mit altem SHA-256-Hash kann sich einloggen, danach steht bcrypt-Hash in DB; (b) Neues Konto wird sofort mit bcrypt angelegt; (c) DB-Dump-Probe: keine 64-stelligen Hex-Hashes mehr nach Migration. |
| **Rollback** | Migration ist additiv (Hashes werden lazily ersetzt). Kein Schema-Bruch; Rollback nur durch Wiederherstellung aus Backup nötig. |
| **Migrationsunabhängig?** | **Ja** – betrifft ausschließlich Legacy-DB, kein Architekturkonflikt. |

---

### F-04 — Klartext-Passwörter und IMAP-Credentials im Repo / in der DB

| Feld | Wert |
|---|---|
| **ID** | F-04 |
| **Severity** | **critical** |
| **Datei/Funktion** | (a) `config.yaml.example:46–53` und `config.yaml:46–53` enthalten Klartext-Werte für `notifications.email.username` und `password` (Gmail App Password), (b) `database.py:859` Tabelle `email_inbox_config` speichert IMAP-Passwort als `TEXT`, (c) `cookies.txt` ist im Repo (leer, aber als Pfadkonvention beibehalten). Zusätzlich `web/app.py:1722` Default `SESSION_SECRET_KEY="fallback-change-me"`, `shared_auth.py:18` Default `JWT_SECRET="<sbs-deutschland-shared-secret-2025>"`. |
| **Risiko** | Im Repo liegende Credentials sind Quasi-öffentlich. App-Password kompromittiert Mail-Versand und potenziell die zugehörige Mailbox. IMAP-Klartext erlaubt jedem mit DB-Lesezugriff (Backup-Dumps, Replikate, Audit-Tools) Vollzugriff auf Kunden-Postfächer. Statische Default-Secrets erlauben JWT-Signierung durch jeden, der Zugriff auf den Code hat. |
| **Minimaler Fix** | (a) `config.yaml` aus dem Repo entfernen (es ist bereits in `.gitignore` für künftige Commits, vgl. `.gitignore:124`, aktuell aber gespeichert), `config.yaml.example` von Klartext befreien (Platzhalter `<SET-IN-VAULT>`); (b) **App-Password und JWT-Secret rotieren** (außerhalb von Code, in Secret Storage); (c) IMAP-Passwörter via Fernet/age symmetrisch verschlüsselt speichern, Schlüssel via Env-Variable; (d) Default-Werte aus `shared_auth.py:18` und `web/app.py:1722` entfernen, `RuntimeError` bei Fehlen. |
| **Testplan** | (a) `git grep -E "smtp|imap|password|secret"` liefert keine Klartext-Strings im Repo; (b) Start ohne `SESSION_SECRET_KEY`/`JWT_SECRET` → klarer Fehler; (c) Lese-Zugriff auf `email_inbox_config` zeigt nur Ciphertext. |
| **Rollback** | Schlüsselrotation hat keinen technischen Rollback (Schlüssel bleibt rotiert). Code-Defaults können temporär wieder eingebaut werden, Wert sollte aber neu generiert sein. |
| **Migrationsunabhängig?** | **Ja**, MUSS sofort. |

---

### F-05 — JWT-Secret hat ephemeren Default

| Feld | Wert |
|---|---|
| **ID** | F-05 |
| **Severity** | **high** |
| **Datei/Funktion** | `modules/rechnungsverarbeitung/src/auth/jwt_auth.py:21` `SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))`. |
| **Risiko** | Ohne gesetzte Env-Variable wird beim Start ein zufälliger Schlüssel generiert. Dadurch werden bei jedem Restart alle bestehenden Tokens ungültig (Operational), zudem unterscheiden sich Schlüssel zwischen mehreren Instanzen → JWTs sind nicht horizontal-skalierungstauglich. Stützt parallel `shared_auth.py:18` mit eingecheckter Default-Konstante – noch riskanter. |
| **Minimaler Fix** | Default entfernen; bei fehlender Variable klar abbrechen. Schlüssel verpflichtend per Env / Secret Manager bereitstellen, gleicher Wert für alle Instanzen. |
| **Testplan** | (a) Start ohne `JWT_SECRET_KEY` → Fail Fast; (b) Token aus Pod A in Pod B verifizierbar (Key identisch). |
| **Rollback** | Schlüssel kann jederzeit per Env neu gesetzt werden. Aktive Sessions werden invalidiert. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-06 — CORS `allow_origins=["*"]` mit `allow_credentials=True`

| Feld | Wert |
|---|---|
| **ID** | F-06 |
| **Severity** | **high** |
| **Datei/Funktion** | `modules/rechnungsverarbeitung/src/api/main.py:86–92`. Zum Vergleich: `web/app.py:2798–2800` definiert eine Whitelist (`https://sbsdeutschland.com`, `https://app.sbsdeutschland.com`, …). |
| **Risiko** | Browser ignorieren `*` zwar bei `Access-Control-Allow-Credentials: true`, aber FastAPI sendet `*` und Credentials-Header gleichzeitig — uneinheitliches Verhalten. Bei einigen Clients (Custom-Fetch, Curl-Frontends, Webviews) lassen sich Cookies/Auth-Header über fremde Origins missbrauchen. Zudem führt es zu CSRF-Bypass-Vektoren, sobald Cookies eingeführt werden (z. B. SSO-Cookie aus `shared_auth.py`). |
| **Minimaler Fix** | Whitelist analog zu Legacy konfigurieren: explizite Liste aus `https://app.sbsdeutschland.com`, `https://sbsnexus.de`, ggf. lokale Dev-Origins. `allow_credentials=True` nur kombinieren, wenn Origin gewhitelistet ist. Optional: Wildcard nur bei `dev`-Profil zulassen. |
| **Testplan** | (a) `OPTIONS`-Preflight von Whitelisted Origin → `Access-Control-Allow-Origin: <origin>`; (b) von fremder Origin → kein CORS-Header. |
| **Rollback** | Whitelist temporär aufweiten; nicht jedoch Rückkehr zu `*` mit Credentials. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-07 — Sensible Tokens werden in Logs ausgegeben

| Feld | Wert |
|---|---|
| **ID** | F-07 |
| **Severity** | **high** |
| **Datei/Funktion** | `web/app.py:4044, 4080` (`logger.info("🔐 [RESET-CONFIRM-…] called with token=%s", token)`). Gleicher Pattern in mehreren Backup-Versionen (`backup_20260203_162219/app.py`, `web/app_before_finance_copilot_20251130_025356.py`). |
| **Risiko** | Password-Reset-Tokens (`secrets.token_urlsafe(32)`, vgl. `database.py:1671,1760,1822`) gelangen in `journalctl` und potenziell in `/var/log/nginx/access.log`. Wer Log-Read-Rechte hat (Operations, SREs, Backups, Sentry mit `send_default_pii`-Toggle) kann Account-Resets stehlen. |
| **Minimaler Fix** | Token in den betroffenen `logger.info`-Aufrufen redigieren (nur Hash/Prefix loggen, z. B. `token=%s…`, max 8 Zeichen). Generelles Logging-Filter (`logging.Formatter`-Filter, der Felder `token`, `password`, `secret`, `api_key`, `authorization` redigiert) zentral einbauen. |
| **Testplan** | (a) Reset-Flow ausführen → Logs enthalten kein vollständiges Token; (b) gezielter Log-Filter-Unit-Test mit Beispiel-Strings. |
| **Rollback** | Filter ist additiv – kann jederzeit abgeschaltet werden. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-08 — Kein CSRF-Schutz auf den Legacy-HTML-Routen

| Feld | Wert |
|---|---|
| **ID** | F-08 |
| **Severity** | **high** |
| **Datei/Funktion** | `web/app.py` (Sessions via `SessionMiddleware:1722`), gesamte HTML-/Form-basierte Pfade (`/login`, `/register`, `/api/admin/users`, `/api/keys`, `/api/webhooks`, `/api/2fa/*`, …). Suchergebnis: keinerlei CSRF-Middleware, kein `X-CSRF-Token`-Header, kein Same-Origin-Check sichtbar. |
| **Risiko** | Cookie-basierte Session lässt sich von beliebiger Origin per `<form>` oder `fetch` mit `credentials: include` ausnutzen. Bei `/api/admin/users`, `/api/keys`, `/api/webhooks` kann ein Angreifer Admin-Aktionen im Namen eines authentifizierten Opfers auslösen. SSO-Cookie aus `shared_auth.py:84` ist `samesite=lax`, was nur Top-Level-GET-Navigationen schützt – `POST`/`PUT`/`DELETE` aus Drittseiten bleiben verwundbar. |
| **Minimaler Fix** | (a) `starlette-csrf` o. ä. Middleware aktivieren oder eigene Implementierung mit doppeltem `csrftoken`-Cookie + Hidden-Field. (b) SameSite-Cookie hochstufen auf `strict` für reine Admin-Endpunkte. (c) Cross-Origin-POST nur erlauben, wenn JWT-Authorization-Header gesetzt ist (kein Cookie). |
| **Testplan** | (a) `POST /api/keys` ohne CSRF-Token → `403`; (b) `POST` mit gültigem Token → `200`; (c) Cross-Origin-Form-Submit ohne Token → `403`. |
| **Rollback** | Middleware kann per Feature-Flag temporär abgeschaltet werden, bis Frontends migrieren. |
| **Migrationsunabhängig?** | **Ja** – betrifft Legacy. Modular-API ist Token-basiert; nach Behebung von F-01 ist sie immun, solange keine Cookies eingeführt werden. |

---

### F-09 — Default Session-Secret im Legacy

| Feld | Wert |
|---|---|
| **ID** | F-09 |
| **Severity** | **high** |
| **Datei/Funktion** | `web/app.py:1722` `SessionMiddleware(secret_key=os.getenv('SESSION_SECRET_KEY', 'fallback-change-me'), domain='.sbsdeutschland.com')`. |
| **Risiko** | Wird die Variable nicht gesetzt, läuft die Session-Signierung mit dem öffentlichen Default. Angreifer kann Session-Cookies fälschen, vollständiger Account-Bypass inklusive `is_admin`. |
| **Minimaler Fix** | Default entfernen (Fail-Fast), Secret im Secret-Storage halten, gleiches Secret in allen Instanzen, dokumentierter Rotationsplan (mit Doppel-Key-Phase, falls `SessionMiddleware` Multi-Key unterstützt). |
| **Testplan** | (a) Start ohne `SESSION_SECRET_KEY` → klarer Fehler; (b) Cookie aus Pod A wird in Pod B akzeptiert. |
| **Rollback** | Wert in Env zurücksetzen. Aktive Sessions werden invalidiert. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-10 — Tenant-Default `"default-tenant"` im Modular-Stack

| Feld | Wert |
|---|---|
| **ID** | F-10 |
| **Severity** | **high** |
| **Datei/Funktion** | `shared/tenant/context.py:23` `_tenant_id_ctx.get()` Fallback `"default-tenant"`. |
| **Risiko** | Sobald Code Pfade existieren, in denen `_require_tenant` umgangen wird (CLI-Scripts, Hintergrund-Jobs, async Tasks ohne Header-Kontext), schreiben die Services in einen einheitlichen „Sammelmandanten". Unterminiert Mandantentrennung. |
| **Minimaler Fix** | Default entfernen oder per Env-Flag (`ALLOW_DEFAULT_TENANT=on`) auf reine Dev-Profile beschränken. In Produktion muss `get_current_tenant()` ohne expliziten Set-Aufruf eine `RuntimeError` werfen. |
| **Testplan** | (a) Hintergrundjob ohne Tenant → `RuntimeError`; (b) Job mit Tenant-Set-Aufruf → läuft. |
| **Rollback** | Env-Flag wieder aktivieren. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-11 — Auth-Duplikate zwischen Legacy und Modular

| Feld | Wert |
|---|---|
| **ID** | F-11 |
| **Severity** | **medium** |
| **Datei/Funktion** | (a) `database.py:991/1105` zwei `create_user`-Definitionen mit SHA-256, (b) `modules/.../auth/jwt_auth.py:50` bcrypt + JWT, (c) `shared_auth.py:25` separater HS256-Pfad mit eigenem Secret und 7-Tage-Token, (d) `web/app.py` Sessions + (e) `api_nexus.py` Static-Bearer. Zwei OAuth-Pfade in `web/routes_oauth.py` lebt nur im Legacy. |
| **Risiko** | Inkonsistente Auth-Pfade führen zu Drift: ein User kann sich legacy einloggen, aber modulare Tokens sind anders signiert. Cross-Subdomain-SSO über `shared_auth.py` nutzt einen separaten Secret-Pfad – Angreifer können das schwächste Glied wählen. Erhöht Angriffsfläche und Schulungsaufwand. |
| **Minimaler Fix** | (a) Sofort: dokumentieren, welcher Pfad authoritativ ist (Empfehlung: JWT aus `jwt_auth.py`); (b) Mittelfristig: Bridge `shared_auth.create_sso_token` durch dieselbe Secret/Algorithmus-Logik wie `jwt_auth.py` ersetzen; (c) `database.py` doppelte Funktionen entfernen (Tech Debt aus Baseline §5.2 / §13). Keine Funktionsänderung im Hotfix-Schritt nötig, aber Doku verpflichtend. |
| **Testplan** | (a) Auth-Matrix dokumentieren (welcher Endpoint akzeptiert was); (b) Negativtest: Token aus `shared_auth` darf nicht in `jwt_auth`-Endpoints akzeptiert werden (oder umgekehrt), solange Bridges nicht implementiert sind. |
| **Rollback** | reine Doku-Änderung. |
| **Migrationsunabhängig?** | **Teilweise** – Doku sofort, Konsolidierung gehört in den Migrationspfad (ADR-001 §7). |

---

### F-12 — Rate Limiting nur lokal, keine Persistenz, doppelter Stack

| Feld | Wert |
|---|---|
| **ID** | F-12 |
| **Severity** | **medium** |
| **Datei/Funktion** | (a) Modular: `modules/.../auth/rate_limiter.py:8` `Limiter(key_func=get_remote_address, default_limits=["100/minute"])` (`slowapi`, in-memory). (b) Legacy: `rate_limiter.py:79` In-Memory Dict, `web/rate_limiter.py` SQLite-Tabelle `rate_limit_usage`. (c) `api_nexus.py:51–63` eigenes In-Memory-Dict. |
| **Risiko** | Drei unterschiedliche Implementierungen, alle in-memory oder lokal. Bei mehreren Pods gilt das Limit pro Pod, nicht global; Brute-Force gegen Login (`/login`) ist effektiv, sobald Last-Verteilung greift. Außerdem keine Differenzierung zwischen IPs hinter NAT/Proxy (`get_remote_address` nimmt direkt `request.client.host`, ignoriert `X-Forwarded-For`). |
| **Minimaler Fix** | (a) Sofort: striktere Limits für Auth-Pfade (`/login`, `/api/v1/auth/token`, `/auth/forgot-password`) auf 5/min/IP. (b) `slowapi` mit Redis-Backend konfigurieren oder kurzfristig `X-Forwarded-For`-Auswertung aktivieren (Trust-Proxy notwendig). (c) Eindeutigen Limiter-Stack pro Layer benennen (Legacy vs. Modular), Duplikate entfernen. |
| **Testplan** | (a) 6× falscher Login innerhalb 60 s → `429`; (b) Limit greift über mehrere Pods (sobald Backend zentralisiert). |
| **Rollback** | Limit-Konfiguration via Env steuern. |
| **Migrationsunabhängig?** | **Ja** für Limit-Verschärfung; zentralisiertes Backend ist eigenständige Migration. |

---

### F-13 — Security Headers fehlen im Modular-Layer und sind im Legacy unvollständig

| Feld | Wert |
|---|---|
| **ID** | F-13 |
| **Severity** | **medium** |
| **Datei/Funktion** | (a) Modular `modules/.../api/main.py` hat **keine** Security-Header-Middleware; (b) Legacy `web/app.py:180–189` setzt `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, **aber kein** `Content-Security-Policy` und kein `Strict-Transport-Security`. |
| **Risiko** | Fehlendes HSTS verhindert nicht den ersten HTTP→HTTPS-Stripping-Angriff (CVE-Klassiker), fehlendes CSP erlaubt unvermeidbare XSS-Eskalation in HTML-Templates (`web/templates/*.html`). Modular-API liefert JSON, ist aber teilweise als Browser-Fallback adressierbar (`/api/docs`). |
| **Minimaler Fix** | (a) Modular: Middleware analog zu Legacy einziehen + `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`. (b) Legacy: CSP einführen, beginnend mit Report-Only-Modus, dann enforce. `frame-ancestors 'self'`, `base-uri 'self'`, `default-src 'self' https:`, `script-src 'self' 'nonce-…'`. |
| **Testplan** | (a) `curl -I` gegen Domain → erwartete Header; (b) CSP-Report-Logs auswerten; (c) Pen-Test-Tools (`mozilla-observatory`, `securityheaders.com`) Score ≥ B. |
| **Rollback** | Header-Middleware per Feature-Flag deaktivieren. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-14 — `cookies.txt` und Backup-Verzeichnisse im Repo

| Feld | Wert |
|---|---|
| **ID** | F-14 |
| **Severity** | **medium** |
| **Datei/Funktion** | `cookies.txt`, `_archive/`, `_archive_20260217_194225/`, `_old_code/`, `backup_2025-11-18/`, `backup_20260203_162219/`, `web/app.py.backup_*`, `web/app_before_*`, `web/app_jobhelper_backup_*`. Aktuell lt. Inspektion `cookies.txt` leer; Backup-Files enthalten **veraltete Default-Secrets** (`web/app_before_*:917,1239` etc. mit `secret_key='sbs-invoice-app-secret-key-2025'`). |
| **Risiko** | Veraltete Backup-Files dokumentieren historisch echte Secrets, vereinfachen Forensik für Angreifer („welche Werte hatten wir früher?"). Außerdem Compliance-Hygiene: PII-Risiko im Repo wenn historische Backups Daten enthalten. |
| **Minimaler Fix** | (a) `cookies.txt` löschen + `.gitignore` ergänzen; (b) Backup-Verzeichnisse außerhalb des Repos archivieren (Cold Storage, S3+KMS), nicht im Source-Tree. (c) BFG-Cleanup-Run gegen Git-History (Risikoabwägung mit Branch-Strategie). |
| **Testplan** | `git ls-files` enthält keinen Backup-Pfad mehr; `git log -p -- '*backup*'` zeigt nur Lösch-Commit. |
| **Rollback** | Backups bleiben in Cold Storage erreichbar. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-15 — Default-Tenant-Userspoof in `api_nexus.verify_api_key`

| Feld | Wert |
|---|---|
| **ID** | F-15 |
| **Severity** | **medium** |
| **Datei/Funktion** | `api_nexus.py:67` returned `{"id": 16, "email": "ki@sbsdeutschland.de", "is_admin": True}` als User‑Surrogat für jede gültige Nexus-Auth. |
| **Risiko** | Audit-Trail attribuiert alle Nexus-API-Aktionen einem Admin-User, der real existiert. Nicht nachvollziehbar, welcher Konsument welche Aktion ausgelöst hat. Missbrauch fällt nicht auf, weil im `audit_log` immer derselbe User steht. |
| **Minimaler Fix** | API-Keys an konkrete Service-Accounts binden, mehrere Keys mit eigener `service_account_id`. Audit-Log schreibt `service_account_id`, nicht admin-id 16. |
| **Testplan** | (a) `audit_log` zeigt unterschiedliche Service Accounts; (b) Revocation eines Service Accounts blockiert nur dessen Calls. |
| **Rollback** | Migration additiv (alte Static-Auth bleibt zunächst, neue Schlüssel zusätzlich). |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-16 — Hardkodierter `.env`-Pfad und gemischte Settings-Quellen

| Feld | Wert |
|---|---|
| **ID** | F-16 |
| **Severity** | **low** |
| **Datei/Funktion** | `modules/rechnungsverarbeitung/src/api/main.py:6` `load_dotenv("/var/www/invoice-app/.env")`. `api_nexus.py:7` `load_dotenv()` (CWD). Zusätzlich `shared/settings.py` (pydantic). |
| **Risiko** | Container-Deployments (vgl. `docker-compose.yml`) injizieren Variablen direkt; das hartkodierte Lesen aus `/var/www/invoice-app/.env` schlägt im Container still fehl, App nutzt dann ggf. Defaults (siehe F-05/F-09). Inkonsistente Sources erschweren Audit. |
| **Minimaler Fix** | `load_dotenv()` ohne Pfad oder per `Settings`-Klasse zentralisieren; Container-Deployments verlassen sich auf Env. |
| **Testplan** | (a) Container-Start ohne `/var/www/invoice-app/.env` → identisches Verhalten wie systemd-Deployment. |
| **Rollback** | Pfad-Override via Env-Variable möglich. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-17 — Sentry `send_default_pii=False` korrekt, aber LLM-Payloads ungefiltert

| Feld | Wert |
|---|---|
| **ID** | F-17 |
| **Severity** | **low** |
| **Datei/Funktion** | `modules/.../api/main.py:9–16` (Sentry korrekt konfiguriert). Aber `llm_router.py`, `category_ai.py` loggen Prompts/Responses inkl. extrahierter Rechnungsdaten. |
| **Risiko** | OCR-extrahierte Inhalte (USt-IdNr, IBAN, Beträge, Empfängerdaten) gelangen ins Log. Abhängig von Log-Aufbewahrung Konflikt mit DSGVO Art. 5 Abs. 1 lit. e (Speicherbegrenzung) und § 147 AO (Aufbewahrungsfristen außerhalb der Buchhaltung). |
| **Minimaler Fix** | LLM-Prompts/Responses nur als Hash/Längenmetadaten loggen, vollständige Payloads nur bei DEBUG-Level + maskiert. |
| **Testplan** | (a) Log-Sample zeigt keine IBAN-/USt-Werte mehr; (b) Audit-Eintrag enthält Hash der Anfrage. |
| **Rollback** | Logging-Level temporär hochziehen. |
| **Migrationsunabhängig?** | **Ja**. |

---

### F-18 — `WWW-Authenticate: Bearer` Inkonsistenz und fehlende Audience/Issuer-Validierung

| Feld | Wert |
|---|---|
| **ID** | F-18 |
| **Severity** | **low** |
| **Datei/Funktion** | `modules/.../auth/jwt_auth.py:88–92` (`jwt.decode` ohne `audience`/`issuer`). `shared_auth.py:73` setzt `verify_aud: False` ausdrücklich. |
| **Risiko** | Tokens, die für andere Subdomains/Audiences ausgestellt sind, werden akzeptiert. Insbesondere mit Cross-App-SSO (`contract.sbsdeutschland.com`, `app.sbsdeutschland.com`) ist Audience-Differenzierung essentiell. |
| **Minimaler Fix** | `audience` und `issuer` beim Decode setzen (`audience="finance-api"`, `issuer="sbs-deutschland"`). Token-Erzeugung entsprechend befüllen. |
| **Testplan** | (a) Token mit falscher Audience → `401`; (b) Audit-Log zeigt Issuer-Konsistenz. |
| **Rollback** | Audience-Check per Env-Flag deaktivieren (Übergangsphase). |
| **Migrationsunabhängig?** | **Ja**. |

---

## Priorisierung

### 1. Sofort fixen (heute / morgen)
| ID | Titel | Severity |
|---|---|---|
| **F-01** | Modulare API ohne Auth, nur Tenant-Header | critical |
| **F-02** | Nexus Default-API-Key | critical |
| **F-03** | SHA-256 ohne Salt | critical |
| **F-04** | Klartext-Secrets (config.yaml/IMAP/JWT/Session) | critical |
| **F-05** | Ephemerer JWT-Default | high |
| **F-09** | Default Session-Secret | high |

### 2. Diese Woche fixen
| ID | Titel | Severity |
|---|---|---|
| **F-06** | CORS `*` mit Credentials | high |
| **F-07** | Token-Logging | high |
| **F-08** | CSRF-Schutz Legacy | high |
| **F-10** | `default-tenant`-Fallback | high |
| **F-12** | Rate-Limit-Verschärfung Auth-Pfade | medium |

### 3. Vor Enterprise-Demo fixen
| ID | Titel | Severity |
|---|---|---|
| **F-11** | Auth-Duplikate dokumentieren | medium |
| **F-13** | Security Headers (CSP/HSTS) im Modular & Legacy | medium |
| **F-14** | `cookies.txt`/Backups aus Repo | medium |
| **F-15** | Service-Account-Identitäten für Nexus | medium |
| **F-18** | Audience/Issuer-Validierung | low |

### 4. Später
| ID | Titel | Severity |
|---|---|---|
| **F-16** | Settings-Zentralisierung | low |
| **F-17** | LLM-Logging-Hygiene | low |
| **F-12 (Teil 2)** | Zentrales Redis/DB-basiertes Rate-Limiting | medium |
| **F-14 (Teil 2)** | Git-History-Cleanup (BFG) | medium |

---

## Top 5 Hotfixes

1. **F-01 — Auth-Pflicht für alle modularen Endpunkte.** Höchste Priorität: aktuell ist die produktiv adressierte Schicht im Effekt offen.
2. **F-02 — Nexus Default-API-Key entfernen + rotieren.**
3. **F-04 — Klartext-Secrets bereinigen (config.yaml, IMAP, JWT/Session-Defaults), App-Password rotieren.**
4. **F-03 — Passwort-Hashing auf bcrypt umstellen, schrittweise Migration bestehender Hashes.**
5. **F-05 + F-09 — Statische Secret-Defaults entfernen (JWT_SECRET, SESSION_SECRET_KEY, JWT in `shared_auth.py`).**

---

## Welche Fixes zuerst in Code umgesetzt werden sollen

Reihenfolge für die Code-Umsetzung – jeweils kleine, isolierte PRs:

1. **F-04 (Repo-Hygiene + Secret-Rotation):** `config.yaml` aus dem Repo nehmen, `config.yaml.example` von Klartext befreien, alle eingecheckten Default-Secrets durch `RuntimeError`-Stubs ersetzen, Rotation der echten Werte. **Vor jedem anderen Code-Fix**, weil sonst weitere Commits die Secrets weiter im Klartext referenzieren.
2. **F-05 + F-09:** Defaults aus `jwt_auth.py:21`, `shared_auth.py:18`, `web/app.py:1722` entfernen. Fail-Fast bei fehlender Env-Variable. Klein, lokal, hohe Wirkung.
3. **F-02:** `api_nexus.py:20` Default entfernen, `secrets.compare_digest`, Token rotieren.
4. **F-01:** `Depends(get_current_user)` und Tenant-Cross-Check zentralisieren (Helper `require_authenticated_tenant`), schrittweise an alle `/api/v1`-Endpunkte ziehen, geschützt durch Feature-Flag, mit Smoke-Tests pro Cluster.
5. **F-07:** Logging-Filter in `web/app.py` und Modular-Logging-Setup einführen, betroffene `logger.info`-Stellen redigieren.
6. **F-06:** CORS auf Whitelist umstellen (`modules/.../api/main.py:86`).
7. **F-10:** `shared/tenant/context.py:23` Default entfernen, Env-Flag für Dev.
8. **F-12 (Phase 1):** strengere Auth-Pfad-Limits (5/min/IP) in `slowapi`-Setup ergänzen.
9. **F-13:** Security-Header-Middleware in der Modular-API einziehen, HSTS+CSP im Legacy ergänzen.
10. **F-03:** bcrypt-Migrations-Pfad in `database.py` (Doppelpfad), neue User direkt bcrypt.

---

## Welche Fixes NICHT ohne manuelles Review gemacht werden sollen

Diese Fixes haben Seiteneffekte, die ein Codebot/automatisierter Patch falsch einschätzen würde — bitte explizit reviewen und mit Stakeholdern abstimmen:

1. **F-08 (CSRF) — manuelles Review.** Setzen einer CSRF-Middleware bricht potenziell alle existierenden Forms (Login, Register, Admin-Panel, 2FA-Setup, Stripe-Webhook ⚠️ darf NICHT durch CSRF gefiltert werden, ist eingehend von Stripe). Frontend-Migration und API-Konsumenten (mobile Apps?) müssen vorher inventarisiert werden.
2. **F-03 (Passwort-Re-Hashing) — manuelles Review.** Doppelpfad (SHA-256 erkennen, bei Login auf bcrypt heben) ist sicherheitskritisch. Falsch implementiert → entweder Login-Bypass oder Mass-Lockout. Pen-Test vor Rollout.
3. **F-11 (Auth-Konsolidierung) — manuelles Review.** Konsolidierung der drei Auth-Pfade (`web/app.py` Sessions, `shared_auth.py` SSO-JWT, `jwt_auth.py` Modular) ist faktisch eine Architekturentscheidung mit Vertragsfolgen (z. B. SSO über `*.sbsdeutschland.com`). Gehört in den Migrationspfad gemäß ADR-001.
4. **F-12 Phase 2 (zentrales Rate-Limit-Backend) — manuelles Review.** Hinzufügen von Redis (oder Postgres-Backend) ist Infrastrukturentscheidung. Ohne SRE-Abstimmung nicht ausrollen.
5. **F-13 (CSP) — manuelles Review.** CSP zerschießt erfahrungsgemäß Inline-Skripte/Stripe-Iframe/Sentry/Tag-Manager. Erst Report-Only-Modus für ≥ 7 Tage, dann enforce. Mit Marketing/Frontend abstimmen, nicht „blind enforced".
6. **F-14 Phase 2 (Git-History-Cleanup mit BFG/`git filter-repo`) — manuelles Review.** Erfordert Force-Push und Koordination mit allen Branches/Tags/PRs. Niemals automatisch; explizite Ankündigung & Coordination mit allen Devs.
7. **F-04 Phase 2 (Re-Verschlüsselung der `email_inbox_config`-Spalte) — manuelles Review.** Schemata in SQLite plus Live-Daten plus Schlüsselmanagement. Migration mit Daten-Rewrite ist DBA-Tätigkeit.
8. **F-17 (LLM-Logging) — manuelles Review.** Sentry-/Log-Konfiguration berührt Compliance-Vereinbarungen (Auftragsverarbeitung). Datenschutzbeauftragten einbeziehen.

---

## Migrationsunabhängigkeit – kompakte Übersicht

| Fix | Migrationsunabhängig? |
|---|---|
| F-01 | Ja |
| F-02 | Ja |
| F-03 | Ja |
| F-04 | Ja (Pflicht) |
| F-05 | Ja |
| F-06 | Ja |
| F-07 | Ja |
| F-08 | Ja (Legacy) |
| F-09 | Ja |
| F-10 | Ja |
| F-11 | Teilweise (Doku ja, Konsolidierung nein) |
| F-12 | Phase 1 ja, Phase 2 nein |
| F-13 | Ja |
| F-14 | Ja |
| F-15 | Ja |
| F-16 | Ja |
| F-17 | Ja |
| F-18 | Ja |

---

## Offene Fragen

1. ⚠️ Wird `api_nexus.py` produktiv über `web/app.py` eingebunden (`include_router(nexus_router)`)? Falls nein, mindert das den F-02-Impact, eliminiert ihn aber nicht (`api_nexus.py` ist standalone importierbar).
2. ⚠️ Welcher Auth-Stack ist auf `app.sbsdeutschland.com` heute aktiv (Sessions, SSO-Cookie, JWT)? Ohne diese Klarheit ist die Reihenfolge zwischen F-08 (CSRF) und F-01 (Auth-Pflicht) nicht final festsetzbar.
3. ⚠️ Existieren bereits Vertragsverpflichtungen (DPA, ToS) zur Vorhaltung von Klartext-Logs? F-07/F-17 hängen davon ab.
4. ⚠️ Gibt es eine zentrale Secret-Storage-Lösung (Vault, AWS SSM, Doppler)? Ohne diese ist F-04 nur Verschiebung der Klartext-Files in Env-Files.
5. ⚠️ Welche Konsumenten/Webhooks treffen heute auf die Modular-API? F-01 könnte Drittsysteme brechen.
6. ⚠️ Gibt es Pen-Test-Reports oder externe Audits, die Findings priorisieren? Falls ja, abgleichen.

---

## Referenzen

- `docs/adr/ADR-001-flowcheck-target-architecture.md`
- `docs/FLOWCHECK_ARCHITECTURE_BASELINE.md`
- `SECURITY.md`, `SECURITY_PRIVACY_DESIGN.md`, `AGENTS.md`, `CLAUDE.md`
- OWASP ASVS v4.0.3 §V2 (Auth), §V3 (Session), §V4 (Access Control), §V8 (Sensitive Data), §V14 (Configuration)
- BSI TR-02102-2 (Passwortverwaltung), BSI Grundschutz APP.3.1, APP.3.3
- DSGVO Art. 32 (Sicherheit der Verarbeitung)

---

*Ende Security Hotfix Plan. Keine Codeänderungen, keine Dependencies hinzugefügt, keine bestehenden Dateien angepasst, keine Secrets ausgegeben.*
