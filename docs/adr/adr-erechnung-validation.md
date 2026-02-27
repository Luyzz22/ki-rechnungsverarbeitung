# ADR: E‑Rechnung Validierungsstrategie

## Context
Für B2B-Inland muss der Hub strukturierte E-Rechnungen (XRechnung/ZUGFeRD) verarbeiten und belastbar validieren. Es braucht reproduzierbare, maschinenlesbare Reports für Audit/Prüfung.

## Decision
- Primärstrategie: **KoSIT Validator** mit **validator-configuration-xrechnung** über Subprocess/Docker-Runner.
- Fallback: parser-basierte Vorvalidierung (well-formedness + Pflichtfelder) nur als technische Vorprüfung, **nicht** als regulatorischer Ersatz.
- Persistenz pro Dokument:
  - `validation_status` (`passed|failed|warning`)
  - `validation_engine` + `config_version`
  - `report_json` + `report_text`
  - `validated_at`

## Alternatives
1. **Native Python-only Validation**
   - + Geringere Betriebsabhängigkeiten
   - − Hohe Pflegekosten, geringere Konformitätssicherheit
2. **Externer SaaS-Validator**
   - + Schnell startbar
   - − Vendor lock-in, Datenschutz/Hosting-Risiken

## Consequences
- Zusätzliche Runtime-Abhängigkeit (Java/Docker/CLI-Tooling).
- Dafür bessere Revisionsfähigkeit und regulatorische Nachvollziehbarkeit.
- Teststrategie: Fixture-basierte Positiv-/Negativfälle (xrechnung-testsuite).

## Rollback / Exit
- Feature-Flag `ERECHNUNG_VALIDATION_ENGINE=kosit|native`.
- Bei Betriebsstörung KoSIT: temporärer Fallback auf native Vorvalidierung mit „non-compliant-validation-mode“ Kennzeichnung.

## Referenzen
- KoSIT Validator: https://github.com/itplr-kosit/validator
- XRechnung Konfiguration: https://github.com/itplr-kosit/validator-configuration-xrechnung
- xrechnung-testsuite: https://github.com/itplr-kosit/xrechnung-testsuite
- BMF FAQ E-Rechnung: https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html
