# FlowCheck+ — Modular API route auth audit

**Source of truth:** `modules/rechnungsverarbeitung/src/api/main.py` (router `v1` prefix `/api/v1`, plus `GET /api/v1/health` on the app).

**Related finding:** F-01 in `docs/FLOWCHECK_SECURITY_HOTFIX_PLAN.md` — many domain routes trust `X-Tenant-ID` without `Depends(get_current_user)`.

**Purpose:** Inventory every `/api/v1` route, classify intended auth posture, and record migration risk. **No mass route changes** should be done in a single patch; use this sheet to plan incremental hardening.

---

## Methodology

| Classification | Meaning |
|----------------|---------|
| **public_ok** | Intended to be callable without a logged-in user (or without JWT); may still use other controls (e.g. Stripe webhook signature). |
| **auth_required** | Must require an authenticated principal (JWT Bearer or configured `X-API-Key` per `get_current_user` in `modules/rechnungsverarbeitung/src/auth/jwt_auth.py`). Tenant should come from the token (or be validated against it), not only from a client-controlled header. |
| **admin_required** | **auth_required** plus tenant admin role (or equivalent); today some routes enforce `user.role == "admin"` inside the handler. |
| **unclear_needs_review** | Product / compliance unclear from code alone; treat as **blocker for enterprise** until PM/security signs off. |

**Current patterns observed in code:**

- **`_require_tenant(x_tenant_id)`** — requires non-empty `X-Tenant-ID` and calls `TenantContext.set_current_tenant`. Does **not** validate JWT.
- **`Depends(get_current_user)`** — resolves `UserAuth` from `Authorization: Bearer` or `X-API-Key` (`jwt_auth.get_current_user`).
- **`get_tenant_from_auth`** (in `jwt_auth.py`) — exists to prefer JWT tenant with header fallback, but is **not wired** into `main.py` handlers as of this audit.

**Recommended direction (per route, not blanket):** `Depends(get_current_user)` and use `user.tenant_id` as the effective tenant; optionally accept `X-Tenant-ID` only if it **matches** `user.tenant_id` (or drop the header for browser clients and use JWT only).

---

## Route inventory (every `/api/v1` route)

Full path = `/api/v1` + path below (router prefix + decorator path).

| Method | Path | Classification | Current auth mechanism | Tenant mechanism | Recommended auth dependency | Migration risk |
|--------|------|----------------|------------------------|------------------|-----------------------------|----------------|
| GET | `/health` | **public_ok** | None | None | None | **Low** — keep unauthenticated; ensure no sensitive data in response (today: API/DB status only). |
| POST | `/invoices/upload` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | `Depends(get_current_user)`; tenant from `user.tenant_id`; validate header if kept | **High** — upload clients may be header-only today. |
| GET | `/invoices/{document_id}/file` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** — file download must not rely on spoofable header alone. |
| POST | `/invoices/{document_id}/generate-xrechnung` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/budget/kategorien` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/budget/summary` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/budget/set` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** — mutating budget. |
| GET | `/budget/monat` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/validate-xrechnung` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/upload-batch` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/duplicate-check` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/anomaly-check` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/mark-duplicate` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same; **note:** side-effectful GET — consider POST in a follow-up | **High** |
| GET | `/export/csv` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** — bulk export. |
| GET | `/export/excel` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/generate-zugferd` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/skonto-check` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/analytics/supplier-scorecard` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/export/datev-zip` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/audit-log` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** — audit data sensitive. |
| GET | `/export-history` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/transition` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same — ties to approval / state machine | **High** |
| GET | `/invoices/{document_id}/transitions` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/events` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| GET | `/invoices/{document_id}/chain/verify` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/evidence` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same — GoBD evidence | **High** |
| POST | `/invoices/{document_id}/datev-export` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/validate` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/{document_id}/kontierung` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/invoices/datev-batch` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/copilot/chat` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same + optional rate limit / abuse controls | **High** — LLM path. |
| GET | `/analytics/dashboard` | **auth_required** | None | `X-Tenant-ID` + `_require_tenant` | Same | **High** |
| POST | `/auth/token` | **public_ok** | Demo credential check in handler | N/A (returns tokens with embedded `tenant_id`) | Optional: replace demo with real user store; add brute-force protection | **Medium** — contract change if clients expect unauthenticated abuse. |
| POST | `/auth/refresh` | **public_ok** | Body carries `refresh_token`; `decode_token` | N/A | Keep public; ensure refresh rotation / revocation policy elsewhere | **Medium** |
| GET | `/auth/me` | **auth_required** | **`Depends(get_current_user)`** | From JWT / API key | Already correct pattern | **Low** |
| POST | `/users/register` | **public_ok** | None at route | Handler creates tenant/user | Rate limit + CAPTCHA / email verification (product decision) | **Medium** |
| POST | `/users/login` | **public_ok** | `user_service.login` | Returns JWT | Brute-force protection | **Medium** |
| GET | `/users/profile` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| GET | `/users/team` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| POST | `/email/poll` | **auth_required** | **`Depends(get_current_user)`** | (implicit via user context in service) | Ensure poll also scopes by tenant in service layer | **Medium** |
| GET | `/email/status` | **auth_required** | **None** | N/A | **`Depends(get_current_user)`** — exposes IMAP config hints | **High** — **gap today:** unauthenticated disclosure risk. |
| GET | `/billing/plans` | **public_ok** | None | N/A | None | **Low** |
| GET | `/billing/subscription` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| POST | `/billing/checkout` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| POST | `/billing/portal` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| GET | `/billing/usage` | **auth_required** | **`Depends(get_current_user)`** | From JWT | None | **Low** |
| POST | `/billing/webhook` | **public_ok** | **Stripe signature** via `subscription_service.handle_webhook` | Resolved from Stripe payload | Dedicated dependency or middleware; never JWT | **Low** if webhook secret enforced; **critical** if secret missing (configure ops, not route table). |
| PUT | `/users/role` | **admin_required** | **`Depends(get_current_user)`** + `if user.role != "admin"` | From JWT | `require_role("admin")` or shared RBAC dependency | **Medium** |
| POST | `/users/invite` | **admin_required** | **`Depends(get_current_user)`** + admin check | From JWT | Same | **Medium** |
| DELETE | `/users/{user_id}` | **admin_required** | **`Depends(get_current_user)`** + admin check | From JWT | Same | **Medium** |
| POST | `/auth/forgot-password` | **public_ok** | None | N/A | Rate limit; audit email sends | **Medium** |

---

## Counts by classification

| Classification | Count |
|----------------|-------|
| public_ok | 8 |
| auth_required | 42 |
| admin_required | 3 |
| unclear_needs_review | 0 |

**Total routes in table:** 53 (`GET /api/v1/health` + 52 `v1` routes).

*(Classifications are conservative per FlowCheck+ guidance: invoice, export, audit, approval transitions, budget, analytics, copilot, and team-adjacent routes are **auth_required** even though code today often omits JWT.)*

---

## Highest-priority gaps (F-01 alignment)

1. **Header-only tenant:** All rows with migration risk **High** currently allow any caller who can reach the API to set `X-Tenant-ID` without proving membership of that tenant (subject to network exposure). Align with `Depends(get_current_user)` and JWT `tenant_id`.
2. **`GET /api/v1/email/status`:** No `Depends(get_current_user)` in `main.py`; response can reveal whether IMAP is configured and related metadata. Treat as **auth_required** in code next.
3. **`POST /api/v1/auth/token`:** Classified **public_ok** (reasonable for an OAuth-style login surface), but the in-handler demo credentials are **not** enterprise-ready—track replacement with real user lookup, brute-force limits, and observability as a separate hardening task (does not change the **public_ok** classification).
4. **Service accounts / machine clients:** If legitimate integrations require header-only access, document them and use **`X-API-Key`** path in `get_current_user` with explicit tenant binding instead of raw `X-Tenant-ID`.

---

## Suggested implementation order (incremental)

1. Add JWT to **`GET /email/status`** (small surface, clear leak).
2. Harden **read-heavy list/download** (`GET /invoices`, file download, exports) — highest blast radius on data exfiltration.
3. Harden **mutating** routes (upload, transition, budget set, DATEV, evidence).
4. Normalize admin routes to a shared **`require_role("admin")`** dependency to avoid drift.

---

## Uncertainty / open questions

- Whether **`POST /auth/token`** is kept for demos only or must remain a production OAuth2-style entry; affects rate limiting and credential store.
- Whether **browser** clients send only cookies vs Bearer tokens; may change how `get_current_user` is extended (cookie-based JWT not audited here).
- **Pen-test expectation:** Some routes may require **viewer** vs **editor** vs **admin** beyond the current binary `admin` check — needs RBAC matrix (out of scope for this file).

---

*Document generated from static analysis of `modules/rechnungsverarbeitung/src/api/main.py`. Re-run this audit when routes are added or prefixes change.*
