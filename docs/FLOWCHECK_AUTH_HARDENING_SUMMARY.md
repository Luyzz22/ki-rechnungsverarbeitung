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

## Routes Intentionally Left Public / Bootstrap

- `POST /api/v1/auth/token`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/users/register`
- `POST /api/v1/users/login`
- `GET /api/v1/email/status`
- `GET /api/v1/billing/plans`
- `POST /api/v1/billing/webhook`
- `POST /api/v1/auth/forgot-password`

These routes are intentionally public or bootstrap-oriented entry points, not protected business routes. They should remain unauthenticated unless the auth/product model changes, but each needs its own abuse controls and tests.

## Why These Routes Remain Public

- `POST /api/v1/auth/token`, `POST /api/v1/auth/refresh`, `POST /api/v1/users/register`, and `POST /api/v1/users/login` are authentication or onboarding entry points and must be reachable before a user has a token.
- `GET /api/v1/email/status` remains public as a non-sensitive configuration health signal. It no longer returns IMAP host, IMAP user, or other sensitive configuration values.
- `GET /api/v1/billing/plans` remains public so unauthenticated users can view available plans.
- `POST /api/v1/billing/webhook` remains public because Stripe must be able to call it directly; signature verification is delegated to `subscription_service.handle_webhook`.
- `POST /api/v1/auth/forgot-password` remains public because password recovery must be available before authentication. It preserves the generic response and must not reveal whether an account exists.

## Tenant Model

- `user.tenant_id` is canonical for authenticated routes.
- Optional `X-Tenant-ID` remains only as temporary client compatibility for authenticated routes.
- If `X-Tenant-ID` is present and differs from `user.tenant_id`, `_resolve_tenant_for_authenticated_request(...)` returns `403`.
- New protected route patches set `TenantContext` through the helper instead of treating the header as authorization.

## Validation

An AST-based route scan shows the following `/api/v1` routes without `Depends(get_current_user)`. These are intentionally public/bootstrap routes, not protected business routes:

```text
AST route scan: intentionally public/bootstrap routes without Depends(get_current_user):
- POST /api/v1/auth/token
- POST /api/v1/auth/refresh
- POST /api/v1/users/register
- POST /api/v1/users/login
- GET /api/v1/email/status
- GET /api/v1/billing/plans
- POST /api/v1/billing/webhook
- POST /api/v1/auth/forgot-password
```

Future route-auth audits must use AST-based route scanning rather than fixed line-window grep, because dependency declarations can move across multiple signature lines and line-window scans can undercount public routes.

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
