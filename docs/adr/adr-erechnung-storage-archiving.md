# ADR: E‑Rechnung Storage, Archivierung & Evidence

## Context
Der Hub muss technische Nachweise für Betriebsprüfung/Audit bereitstellen, ohne juristische Zusagen abzugeben. Buchungsbelege ab 01.01.2025 haben i.d.R. 8 Jahre Aufbewahrung.

## Decision
- Rohdaten-Storage pro Rechnung:
  - original XML/PDF (unverändert)
  - SHA-256 Fingerprint
  - tenant_id, source, ingest timestamp
- Archivierungsmodell:
  - append-only Audit Events
  - hash chaining pro Dokument-Lifecycle
  - konfigurierbare Retention (`default_buchungsbeleg_years=8`)
- Evidence-Export (`audit-package.zip`):
  - raw invoice
  - validation report (JSON + text)
  - canonical snapshot
  - audit trail
  - export log/idempotency metadata

## Alternatives
1. Reines DB-Storage ohne unveränderliche Evidenzlogik
   - + Einfach
   - − Schwächerer Nachweis bei Prüfungen
2. WORM/Object Lock only
   - + Starke Unveränderbarkeit
   - − Infrastrukturabhängig, höherer Betriebsaufwand

## Consequences
- Mehr Speicherbedarf und Metadatenmanagement.
- Klare Prüfbarkeit und Recovery-Fähigkeit.

## Rollback / Exit
- Feature-Flag für hash chaining.
- Wenn Object Lock nicht verfügbar, bleibt append-only + Hash als Mindeststandard aktiv.

## Referenzen
- BGBl. 2024 I Nr. 323 (BEG IV): https://www.bgbl.de/
- IHK Hinweise Aufbewahrungspflichten: https://www.ihk.de/
