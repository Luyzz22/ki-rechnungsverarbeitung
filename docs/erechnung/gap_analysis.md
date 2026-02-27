# Gap-Analyse – Ist vs. E‑Rechnungs‑Hub MVP

## Ziel-MVP (Kurz)
Deterministische Pipeline: **received → validated → canonicalized → suggested → approved → exported → archived** inkl. tenant-sicherem Audit Trail und Evidence-Package.

## A) Inbound E-Rechnung Ingestion

### Ist
- Upload/API vorhanden.
- E-Rechnungs-Importlogik in `einvoice_import.py` vorhanden.

### Gap
- Einheitliche zentrale Eingangsschicht für XML/PDF/Email/API fehlt.
- Keine klare Formatklassifikation als First-Class State (`xrechnung|zugferd|pdf-sonstige`).
- Keine standardisierte Rohdatenablage mit Fingerprint/Hash + tenant binding als einheitliches Modell.

## B) Validation + Canonical Model

### Ist
- Parsing vorhanden, aber Validierung gegen KoSIT/XRechnung nicht zentral und revisionssicher persistiert.

### Gap
- Fehlender standardisierter Validierungsadapter (KoSIT bevorzugt).
- Kein verbindliches internes Canonical Schema mit Versionsfeld.
- Fehlende Persistenz von maschinenlesbarem + human-readable Validierungsreport.

## C) Workflow + Kontierungsvorschläge

### Ist
- Auto-Kontierung vorhanden.
- Status-/Workflow-Ansätze vorhanden.

### Gap
- Kein durchgehender State-Machine-Workflow speziell für E-Rechnung.
- Approval-Schritte nicht als klarer, testbarer Prozess mit deny-by-default RBAC modelliert.
- Audit-Events nicht überall konsistent an State-Transitions gekoppelt.

## D) DATEV Integration

### Ist
- DATEV-Exporter vorhanden (CSV/EXTF und XML-orientiert).

### Gap
- Produktisierter, idempotenter Exportfluss mit Retry-Strategie/Idempotency-Key nicht durchgehend.
- Fehlende klare Entscheidung/Abgrenzung EXTF vs. Buchungsdatenservice im Ziel-Flow.
- Dokumentbezug (Belegreferenzierung) nicht als durchgängige Evidence-Kette modelliert.

## E) Archivierung (GoBD/BEG IV)

### Ist
- Export-/ZIP-Funktionen vorhanden.

### Gap
- Revisionssichere, manipulationserschwerende Archivierung (hash-chain/append-only) fehlt als Standardpfad.
- Retention-Policy (Default 8 Jahre für Buchungsbelege ab 2025) nicht zentral konfiguriert/verifiziert.
- Audit Package (raw+validation+audit+export logs) nicht als standardisiertes Artefakt.

## F) Observability + Security

### Ist
- Audit/API/Health-Bausteine vorhanden.

### Gap
- KPI-Metriken für Hub fehlen (`validation_error_rate`, `export_success_rate`, `cycle_time`, `automation_rate`).
- Strukturierte, tenant-safe Logs mit PII-Redaction nicht flächendeckend standardisiert.
- RBAC-Autorisierungstests für neuen Hub-Flow fehlen.

## Priorisierte Umsetzungsreihenfolge
1. **Validation + canonical schema + report persistence** (hoch, regulatorisch kritisch).
2. **State machine + audit coupling + RBAC checks**.
3. **DATEV idempotent export adapter + retry**.
4. **Archivierung/Evidence package + retention policy**.
5. **Observability KPI metrics + dashboards**.
