# FlowCheck Tenant Processing Policy

Die Tenant Processing Policy ist die serverseitige Vorstufe vor Inference Policy, Provider Governance und Provider-Client-Instanziierung.

## Reihenfolge

1. Organisation/Tenant serverseitig bestimmen.
2. `resolve_tenant_processing_policy(...)` aufrufen.
3. Effektives Inference-Profil an den Inference-Policy-Guard geben.
4. Provider-Governance fuer regionale Cloud-Deployments pruefen.
5. Erst danach Provider-Client instanziieren.

HTTP-Body, Query-Parameter, Header, Cookies oder Tenant-User duerfen weder `cloud_processing_region`, `effective_inference_profile`, Provider-Allowlists noch Governance-Nachweise setzen.

## Organisationskontext

Aktive KI-, OCR-, Upload-, MBR-, Copilot- und Rechnungsverarbeitungspfade muessen vor dem Inference-Guard einen `TrustedOrganizationContext` aufloesen.

Vertrauenswuerdige Quellen sind:

- Legacy-Web-Session `user_id` plus `users.current_org_id` und `org_members`.
- Legacy-Rechnungs-/Job-Relation `invoices -> jobs -> user_id -> org_members`.
- Modularer API-Kontext aus bereits validiertem `UserAuth.tenant_id`.
- Explizit markierte Demo-Flows in Development/Test.

Nicht vertrauenswuerdig sind:

- `organization_id`, `org_id`, `tenant_id`, `cloud_processing_region` oder `inference_profile` aus HTTP-Body.
- Query-Parameter, Header, Cookies, JavaScript-Input oder Form-Daten.
- Provider-Freigaben, Evidence-Refs oder Allowlist-Werte aus Client-Input.

Fehlt der vertrauenswuerdige Organisationskontext, gilt:

- Production oder `FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION=true`: fail-closed mit `ORG_CONTEXT_REQUIRED`.
- Development/Test: nur explizit markierte Demo-Flows duerfen ohne persistierte Organisation laufen.

Client-Input bestimmt nie die effektive Datenregion und nie das effektive Inference-Profil.

## Regionen

`UNSET`

- Development/Test folgt den bestehenden Defaults.
- Production mit `FLOWCHECK_REQUIRE_EU_REGIONAL_CLOUD_IN_PRODUCTION=true` blockiert externe Provider.
- Bestehende historische Organisationen starten defensiv mit `unset`.

`EU`

- Erzwingt `EU_REGIONAL_CLOUD`.
- Erlaubt externe Verarbeitung nur ueber zentral freigegebene regionale Provider-Deployments.
- Direct OpenAI, Anthropic und Gemini bleiben verboten.

`LOCAL_ONLY`

- Erzwingt `SOVEREIGN`.
- Erlaubt nur lokale Provider.
- Solange lokale Provider nicht implementiert oder konfiguriert sind, endet der Flow fail-closed mit `SOVEREIGN_INFERENCE_UNAVAILABLE`.

`PROFESSIONAL_SECRECY`

- Ist kein Tenant-Processing-Policy-Wert.
- Darf nicht per Request, UI oder Organisationseinstellung aktiviert werden.
- Bleibt fuer spaetere Kanzlei-/KanzleiAI-Tiers reserviert.

## Persistenz

Die bestehende SQLite-Strategie nutzt idempotente Schema-Erweiterungen. `organizations.cloud_processing_region` wird mit Default `unset` vorbereitet. Alte SQLite-Datenbanken ohne diese Spalte bleiben lesbar und werden beim serverseitigen Resolver/Initializer defensiv erweitert.

Es gibt keine destruktive Migration und keine nachtraegliche Aenderung historischer Rechnungsdaten.

## Admin-Service

`set_organization_cloud_processing_region(...)` ist ein interner Service-Layer ohne UI. Er nutzt die bestehende Organisationsberechtigung:

- `owner` und `admin` duerfen setzen.
- `member` und `viewer` duerfen nicht setzen.
- Werte werden strikt gegen `CloudProcessingRegion` validiert.
- Effective Profile, Provider-Freigaben, Endpoint-Allowlists und Evidence-Refs sind nicht setzbar.

Eine spaetere API/UI-Integration muss denselben Service-Layer verwenden und darf keine Client-Felder direkt in den Resolver durchreichen.
