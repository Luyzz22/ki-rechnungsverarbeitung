# FlowCheck+ Production Activation Checklist

Diese Checkliste beschreibt die Voraussetzungen, bevor FlowCheck+ im produktiven
EU-Regional-Cloud-Modus fuer Eingangsrechnungen aktiviert wird. Sie ersetzt
keine vertragliche, organisatorische oder infrastrukturelle Freigabe.

## Code prueft

Der lokale Production-Preflight ist rein konfigurationsbasiert. Er fuehrt keine
Netzwerkzugriffe aus, ruft keine Azure-Credentials ab und instanziiert keine
Provider-Clients.

- Produktionsmodus mit aktivierter Regional-Cloud-Pflicht blockiert
  `STANDARD` als Default-Inference-Profil.
- `FLOWCHECK_PROVIDER_GOVERNANCE_ENFORCEMENT` muss `block` sein.
- Die zentrale Provider-Endpoint-Host-Allowlist darf nicht leer sein.
- Jeder aktive EU-Regional-Provider benoetigt einen exakten Host aus der
  serverseitigen Allowlist.
- Die Processing-Region muss explizit gesetzt sein und darf nicht `global`,
  `datazone`, `auto`, `default` oder leer sein.
- Modell-Deployment-ID und Modellversion muessen gesetzt und gepinnt sein.
- Floating-Werte wie `latest`, `default`, `auto` und `current` werden blockiert.
- `provider_governance_approved` muss serverseitig `true` sein.
- `retention_evidence_ref` und `no_training_evidence_ref` muessen gesetzt sein.
- Wenn Azure als aktiver Regional-Provider konfiguriert ist, muessen die Azure
  Adapter aktiviert sein.
- Azure Identity muss `managed_identity` verwenden.
- Developer Credentials duerfen in Produktion nicht erlaubt sein.
- Fehlerausgaben enthalten nur Fehlercodes und Feldnamen, keine
  Konfigurationswerte.

## Betrieb / Infrastruktur prueft

Die folgenden Punkte koennen nicht allein durch Python-Code nachgewiesen werden.
Sie muessen durch Beschaffung, Betrieb, Datenschutz und Infrastrukturartefakte
belegt werden.

- Azure-Ressourcen sind in einer freigegebenen EU-Region bereitgestellt.
- Microsoft Entra RBAC ist fuer die produktive Workload-Identitaet korrekt
  eingerichtet.
- Managed Identity ist auf dem produktiven Worker oder ueber Azure Arc
  verfuegbar.
- Netzwerk-Egress wird ausserhalb des App-Codes durch Firewall, Proxy oder
  Cloud-Network-Controls beschraenkt.
- Private Endpoint oder eine klar dokumentierte statische
  Hetzner-Egress-IP-Freigabe ist umgesetzt.
- Retention-, ZDR- und No-Training-Nachweise liegen als interne Artefakte vor.
- AVV/DPA und Subprozessorpruefung sind abgeschlossen.
- Eine DSFA-Vorpruefung wurde dokumentiert.
- Ein Non-Production-Integrationstest gegen isolierte Ressourcen wurde
  bestanden.
- Canary-Tenant, Monitoring und ein Rollback-Runbook ohne Direct-Provider-
  Fallback sind freigegeben.

## Aktivierungsablauf

1. Governance-Artefakte pruefen und Referenz-IDs in der serverseitigen
   Deployment-Konfiguration hinterlegen.
2. Endpoint-Host-Allowlist und Provider-Deployment-Konfiguration reviewen.
3. Non-Production-Integrationstest ausfuehren.
4. Lokalen Production-Preflight ausfuehren:

   ```bash
   python3 scripts/validate_provider_governance.py
   ```

5. Canary-Tenant aktivieren und Monitoring pruefen.
6. Produktive Aktivierung erst nach Engineering-, Betriebs- und
   Datenschutzfreigabe vornehmen.

## Grenzen

Der Code erzwingt logische Policy-, Profil-, Allowlist-, Modell-Pinning- und
Evidence-Referenzpflichten. Er beweist nicht eigenstaendig Region, ZDR,
No-Training, AVV/DPA, Private Networking oder tatsaechliche Egress-Isolation.
