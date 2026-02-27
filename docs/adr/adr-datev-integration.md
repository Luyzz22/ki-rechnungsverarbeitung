# ADR: DATEV Integrationspfad für E‑Rechnungs‑Hub

## Context
Der Hub benötigt stabilen Export von Buchungssätzen plus Belegreferenzierung. Bestandscode enthält EXTF/CSV- und XML-orientierte Exportpfade.

## Decision
- **MVP primär: DATEV EXTF/CSV Export** aus stabilisiertem Adapter (geringster Integrationswiderstand).
- **Parallel vorbereiten:** Adapter-Vertrag für Buchungsdatenservice inkl. Idempotency-Key, Retry-Policy, Dead-letter Logging.
- Exportauftrag enthält:
  - tenant_id
  - invoice_ids
  - payload hash
  - idempotency key
  - retry_count/status

## Alternatives
1. Sofortiger Wechsel auf Buchungsdatenservice-only
   - + Zukunftsnäher
   - − Höheres Delivery-Risiko im MVP
2. Nur manueller CSV Download
   - + Sehr schnell
   - − Keine belastbare Automationsstory

## Consequences
- MVP wird schneller marktreif.
- Technische Schulden werden durch klaren Adapter-Vertrag kontrolliert.

## Rollback / Exit
- Bei Instabilität der Online-Schnittstelle: Rückfall auf EXTF-Downloadpfad ohne Datenverlust.
- Exportstatus bleibt auditierbar, erneuter Lauf via identischem Idempotency-Key möglich.

## Referenzen
- Buchungsdatenservice Interface Requirements: https://developer.datev.de/de/product-detail/accounting-extf-files/2.0/documentation/interface-requirements-for-buchungsdatenservice
- DATEV Products Overview: https://developer.datev.de/de/products
