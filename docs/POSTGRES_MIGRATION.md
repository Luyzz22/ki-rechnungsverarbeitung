# SQLite → PostgreSQL (Neon) – Migration & Cutover

> Status: **Foundation eingebaut & getestet** (Platzhalter-/Zeilen-Kompatibilität,
> Connection-Switch, Migrationsskript). Der vollständige Produktiv-Cutover
> erfordert eine erreichbare Neon-Instanz zum Verifizieren – siehe „Offene Punkte".

## Architektur

`database.get_connection()` wählt das Backend automatisch:
- **`DATABASE_URL` gesetzt** (`postgresql://…`) → psycopg-Verbindung über
  `db_compat.connect_postgres()` (mit `?`→`%s`-Übersetzung und
  `sqlite3.Row`-ähnlichen Zeilen).
- **nicht gesetzt** → SQLite (Default, lokale Entwicklung / aktueller Bestand).

Damit ist die Umstellung **opt-in** und ohne Risiko für den laufenden
SQLite-Betrieb (kein Verhalten ändert sich, solange `DATABASE_URL` fehlt).

### `db_compat.py`
- `translate_placeholders(sql)` – `?`→`%s`, literale `%`→`%%` (unit-getestet).
- `HybridRow` – Index- **und** Namenszugriff, `dict(row)` (unit-getestet).
- `PgConnection`/`PgCursor` – dünner Wrapper; `lastrowid` via `RETURNING id`
  (best-effort), `PRAGMA` → No-Op.

## Cutover-Prozess

1. **Neon-DB anlegen** (Region Frankfurt) und `DATABASE_URL` notieren.
2. **Abhängigkeit**: `pip install 'psycopg[binary]'` (steht bereits in `requirements.txt`).
3. **Schema + Daten migrieren** (App vorher in Wartung/stoppen):
   ```bash
   export DATABASE_URL="postgresql://USER:PW@HOST/db?sslmode=require"
   python scripts/migrate_sqlite_to_postgres.py \
       --source /var/www/invoice-app/invoices.db \
       --target "$DATABASE_URL" --create-schema --dry-run   # erst zählen
   python scripts/migrate_sqlite_to_postgres.py \
       --source /var/www/invoice-app/invoices.db \
       --target "$DATABASE_URL" --create-schema             # dann schreiben
   ```
4. **`DATABASE_URL` in `.env`** setzen und Dienst neu starten
   (`systemctl restart invoice-app`). `get_connection()` nutzt nun PostgreSQL.
5. **Smoke-Test**: Login, `/api/app/dashboard/kpis`, `/api/app/invoices`,
   Upload, Freigabe, DATEV-Export.
6. **Sequenzen prüfen**: nach dem Daten-Import die `SERIAL`-Sequenzen auf
   `MAX(id)+1` setzen, z. B.
   `SELECT setval(pg_get_serial_sequence('invoices','id'), MAX(id)) FROM invoices;`

## Offene Punkte (vor Produktiv-Cutover zu erledigen/verifizieren)

Diese erfordern eine echte Neon-Instanz und sind **noch nicht** verifiziert:

1. **SQLite-spezifische Funktionen** in Bestands-Queries müssen auf PG portiert
   werden:
   - `strftime('%Y-%m', x)` → `to_char(x::timestamp, 'YYYY-MM')`
   - `substr(x,1,10)` → `left(x,10)` / `substring`
   - `datetime('now', '-30 days')` → `now() - interval '30 days'`
   - `DATE('now')` → `current_date`
   Betroffen u. a.: Dashboard-/Audit-Datumsfilter, `enterprise_dashboard.get_trend`,
   diverse Reports.
2. **DDL**: `db_compat` übersetzt Platzhalter, nicht das Schema. Die
   `init_*`-Funktionen nutzen `PRAGMA table_info` (→ No-Op auf PG) und
   `INTEGER PRIMARY KEY AUTOINCREMENT`. Für PG sollte das Schema über das
   Migrationsskript (`--create-schema`) **oder** Alembic erzeugt und einmal
   geprüft werden. `_ensure_column`-Aufrufe (ALTER) sind auf PG idempotent
   abzusichern.
3. **Upserts**: `INSERT OR IGNORE`/`INSERT OR REPLACE` (SQLite) ≠ PG
   (`ON CONFLICT … DO NOTHING/UPDATE`). Vorkommen prüfen.
4. **`lastrowid`**: wird best-effort über `RETURNING id` emuliert – funktioniert
   für Tabellen mit `id`-Spalte; Sonderfälle prüfen.
5. **Booleans/JSON**: SQLite speichert 0/1 und Text-JSON; auf PG ggf. `boolean`
   bzw. `jsonb` – die neue `api_frontend.py` ist datentyp-tolerant, ältere
   Module sind zu prüfen.

## Empfehlung
Die `/api/app`-API (Frontend) und die neuen Enterprise-Module verwenden
`?`-Platzhalter und sind über `db_compat` PG-kompatibel. Für einen sauberen
Produktiv-Cutover die obigen Punkte gegen eine Neon-Staging-DB abarbeiten und
den Smoke-Test (Schritt 5) grün fahren, bevor `DATABASE_URL` in Produktion
aktiviert wird.
