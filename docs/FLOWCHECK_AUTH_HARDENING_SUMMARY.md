# FlowCheck+ F-01 Route Auth Hardening Summary

## Date

2026-05-04

## Summary

F-01 route-auth hardening for the modular API in `modules/rechnungsverarbeitung/src/api/main.py` is complete for the protected business route groups covered by the incremental security hotfixes. Protected invoice, budget, export, audit, analytics, evidence, validation, DATEV, kontierung, and copilot routes now require `Depends(get_current_user)` instead of trusting only `X-Tenant-ID`.

## Protected Route Groups Now Requiring `get_current_user`

- Invoice upload, batch upload, file download, invoice reads, transition reads/writes, event reads, and chain verification.
- Invoice checks and document generation routes, including duplicate check, anomaly check, mark duplicate, XRechnung, ZUGFeRD, Skonto, KoSIT validation, evidence package generation, DATEV export, DATEV batch export, and kontierung.
- Budget routes for categories, summary, monthly budget, and budget updates.
- Export and reporting routes for CSV, Excel, DATEV ZIP, audit log, export history, supplier scorecard, analytics dashboard, and copilot chat.
- Existing user, billing, and RBAC routes that already depended on `get_current_user` remain protected.

## Routes Intentionally Left Public

- `GET /api/v1/email/status`
- `POST /api/v1/billing/webhook`
- `POST /api/v1/auth/forgot-password`

## Why These Routes Remain Public

- `GET /api/v1/email/status` remains public as a non-sensitive configuration health signal. It no longer returns IMAP host, IMAP user, or other sensitive configuration values.
- `POST /api/v1/billing/webhook` remains public because Stripe must be able to call it directly; signature verification is delegated to `subscription_service.handle_webhook`.
- `POST /api/v1/auth/forgot-password` remains public because password recovery must be available before authentication. It preserves the generic response and must not reveal whether an account exists.

## Tenant Model

- `user.tenant_id` is canonical for authenticated routes.
- Optional `X-Tenant-ID` remains only as temporary client compatibility for authenticated routes.
- If `X-Tenant-ID` is present and differs from `user.tenant_id`, `_resolve_tenant_for_authenticated_request(...)` returns `403`.
- New protected route patches set `TenantContext` through the helper instead of treating the header as authorization.

## Validation

Focused F-01 route-auth scan output showed only the three intentionally public routes without `Depends(get_current_user)`:

```text
F-01 focused public routes without Depends(get_current_user):
- GET /api/v1/email/status
- POST /api/v1/billing/webhook
- POST /api/v1/auth/forgot-password
```

Compile check:

```text
python3 -m compileall modules/rechnungsverarbeitung/src/api/main.py
Compiling 'modules/rechnungsverarbeitung/src/api/main.py'...
```

## Remaining Follow-Ups

- Add rate limiting for `POST /api/v1/auth/forgot-password`.
- Add Stripe webhook signature verification tests.
- Add monitoring for `GET /api/v1/email/status` without exposing sensitive configuration.
- Eventually remove temporary `X-Tenant-ID` compatibility for authenticated routes and rely on `user.tenant_id` only.
