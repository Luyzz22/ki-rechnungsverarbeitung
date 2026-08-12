# ADR-002: Kanonische Identity- und PostgreSQL-Schema-Ownership

> **Status:** Accepted  
> **Datum:** 2026-08-12  
> **Scope:** `ki-rechnungsverarbeitung` – Legacy- und Modular-Persistenz  
> **Ergänzt:** `ADR-001-flowcheck-target-architecture.md`

## 1. Entscheidung

Die **modulare API** ist gemäß ADR-001 die Zielarchitektur. Daraus folgt für die produktive PostgreSQL-Persistenz verbindlich:

1. **Modulare User-ID:** opaque String/UUID, nicht numerisch semantisch interpretiert.
2. **Modulare Tenant-ID:** eigener opaque String (`tenant_id`), unabhängig von `users.id`.
3. **Alembic ist alleiniger Schema-Owner** des modularen PostgreSQL-Schemas.
4. Der Legacy-Pfad (`database.py`, SQLite) behält seine numerische User-/Tenant-Domain nur während der Übergangsphase.
5. Eine Legacy-SQLite→PostgreSQL-Migration darf **nicht** in dasselbe physische Schema schreiben, das die modulare Runtime verwaltet, solange die Legacy-Tabellenverträge nicht explizit transformiert wurden.
6. Gleichnamige Tabellen mit unterschiedlichen Verträgen – insbesondere `invoices` – dürfen nicht parallel als zwei kanonische Modelle existieren.
7. Es gibt **keinen automatischen `TEXT ↔ INTEGER`-Cast** für User-/Tenant-IDs.

## 2. Evidenz im aktuellen Code

Der modulare Auth-Pfad arbeitet bereits mit String-Identitäten:

- `UserService.register()` erzeugt `user_id = str(uuid.uuid4())`.
- `UserService.register()` erzeugt eine separate `tenant_id = "tenant-..."`.
- `UserAuth.user_id` und `UserAuth.tenant_id` sind Strings.
- `Invoice.tenant_id` und `InvoiceEvent.tenant_id` sind Strings.

Der Legacy-Pfad verwendet dagegen in `database.py` numerische User-/Tenant-Bezüge (`INTEGER` / PostgreSQL `SERIAL`).

Damit ist ein beobachtetes `users.id TEXT` **nicht pauschal ein Schemafehler**. Es kann zum modularen Identity-Vertrag gehören. Ein Fehler liegt vor, wenn ein Runtime- oder Migrationspfad gegen eine für ihn inkompatible Domain arbeitet.

## 3. Befund

### HOCH – Dualer Identity-Vertrag

**Befund:** Legacy und Modular besitzen unterschiedliche ID-Domains.

**Risiko:** Ein globaler Cast oder ein globaler Schema-Guard kann entweder den modularen Auth-Pfad oder Legacy-FKs zerstören. Im schlechtesten Fall entstehen falsche Tenant-Zuordnungen.

**Regulatorische Grundlage:** DSGVO Art. 5 Abs. 1 lit. f, Art. 25, Art. 32 Abs. 1 lit. b/d; NIS2 Art. 21 Abs. 2 lit. e/f, soweit anwendbar.

**Fix:** Modulare String-/UUID-Identity wird kanonisch; Legacy-IDs werden nur über eine explizite Migrations-/Mapping-Schicht übernommen.

### HOCH – Physische Tabellenkollision `invoices`

**Befund:** Legacy und Modular verwenden denselben Tabellennamen `invoices`, aber unterschiedliche Spalten- und Tenant-Verträge.

**Risiko:** `CREATE TABLE IF NOT EXISTS` schützt nicht vor Schema-Drift. Der zuerst vorhandene Tabellenvertrag kann vom zweiten Stack stillschweigend als kompatibel angenommen werden.

**Regulatorische Grundlage:** DSGVO Art. 25 und Art. 32 Abs. 1 lit. b/d.

**Fix:** Alembic übernimmt die modulare Tabelle als kanonischen Vertrag. Legacy-Daten werden transformiert, nicht durch Legacy-DDL in dieselbe Tabelle gespiegelt.

### HOCH – Unvollständige Alembic-Ownership

**Befund:** Revision `001_initial` verwaltet bislang nur `invoices` und `invoice_events`; der modulare `UserService` erwartet zusätzlich eine `users`-Tabelle. Außerdem referenziert die modulare Invoice-Pipeline Felder, die Revision 001 noch nicht vollständig bereitstellt.

**Risiko:** Ein frischer PostgreSQL-Deploy kann erfolgreich migrieren, aber erst beim Login/Invite oder bei der KI-Extraktion an fehlenden Tabellen/Spalten scheitern.

**Regulatorische Grundlage:** DSGVO Art. 25, Art. 32 Abs. 1 lit. b/d; NIS2 Art. 21 Abs. 2 lit. e/f, soweit anwendbar.

**Fix:** Nachfolgende Alembic-Revision übernimmt den modularen Identity-Vertrag und vervollständigt das Invoice-Schema fail-closed.

## 4. Kanonischer modularer Vertrag

### `users`

| Feld | Typ / Invariante |
|---|---|
| `id` | String/UUID, Primary Key |
| `email` | normalisierter String, eindeutig |
| `password_hash` | bcrypt-kompatibler String |
| `name` | String |
| `company` | String |
| `tenant_id` | String, indexiert |
| `role` | String, Anwendung validiert Rollenmenge |
| `created_at` | Timestamp |
| `updated_at` | Timestamp, nullable für importierte Altbestände |

### `invoices`

`tenant_id` bleibt ein String. Der durch `Invoice` und `invoice_processing.py` tatsächlich verwendete Vertrag muss vollständig durch Alembic abgebildet werden, einschließlich Extraktionsfeldern (`supplier`, Beträge, Währung, Rechnungsnummer/-daten und `extracted_data`).

## 5. Migrationsregeln

- Vorhandene textbasierte `users`-Tabellen dürfen von Alembic nur übernommen werden, wenn ID-Typ, Primary Key und sicherheitsrelevante Kernspalten zum modularen Vertrag passen.
- Vorhandene numerische `users.id` im modularen Ziel-Schema führen zu **fail-closed**; keine automatische Konvertierung.
- Fehlende additive, nicht identitätsverändernde Spalten dürfen migrationsseitig ergänzt werden.
- E-Mail-Eindeutigkeit muss datenbankseitig erzwungen werden. Existierende Duplikate blockieren die Migration ohne Ausgabe der betroffenen E-Mail-Adressen.
- Eine `invoices`-Tabelle mit nicht-textuellem `tenant_id` wird im modularen Alembic-Pfad als inkompatible Legacy-Kollision behandelt und blockiert.
- Migrationsfehler dürfen keine User-, Tenant-, E-Mail- oder Rechnungswerte ausgeben.
- Downgrades, die User-/Tenant-Daten zerstören könnten, sind für die Identity-Adoptionsmigration bewusst nicht automatisch erlaubt.

## 6. Legacy-Grenze

`postgres_schema_guard.py` bleibt ein Guard für den **Legacy SQLite→PostgreSQL-Migrationspfad**. Er ist keine globale Aussage über die modulare Production-Datenbank.

Falls Legacy-Funktionen vor ihrer Ablösung zwingend PostgreSQL benötigen, muss dafür entweder:

1. ein physisch separates PostgreSQL-Schema / eine separate Datenbank verwendet werden, oder
2. ein expliziter ETL-/Mapping-Prozess in das modulare Modell implementiert werden.

`DATABASE_URL` der modularen Runtime darf nicht implizit als Freigabe verstanden werden, Legacy-DDL in dasselbe Schema auszuführen.

## 7. Cutover-Gates

Ein echter PostgreSQL-Produktiv-Cutover ist erst freigegeben, wenn:

1. Alembic `users`, `invoices`, `invoice_events` und alle produktiv benötigten modularen Tabellen/Spalten vollständig verwaltet,
2. eine frische PostgreSQL-Instanz `alembic upgrade head` ohne Out-of-band-DDL besteht,
3. Login, Invite, Reset und Rollenänderung gegen dieses Schema getestet sind,
4. Invoice Upload + KI-Extraktionspersistenz gegen dieses Schema getestet sind,
5. Cross-Tenant-Negativtests grün sind,
6. Legacy- und Modular-Tabellen nicht physisch kollidieren,
7. Backup/Restore/Rollback und Datenmapping dokumentiert und getestet sind.

## 8. Konsequenz

Die langfristige Richtung ist **Modular-first mit String/UUID Identity und Alembic als Single Source of Truth**. Der Legacy-Stack bleibt eine migrationspflichtige Quelle, nicht ein zweiter Schema-Owner.