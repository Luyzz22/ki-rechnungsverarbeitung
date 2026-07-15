# Frontend-API-Vertrag (für die Next.js-SPA belegflow-ai.de)

Backend: `https://erechnung.sbsdeutschland.com` · Präfix: **`/api/app`**

## Authentifizierung
Cross-Domain → **JWT Bearer-Token** (keine Cookies):
```
Authorization: Bearer <token>
```
Token via Login/Register erhalten und im Frontend (z. B. `localStorage` +
`api-client.ts`) speichern. CORS erlaubt bereits `https://belegflow-ai.de`
und `https://www.belegflow-ai.de`.

## Endpunkte

| Methode | Pfad | Body / Query | Antwort |
|--------|------|--------------|---------|
| POST | `/api/app/login` | `{email, password}` | `{token, user}` |
| POST | `/api/app/register` | `{email, password, name?, company?}` | `201 {token, user}` |
| GET | `/api/app/me` | – | `{user}` |
| GET | `/api/app/dashboard/kpis` | – | `{count_today, count_month, count_quarter, automation_rate, total_invoices, open_approvals, oldest_age_hours, anomaly_alerts, trend[]}` |
| GET | `/api/app/invoices` | `?status=&q=&limit=&offset=` | `{total, limit, offset, items[]}` |
| GET | `/api/app/invoices/{id}` | – | Rechnungsobjekt · `404` wenn fremd/fehlend |
| GET | `/api/app/lieferanten` | `?sort=volumen\|risiko\|name` | `{suppliers[]}` |
| GET | `/api/app/lieferanten/{name}` | – | `{summary, invoices[]}` |
| GET | `/api/app/freigaben` | – | `{items[]}` (mit `age_hours`, `overdue`) |
| POST | `/api/app/freigaben/{id}/approve` | `{comment?}` | `{ok, status, final, next_role?}` |
| POST | `/api/app/freigaben/{id}/reject` | `{comment?}` | `{ok, status}` |
| GET | `/api/app/audit` | `?action=&date_from=&date_to=&limit=&offset=` | `{total, limit, offset, actions[], items[]}` |
| GET | `/api/app/audit/export.csv` | `?action=&date_from=&date_to=` | CSV-Download |

Fehlerformat: HTTP-Statuscode + `{ "detail": "..." }`.
- `401` nicht/ungültig authentifiziert · `404` nicht gefunden · `400/409` Validierung.

## `trend[]` (für Recharts)
`[{ "date": "YYYY-MM-DD", "count": <int> }]` (30 Tage, lückenlos). Linienfarbe `#003856`.

## Validierung (`GET /api/app/invoices/{id}`) — EINZIGE Quelle der Wahrheit

Das Detail-Objekt enthält ein bereits geparstes, angereichertes Feld
**`validierung`**. **Das Frontend rendert dieses Objekt direkt** und validiert
**nicht** clientseitig neu (keine eigene IBAN-/USt-Regex — das Backend prüft die
IBAN per echter mod-97-Prüfsumme und die USt-IdNr. länderspezifisch). Sowohl der
Validierung-Tab als auch das Compliance-Panel lesen **dasselbe** `validierung`-
Objekt, damit die Zahlen nie divergieren.

```jsonc
"validierung": {
  "ok": false,                 // Gesamtergebnis (keine error-Checks offen)
  "error_count": 1,
  "checks": [                  // direkt rendern: label + ok + severity + message
    { "name": "§14_rechnungsnummer", "ok": true,  "severity": "error",
      "label": "Rechnungsnummer", "category": "Pflichtangabe (§14 UStG)",
      "message": "Pflichtangabe fehlt: Rechnungsnummer" },
    { "name": "iban", "ok": true, "severity": "warning",
      "label": "IBAN", "category": "Prüfung", "message": "IBAN gültig" },
    { "name": "duplikat", "ok": false, "severity": "error",
      "label": "Duplikat", "category": "Prüfung",
      "message": "Identische Rechnung bereits vorhanden (ID 41)" }
  ],
  "pflichtangaben": {          // fürs Compliance-Panel (gleiche Zahl wie der Tab)
    "ok": 6, "total": 6, "geprueft": true, "vollstaendig": true },
  "summary": { "total": 9, "passed": 8, "failed": 1 }
}
```

- `validierung` ist `null`, wenn die Extraktion fehlschlug (Status `fehler`/
  `manuell_erforderlich`) — dann KEIN grünes Compliance-Ergebnis anzeigen.
- `severity`: `"error"` (blockierend) · `"warning"` (Hinweis) · `"info"`.
- `validierung_ok` (Top-Level) spiegelt `validierung.ok` (bzw. `null`).
- `validierung_json` (Rohstring) bleibt für Rückwärtskompatibilität erhalten,
  ist aber **deprecated** — nutzt `validierung`.

## Noch offen (Backend-Folgeaufgabe)
Diese SPA-Seiten brauchen noch Bearer-Endpunkte unter `/api/app` (bislang nur
session-/CSRF-basiert vorhanden):
- **Upload** (`POST /api/app/upload`, multipart) – inkl. Subscription-Check
- **DATEV** (`POST /api/app/datev/preview`, `POST /api/app/datev/export`)

Bis dahin: Upload-/Export-Seite als „bald verfügbar" kennzeichnen oder die
bestehenden session-basierten Endpunkte nur same-origin nutzen.

## Beispiel `src/lib/api-client.ts`
```ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "https://erechnung.sbsdeutschland.com";

function authHeaders(): HeadersInit {
  const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}/api/app${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers ?? {}) },
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<T>;
}
```
