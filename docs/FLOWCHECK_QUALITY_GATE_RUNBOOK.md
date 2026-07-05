# FlowCheck Quality Gate Runbook

Dieses Runbook beschreibt die lokale und GitHub-Action-basierte
Quality-Gate-Pipeline fuer FlowCheck. Das Gate fuehrt keine Deployments aus,
meldet sich nicht bei Azure an und ruft keine externen KI-Provider auf.

## Lokal starten

Aus dem Repository:

```bash
./.venv/bin/python scripts/run_quality_gate.py
```

Der Runner verwendet den Python-Interpreter, mit dem er gestartet wurde. Im
Repository ist das die lokale virtuelle Umgebung.

## Statuscodes

- `QUALITY_GATE_START`: Gate gestartet.
- `CHECK <NAME> status=PASS`: Einzelpruefung erfolgreich.
- `CHECK <NAME> status=FAIL exit_code=<N>`: Einzelpruefung fehlgeschlagen.
- `CHECK BICEP_TOOL_NOT_FOUND status=SKIP`: Lokale Bicep-CLI nicht gefunden;
  lokal ist Bicep optional.
- `QUALITY_GATE_PASS`: Alle verpflichtenden lokalen Pruefungen bestanden.
- `QUALITY_GATE_FAIL`: Mindestens eine verpflichtende Pruefung fehlgeschlagen.

Der Runner gibt keine Roh-Ausgaben von Tests, Preflights, Validatoren oder
Bicep aus. Dadurch werden Konfigurationswerte, Endpoints, IDs und Secrets nicht
versehentlich in die lokale Ausgabe uebernommen.

## Gepruefte Bereiche

- Python-Syntax der zentralen Inference-, Governance-, Preflight- und
  Azure-Adapter-Dateien.
- Vollstaendige Python-Testsuite.
- Production-Governance-Preflight.
- Azure-Non-Production-IaC-Validator.
- Bicep Build, Build-Params und Lint, falls Bicep lokal installiert ist.
- `git diff --check`.

## Lokal optional, CI verpflichtend

Lokal ist Bicep optional: fehlt die CLI, meldet der Runner
`BICEP_TOOL_NOT_FOUND` und das Gate kann trotzdem erfolgreich enden.

In GitHub Actions ist Bicep verpflichtend. Der Workflow installiert die Bicep
CLI im CI-Runner und fuehrt Build, Build-Params und Lint aus. Es erfolgt keine
Azure-Anmeldung und kein Deployment.

## Grenzen

Das Quality Gate ist kein Ersatz fuer:

- Azure `what-if`.
- Azure-RBAC-Review.
- Reale Non-Production-Integrationstests.
- Netzwerk- oder Private-Endpoint-Nachweise.
- Datenschutz-, Beschaffungs- oder Betriebsfreigaben.

## Bei Fehlschlag

1. Fehlgeschlagene Statuszeile identifizieren.
2. Den konkreten Teil lokal separat ausfuehren, ohne Secrets oder echte
   Konfigurationswerte in Ausgaben zu kopieren.
3. Nur die belegbare Ursache korrigieren.
4. Quality Gate erneut ausfuehren.
