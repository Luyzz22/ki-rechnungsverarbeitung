# FlowCheck Azure Non-Production Runbook

Dieses Runbook beschreibt die lokale Betriebsgrundlage fuer einen
Non-Production-Uebergang von FlowCheck auf Hetzner zu Azure OpenAI und Azure
Document Intelligence. Es erstellt keine Ressourcen und ersetzt keine
Azure-Deploymentfreigabe.

## Zielarchitektur fuer diese Phase

```text
FlowCheck FastAPI auf Hetzner
        |
Azure Arc system-assigned Managed Identity
        |
Azure OpenAI + Azure Document Intelligence
        |
Azure Firewall-Regeln: Default Deny + exakte statische Hetzner-Egress-Allowlist
```

Dieser Modus ist ausschliesslich fuer Non-Production vorgesehen. Der spaetere
Produktionszielzustand bleibt ein Azure Worker oder eine Azure Container App im
VNet mit Private Endpoints.

## Azure Arc Onboarding - Non-Production

1. Hetzner-Server manuell ueber Azure Arc onboarden.
2. Danach die system-assigned Managed Identity fuer den Arc-enabled Server
   aktivieren.
3. Principal ID manuell erfassen und ausschliesslich als
   Deployment-Parameter verwenden.
4. Azure OpenAI und Azure Document Intelligence erhalten nur die minimal
   notwendigen Inference-RBAC-Rollen.
5. Keine Azure CLI Developer Identity als Produktionsidentitaet verwenden.
6. Keine API Keys in Environment-Dateien eintragen.
7. Vor Aktivierung Anwendungskonto und Serviceprozess auf Managed-Identity-
   Zugriff testen.
8. Kein Token ausgeben, loggen oder in Runbooks kopieren.

## Parameter- und Rollenreview

- Die Beispielparameterdatei im Repository enthaelt nur Platzhalter.
- Eine echte Non-Production-Parameterdatei muss ausserhalb von Git gepflegt
  werden.
- Built-in-Role-Definition-IDs fuer Azure OpenAI und Document Intelligence
  muessen vor einem spaeteren Deployment im Azure Portal oder per Azure CLI
  verifiziert werden.
- Role Assignments duerfen nur auf die system-assigned Managed Identity des
  Workloads zeigen.
- Service Principal Credentials, Client Secrets und Zugriffsschluessel sind
  nicht Teil dieser Architektur.

## Vor Aktivierung

1. Lokalen IaC-Vertrag reviewen.
2. Lokalen Validator ausfuehren:

   ```bash
   ./.venv/bin/python scripts/validate_azure_nonprod_plan.py
   ```

3. Provider-Governance-Preflight ausfuehren:

   ```bash
   ./.venv/bin/python scripts/validate_provider_governance.py
   ```

4. Non-Production-Parameter durch Engineering, Betrieb und Datenschutz
   freigeben.
5. Manuelle Azure-Schritte nur in freigegebenem Non-Production-Kontext
   ausfuehren.

## Rollback

- Azure Adapter deaktivieren.
- EU-Regional-Cloud-Konfiguration auf blockierten Zustand setzen.
- Kein Fallback zu Direct OpenAI, Anthropic oder Gemini aktivieren.
- Keine Rechnungsinhalte oder Providerantworten in Fehlerausgaben oder Logs
  aufnehmen.

## Grenzen

Dieses Runbook beweist nicht, dass eine Azure-Region, ZDR, No-Training,
Private Networking oder Vertragslage tatsaechlich erfuellt sind. Diese Punkte
muessen durch Azure-Konfiguration, Netzwerkarchitektur, Beschaffung und
Datenschutzartefakte nachgewiesen werden.
