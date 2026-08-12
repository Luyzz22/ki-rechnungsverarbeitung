# SQLite → PostgreSQL (Neon) – Migration & Cutover

> Status: **Produktiv-Cutover weiterhin HOCH gesperrt.**
> Das Repository enthält derzeit zwei unterschiedliche Identity-/Tenant-Modelle.
> Der read-only Schema-Guard ist deshalb ausschließlich auf den
> **Legacy SQLite→PostgreSQL-Migrationspfad** beschränkt. Er darf nicht pauschal
> beim Start der modularen Production-App ausgeführt werden, solange die beiden
> Identity-Verträge nicht konsolidiert sind.

## Architektur

Das Repository befindet sich weiterhin in einer hybriden Übergangsarchitektur:

- **Legacy-Pfad (`database.py`)**: `users.id` numerisch (`INTEGER` / PostgreSQL
  `SERIAL`), `jobs.user_id` und `subscriptions.user_id` ebenfalls numerisch.
- **Modular-Pfad (`modules/rechnungsverarbeitung/**`)**: Authentifizierung über
  `UserService`, der UUID-artige `users.id` als String sowie einen separaten
  String-`tenant_id` verwendet. `UserAuth.user_id` und `UserAuth.tenant_id` sind
  ebenfalls Strings.
- **Modulares Invoice-Schema (Alembic/SQLAlchemy)**: `invoices.tenant_id` ist
  `String(128)`.

Diese Modelle dürfen nicht durch einen impliziten Cast miteinander vermischt
werden. Insbesondere ist `users.id TEXT` **nicht pauschal fehlerhaft**: Es kann
zum modularen Auth-Vertrag gehören. Fehlerhaft ist ein Ziel dann, wenn ein
bestimmter Runtime-/Migrationspfad auf eine inkompatible Domain trifft.

### `db_compat.py`
- `translate_placeholders(sql)` – `?`→`%s`, literale `%`→`%%`.
- `translate_ddl(sql)` – u. a. `INTEGER PRIMARY KEY AUTOINCREMENT` →
  `SERIAL PRIMARY KEY`.
- `HybridRow` – Index- und Namenszugriff, `dict(row)`.
- `PgConnection`/`PgCursor` – SQLite-kompatibler Wrapper; `lastrowid` via
  `RETURNING id` (best-effort), PRAGMA-/DML-/Datetime-Kompatibilität.

## Legacy-Migrationsguard

`postgres_schema_guard.py` schützt den Best-effort-Migrator
`scripts/migrate_sqlite_to_postgres.py`. Dieser Migrationspfad übernimmt das
Legacy-Schema aus SQLite und erwartet deshalb ausdrücklich:

| Legacy-Spalte | Erwartete PostgreSQL-Domain |
|---|---|
| `users.id` | `integer` / SERIAL + alleiniger Primary Key |
| `jobs.user_id` | `integer`, sofern Tabelle vorhanden |
| `subscriptions.user_id` | `integer`, sofern Tabelle vorhanden |

Ein bereits vorhandenes text-/UUID-basiertes `users`-Schema ist für **diesen
Legacy-Migrator** inkompatibel und wird vor CREATE/INSERT blockiert. Das ist
keine Aussage darüber, ob dieses Schema für den modularen Stack gültig ist.

Der Production-Einstiegspunkt `modules/rechnungsverarbeitung/src/api/hardened_app.py`
wendet diesen Legacy-Guard bewusst **nicht** global an. Eine globale Prüfung darf
erst wieder eingeführt werden, wenn der kanonische Production-Identity-Vertrag
feststeht und migrationsseitig versioniert ist.

## Read-only Assessment

Für eine Legacy-Migrationsbewertung kann weiterhin ausgeführt werden:

```bash
python scripts/assess_postgres_id_migration.py --target "$DATABASE_URL"
```

Der Report enthält ausschließlich Schema-Metadaten und Aggregate und setzt
`automatic_migration_permitted=false`. Es werden keine IDs, E-Mails oder
Zeilensamples ausgegeben.

## KRITISCH FÜR DEN CUTOVER – Dualer Identity-Vertrag

Der aktuelle Production-Auth-Pfad und der Legacy-DB-Pfad besitzen nicht dieselbe
Identity-Domain:

### Legacy

```text
users.id            INTEGER/SERIAL
jobs.user_id        INTEGER
subscriptions.user_id INTEGER
Tenant-Bezug        häufig über numerische user_id
```

### Modular

```text
UserService.register(): user_id = UUID-String
UserService.register(): tenant_id = "tenant-<...>"
UserAuth.user_id: str
UserAuth.tenant_id: str
Invoice.tenant_id: String(128)
```

Daraus folgt: Ein automatischer `TEXT → INTEGER`-Cast der beobachteten
PostgreSQL-User-Tabelle wäre derzeit **nicht zulässig**, weil er den modularen
Auth-Vertrag beschädigen kann. Umgekehrt kann ein pauschaler Wechsel aller
Legacy-FKs auf Text bestehende Legacy-Daten und Funktionen brechen.

## HOCH – Tabellenkollision `invoices`

Sowohl der Legacy-Pfad als auch der modulare SQLAlchemy/Alembic-Pfad verwenden
den physischen Tabellennamen `invoices`, jedoch mit unterschiedlichen
Spaltenverträgen und unterschiedlicher Tenant-Domain. `CREATE TABLE IF NOT
EXISTS` löst diese Abweichung nicht: Der zuerst erzeugte Tabellenvertrag bleibt
bestehen und der andere Stack trifft anschließend auf ein partiell fremdes
Schema.

Die Alembic-Initialmigration `alembic/versions/001_initial.py` verwaltet zudem
nur `invoices` und `invoice_events`, nicht aber den vollständigen modularen
Identity-Vertrag (`users` etc.). Damit besitzt das Repository aktuell keinen
einzigen versionierten PostgreSQL-Schema-Owner für die gesamte Production-App.

## Verbotene automatische Fixes

Bis zur Architekturentscheidung nicht automatisch ausführen:

- `ALTER users.id TYPE integer USING id::integer`,
- automatische Re-Nummerierung von Usern/Tenants,
- isolierte PK-Änderungen ohne alle abhängigen FKs,
- pauschale Umstellung aller Tenant-IDs auf Integer oder String,
- Wiederverwendung derselben `invoices`-Tabelle für zwei inkompatible
  Persistenzmodelle ohne explizite Migration,
- Löschen nicht castbarer IDs oder verwaister Datensätze.

## Nächster verbindlicher Architektur-Schritt

Vor einem realen PostgreSQL-Cutover muss ein ADR die kanonische Production-
Identity und die Persistenzgrenzen festlegen. Technisch sind zwei belastbare
Varianten möglich:

1. **Modularer Stack wird kanonisch:** UUID/String-User- und Tenant-IDs werden
   versioniert; Legacy-Daten werden explizit in das modulare Modell migriert.
2. **Physische Schema-Trennung während der Übergangsphase:** Legacy- und
   Modular-Tabellen erhalten getrennte PostgreSQL-Schemas/Tabellennamen und eine
   kontrollierte Mapping-Schicht. Keine gleichnamigen Tabellen mit
   unterschiedlichen Verträgen.

Auf Basis der bestehenden Architektur ist Variante 1 das langfristige Ziel;
Variante 2 ist die risikoärmere Zwischenstufe, falls Legacy-Funktionen weiterhin
parallel benötigt werden.

## Cutover-Gates

Ein Produktiv-Cutover bleibt blockiert, bis mindestens folgende Nachweise grün
sind:

1. ein kanonischer Identity-/Tenant-Vertrag ist als ADR beschlossen,
2. Alembic verwaltet das vollständige Ziel-Schema,
3. Legacy-/Modular-Tabellen kollidieren nicht mehr physisch,
4. Migration besitzt Backup, Rollback, Mapping- und Referenzintegritätsnachweis,
5. Login/Invite/Reset und Tenant-Isolation laufen gegen das Ziel-Schema,
6. Cross-Tenant-Negativtests sind grün,
7. Upload, Review, DATEV und AI-Policy-Gates laufen gegen dieselbe freigegebene
   Staging-Datenbank,
8. erst danach wird `DATABASE_URL` produktiv umgeschaltet.
