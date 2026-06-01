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
