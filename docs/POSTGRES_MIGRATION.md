# SQLite → PostgreSQL (Neon) – Migration & Cutover

> Status: **Foundation eingebaut & getestet; Produktiv-Cutover weiterhin gesperrt.**
> Die Runtime besitzt jetzt einen read-only, fail-closed Schema-Guard für die
> User-ID-Domain. Eine vorhandene PostgreSQL-Datenbank mit inkompatibler
> `users.id`-/FK-Domain wird vor dem Production-App-Import und vor dem
> Best-effort-Migrator blockiert. Ein automatischer Typ-Cast oder Schema-Repair
> findet ausdrücklich nicht statt.

## Architektur

`database.get_connection()` wählt das Backend automatisch:
- **`DATABASE_URL` gesetzt** (`postgresql://…`) → psycopg-Verbindung über
  `db_compat.connect_postgres()` (mit `?`→`%s`-Übersetzung und
  `sqlite3.Row`-ähnlichen Zeilen).
- **nicht gesetzt** → SQLite (Default, lokale Entwicklung / aktueller Bestand).

Damit ist die Umstellung opt-in. Für die produktive FastAPI-Komposition gilt
zusätzlich: `modules/rechnungsverarbeitung/src/api/hardened_app.py` führt
`validate_configured_postgres_schema()` **vor** dem Import des Legacy-App-Graphs
und damit vor möglichen importseitigen Schema-Initialisierungen aus.

### `db_compat.py`
- `translate_placeholders(sql)` – `?`→`%s`, literale `%`→`%%`.
- `translate_ddl(sql)` – u. a. `INTEGER PRIMARY KEY AUTOINCREMENT` →
  `SERIAL PRIMARY KEY`.
- `HybridRow` – Index- und Namenszugriff, `dict(row)`.
- `PgConnection`/`PgCursor` – SQLite-kompatibler Wrapper; `lastrowid` via
  `RETURNING id` (best-effort), PRAGMA-/DML-/Datetime-Kompatibilität.

### `postgres_schema_guard.py`
Der Guard liest ausschließlich `information_schema`-Metadaten. Er ändert weder
Schema noch Daten und gibt keine User-/Tenant-IDs oder sonstigen Zeilenwerte aus.

Kanonischer Vertrag für die aktuelle Legacy-App:

| Spalte | Erwartete PostgreSQL-Domain |
|---|---|
| `users.id` | `integer` (SERIAL-Backing) + alleiniger Primary Key |
| `jobs.user_id` | `integer`, sofern Tabelle vorhanden |
| `subscriptions.user_id` | `integer`, sofern Tabelle vorhanden |

Fehlt `users` vollständig, gilt die Datenbank als **fresh** und darf durch den
kanonischen Initialisierungspfad aufgebaut werden. Existiert `users`, aber die
ID-Domain oder ein vorhandener Referenztyp weicht ab, schlägt der Guard
fail-closed fehl.

## Read-only Assessment vor jeder Migrationsentscheidung

Vor einem realen Cutover zuerst ausschließlich den Assessment-Report ausführen:

```bash
python scripts/assess_postgres_id_migration.py --target "$DATABASE_URL"
```

Der Report enthält nur Schema-Metadaten und Aggregate, insbesondere:
- Anzahl User-Zeilen,
- bei textbasierter `users.id`: Anzahl nicht-dezimaler IDs,
- Anzahl Werte außerhalb des PostgreSQL-`integer`-Bereichs,
- Anzahl numerischer Kollisionsgruppen (z. B. textuell verschiedene IDs, die
  nach einem Integer-Cast identisch würden),
- Aggregate zu verwaisten `jobs.user_id`-/`subscriptions.user_id`-Referenzen.

Der Report setzt immer `automatic_migration_permitted=false`. Er ist eine
Entscheidungsgrundlage, keine Migration.

## Cutover-Prozess

1. **Staging-/Neon-DB in freigegebener Region anlegen.** Produktivdaten nicht
   direkt als erstes Ziel verwenden.
2. **Read-only Schema-Assessment** ausführen und Report fachlich/technisch
   freigeben.
3. Bei inkompatibler User-ID-Domain: **Stop.** Offline-Migrationsplan erstellen,
   der PK und sämtliche FK-/Tenant-Referenzen atomar und typkonsistent behandelt.
4. Erst bei kompatibler/fresh Ziel-DB den Best-effort-Migrator verwenden:
   ```bash
   python scripts/migrate_sqlite_to_postgres.py \
       --source /var/www/invoice-app/invoices.db \
       --target "$DATABASE_URL" --create-schema --dry-run
   python scripts/migrate_sqlite_to_postgres.py \
       --source /var/www/invoice-app/invoices.db \
       --target "$DATABASE_URL" --create-schema
   ```
   Der Migrator führt denselben Schema-Guard aus und beendet sich bei Drift vor
   CREATE/INSERT mit Exit-Code 3.
5. Sequenzen nach expliziter Datenmigration verifizieren/setzen, z. B.:
   `SELECT setval(pg_get_serial_sequence('invoices','id'), MAX(id)) FROM invoices;`
6. Smoke-/Regressionstests auf Staging: Login, Tenant-Isolation,
   `/api/app/dashboard/kpis`, `/api/app/invoices`, Upload, Freigabe,
   DATEV-Export, Auth-Actions und AI-Policy-Gates.
7. `DATABASE_URL` in Produktion erst nach dokumentierter Cutover-Freigabe setzen.

## HOCH – Bekannter Schema-Blocker: User-ID-Domain

Das kanonische Legacy-Schema in `database.py` definiert `users.id` als
`INTEGER PRIMARY KEY AUTOINCREMENT`; die PostgreSQL-Übersetzung macht daraus
`SERIAL`. `subscriptions.user_id`, `jobs.user_id` und die zugehörigen
Legacy-Tenant-Bezüge sind numerisch.

Ein bereits beobachtetes PostgreSQL-Schema mit `users.id TEXT` stammt daher
nicht aus diesem kanonischen DDL-Vertrag und ist nicht automatisch kompatibel.
Der neue Guard verhindert jetzt, dass die Production-App oder der
Best-effort-Migrator ein solches Ziel teilweise initialisieren oder beschreiben.

**Nicht zulässig als automatischer Fix:**
- `ALTER ... TYPE integer USING id::integer` ohne vorherige Datenanalyse,
- selektive Umstellung nur des Primärschlüssels,
- FK-Erzeugung über gemischte Typdomänen,
- Löschen/Ersetzen nicht castbarer IDs,
- automatische Re-Nummerierung von Usern/Tenants.

Die eigentliche Umstellung bleibt eine explizite, getestete Offline-Migration
mit Backup, Rollback, Mapping-Nachweis und referenzieller Vollständigkeitsprüfung.

## HOCH – Separater Schema-Drift: Alembic vs. Legacy-Tenant-Domain

Die derzeitige Alembic-Initialmigration `alembic/versions/001_initial.py`
erzeugt ein separates Rechnungsmodell und definiert `invoices.tenant_id` als
`String(128)`; der Legacy-App-Pfad in `database.py` verwendet dagegen eine
numerische User-/Tenant-Domain für seine Rechnungszuordnung. Alembic verwaltet
aktuell außerdem **nicht** das vollständige Legacy-Schema (`users`, `jobs`,
`subscriptions` usw.).

Dieser Befund wird bewusst **nicht** durch den User-ID-Guard automatisch
"korrigiert". Vor einem Produktiv-Cutover muss entschieden werden, welches
Schema der kanonische Owner für die App-Runtime ist und wie Tenant-IDs über
Alembic-/Legacy-Grenzen hinweg typisiert werden. Bis diese Entscheidung mit
Migration und Tests umgesetzt ist, bleibt der reale PostgreSQL-Cutover trotz
User-ID-Guard **HOCH blockiert**.

## Weitere offene Punkte vor Produktiv-Cutover

1. Alembic und `database.py` zu **einem** kanonischen Schema-Lifecycle
   konsolidieren; keine parallelen, divergierenden DDL-Owner.
2. Alle produktiven SQLite-Kompatibilitätsübersetzungen gegen eine isolierte
   PostgreSQL-Staging-DB regressionsprüfen.
3. Upsert-/`lastrowid`-Sonderfälle und bool/json/timestamp-Domains vollständig
   gegen die Zielversion verifizieren.
4. Reale Backup-/Restore-/Rollback-Prozedur testen.
5. Nach Migration einen Cross-Tenant-Negativtest fahren: Tenant A darf weder
   Inhalt noch Metadaten/Existenzsignale von Tenant B ableiten können.

## Empfehlung

Der neue Schema-Guard reduziert das Risiko einer **partiellen oder impliziten
Migration** wesentlich, löst aber nicht die fachliche ID-Domain-Entscheidung.
Der nächste Architektur-Schritt ist daher nicht ein automatischer Cast auf der
bekannten Ziel-DB, sondern die Konsolidierung von Alembic und Legacy-DDL in ein
kanonisches, versioniertes PostgreSQL-Schema plus getestete Offline-Migration.
