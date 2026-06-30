# FlowCheck Azure Egress Transition

Dieses Dokument beschreibt die Non-Production-Egress-Bruecke fuer FlowCheck auf
Hetzner zu Azure AI Services. Der Uebergangsmodus ist nicht fuer Produktion
freigegeben.

## Prinzip

1. Hetzner benoetigt eine feste ausgehende oeffentliche IP.
2. Diese IP wird ausschliesslich in Azure Network ACLs allowlisted. Diese
   Network ACLs beschraenken den eingehenden Zugriff auf Azure AI Services
   anhand der Hetzner-Egress-IP.
3. Azure AI Services stehen auf Default Deny.
4. Es gibt keinen offenen Internetzugriff fuer die Inference-Verarbeitung.
5. Die Python-Host-Allowlist ist nur eine logische App-Kontrolle und ersetzt
   keine Netzwerk-Egress-Kontrolle.

## Hetzner-seitige Zusatzkontrollen

- Eine normale Host-Firewall wie UFW oder nftables kann FQDN-Allowlisting nicht
  zuverlaessig allein durch statische IP-Regeln abbilden, weil
  Provider-IP-Bereiche und DNS-Aufloesungen sich aendern koennen.
- Eine belastbare ausgehende Zielhost-Beschraenkung benoetigt einen
  FQDN-faehigen Egress-Proxy, eine Firewall mit DNS-/FQDN-Policy oder einen
  kontrollierten Egress-Gateway-Ansatz.
- Ausgehende Regeln duerfen in Non-Production keinen technischen
  Egress-Nachweis vortaeuschen; sie sind ein zusaetzlicher Betriebsvertrag,
  nicht der Produktionsnachweis fuer private Konnektivitaet.
- DNS-Resolution fuer die Inference-Ziele kontrollieren.
- Kein allgemeiner Egress aus dem Inference-Service.
- Egress-Logs nur mit technischen Metadaten fuehren; keine Rechnungsinhalte,
  Prompts, Tokens oder Providerantworten loggen.

## Azure-seitige Regeln

- Network ACL Default Action bleibt `Deny`.
- Nur die freigegebenen statischen Hetzner-Egress-CIDRs duerfen als IP-Regeln
  eingetragen werden.
- Public Network Access ist nur im Non-Production-Uebergangsmodus vorgesehen.
- Fuer `PRIVATE_VNET_TARGET` wird Public Network Access deaktiviert und die
  Private-Endpoint-Parameter werden als Kontrakt vorbereitet.

## Zielzustand

Der Produktionszielzustand ist:

```text
Azure Worker oder Azure Container App im VNet
        |
Private Endpoint
        |
Azure OpenAI + Azure Document Intelligence
```

Alternativ muss ein explizit freigegebenes Hetzner-Azure-Site-to-Site-VPN oder
eine gleichwertig dokumentierte private Konnektivitaet vorliegen. Diese
Entscheidung liegt ausserhalb des Python-Codes.

## Rollback

- Azure Adapter deaktivieren.
- Provider-Governance-Enforcement bleibt auf Fail-Closed.
- Kein Fallback zu Direct OpenAI, Anthropic oder Gemini.
- Keine Lockerung auf allgemeinen Cloud- oder Internet-Egress.
