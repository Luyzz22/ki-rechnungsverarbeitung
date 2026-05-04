# FlowCheck+ CSRF Hardening Plan for Legacy FastAPI App

## Current Finding

F-08 in `docs/FLOWCHECK_SECURITY_HOTFIX_PLAN.md` identifies missing CSRF protection in the legacy `web/app.py` stack. The legacy app uses `SessionMiddleware` and exposes many session-authenticated state-changing routes. Those routes are vulnerable to cross-site request forgery if a browser automatically sends the session cookie for a forged request.

## Why CSRF Matters Here

CSRF matters because the legacy app uses cookie-backed sessions for authenticated browser users. A malicious site can cause a logged-in user's browser to submit a `POST`, `PUT`, or `DELETE` request to the app unless the route checks an unguessable CSRF token that the attacker cannot read.

The risk is especially high for admin and finance workflows: user creation, settings changes, API key management, invoice approval/review, export actions, billing checkout, and organization/team changes can all change business state while relying on the user's existing browser session.

## High-Risk Route Groups

- Session-authenticated `POST`, `PUT`, and `DELETE` APIs in `web/app.py`.
- Admin user routes, including user creation, update, role/status changes, and deletion.
- API key, webhook, organization, team, and settings management routes.
- Billing checkout and cancel routes initiated from a logged-in user session.
- Invoice mutation, review, approval, export, and reprocessing routes.

## Routes That Must Remain CSRF-Exempt

- Stripe webhook endpoints.
- External webhook receiver endpoints that are called by third-party systems.
- Pure Bearer-token or API-key endpoints, where browser cookies are not the authentication mechanism.

Every exemption must be explicit and documented with the authentication mechanism that replaces CSRF protection, such as Stripe signature verification, webhook signing secret, Bearer token, or API key.

## Routes Requiring Special Treatment

- Login and registration routes:
  - Should eventually use CSRF protection for browser form submissions.
  - Must be tested carefully to avoid breaking first-time onboarding.
- Password-reset request and confirmation routes:
  - Must preserve generic responses and should use CSRF for browser forms.
  - Token values must never be logged.
- Contact and demo forms:
  - May remain public, but should use CSRF or an equivalent anti-abuse control if they submit from browser forms.
  - Should be combined with rate limiting or spam protection.

## Target Design

- Generate a signed CSRF token and store or bind it to the user's session.
- Render the token as a hidden input for server-rendered HTML forms.
- Require `X-CSRF-Token` for JSON or `fetch` requests from the browser.
- Exempt safe HTTP methods: `GET`, `HEAD`, and `OPTIONS`.
- Reject missing, invalid, expired, or mismatched tokens with a generic `403`.
- Do not log token values.

## Middleware vs Dependency Decision

Start with a dependency/helper approach, not global middleware.

Reason: the legacy route surface is large and mixed. It includes browser-session routes, public forms, Stripe webhooks, external webhooks, and API-key style endpoints. A global middleware patch would be easy to deploy incorrectly and could break payment/webhook/public flows. A helper or route dependency allows targeted protection of known browser-session mutation routes first, with an explicit exemption list.

Optional global middleware can be considered later once the route inventory and exemption allowlist are stable.

## Migration Strategy

### Phase 1: Inventory + Token Helper

- Inventory all `POST`, `PUT`, `PATCH`, and `DELETE` routes in `web/app.py`.
- Classify each route as session-browser, public form, webhook, API-key/Bearer, or unknown.
- Add CSRF helper functions:
  - create/generate token.
  - validate token.
  - expose token to templates.
  - validate `X-CSRF-Token` for JSON/fetch requests.
- Add tests for helper behavior before protecting routes.

### Phase 2: Protect Admin / Settings / API-Key / Org / Team Routes

- Add CSRF checks to admin user mutation routes.
- Add CSRF checks to settings and profile mutation routes.
- Add CSRF checks to API key and webhook management routes that are controlled from the browser UI.
- Add CSRF checks to organization and team mutation routes.

### Phase 3: Protect Invoice Mutation Routes

- Add CSRF checks to invoice review, approval, rejection, export, correction, and reprocessing actions when they are session-authenticated browser routes.
- Keep pure API-key/Bearer routes out of this phase unless they also accept session cookies.

### Phase 4: Protect Forms

- Add hidden CSRF inputs to login/register forms if they are rendered by the legacy app.
- Add hidden CSRF inputs to password reset request/confirm forms.
- Add hidden CSRF inputs to contact/demo forms or document equivalent anti-abuse controls.
- Add `X-CSRF-Token` to browser fetch calls that post JSON.

### Phase 5: Optional Middleware

- Consider global CSRF middleware only after route behavior is stable.
- Middleware must use an explicit exemption allowlist for Stripe webhooks, external webhooks, safe methods, and non-cookie API endpoints.

## Test Plan

- Helper tests:
  - valid token succeeds.
  - missing token fails.
  - malformed token fails.
  - token from another session fails.
  - expired token fails if expiration is implemented.
- HTML form tests:
  - rendered forms include hidden CSRF input.
  - valid form submission succeeds.
  - missing/invalid token returns `403`.
- JSON/fetch tests:
  - valid `X-CSRF-Token` succeeds.
  - missing/invalid header returns `403`.
- Exemption tests:
  - Stripe webhook remains callable and relies on signature verification.
  - external webhooks remain callable only with their existing signing/API-key mechanism.
  - safe methods `GET`, `HEAD`, and `OPTIONS` remain unaffected.
- Regression tests:
  - login/register still work.
  - password reset still works with generic responses.
  - admin user mutation now requires CSRF.
  - invoice approval/export mutation now requires CSRF.

## Rollback Plan

- Keep the first implementation route-scoped so rollback can remove the CSRF dependency/helper from affected routes without touching unrelated endpoints.
- If a critical browser flow breaks, temporarily remove CSRF from that route and keep audit logs for the failure.
- Never remove webhook signature verification as part of rollback.
- Do not roll back to broad public mutation access without an incident note and follow-up ticket.

## Enterprise SaaS Requirements

- Audit logging for CSRF validation failures:
  - include route, method, authenticated user ID if available, IP or request ID, and reason category.
  - do not log token values.
- No CSRF token logging in application logs, error traces, analytics, or audit details.
- Review session cookie `SameSite` mode:
  - `Lax` is usually a minimum for browser apps.
  - `Strict` may be appropriate for admin-only flows but can break cross-site redirects.
- Review CORS interaction:
  - credentialed cross-origin requests must use explicit origins.
  - CSRF does not replace CORS and CORS does not replace CSRF.
- Webhook exemptions must be documented with their compensating controls.

## Non-Goals

- No global CSRF middleware in the first patch.
- No breaking Stripe webhooks.
- No frontend rewrite.
- No replacement of existing auth/session architecture in this workstream.
- No changes to unrelated API-key/Bearer authentication flows unless route inventory shows they also accept browser session cookies.
