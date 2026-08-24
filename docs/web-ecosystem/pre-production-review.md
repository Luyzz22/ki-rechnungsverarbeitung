# Independent Pre-Production Review

Date: 2026-08-20
Reviewed: the extracted `sbs-web` repository at commit `0c82436`, read-only.
Method: source reading plus live probing — the build running behind real
nginx 1.24.0 — the version assumed at the time, see the correction under B1 —
the release artifact running standalone, and the previous public site probed to
establish the legacy URL inventory.

All BLOCKER and HIGH findings were fixed in `d6c9c94`. Every gate was re-run on
the resulting HEAD.

---

## Summary

| Severity | Found | Fixed | Accepted with rationale |
| --- | --- | --- | --- |
| BLOCKER | 3 | 3 | — |
| HIGH | 4 | 4 | — |
| MEDIUM | 8 | 6 | 2 |
| LOW | 4 | 3 | 1 |

Two findings would have broken the deployment outright: the nginx configuration
did not parse on the target's nginx version, and fifteen live URLs had no
redirect. Neither was visible from reading the repository alone — the first
needed nginx to actually run, the second needed the live site to be probed.

---

## BLOCKER

### B1 — `nginx -t` fails on the target host

`infra/nginx/sbs-web.conf` used `http2 on;`, introduced in nginx 1.25.1.
The production host was believed at the time to be Ubuntu 24.04, which ships
nginx 1.24.0, where the directive does not exist:

```
[emerg] unknown directive "http2" in sbs-web.conf:62
```

`enable-nginx.sh` would have refused to reload and reverted, so the switch would
have failed rather than broken anything. Still a blocker: the configuration as
written could not be applied.

**Fixed.** `listen ... ssl http2`, which is valid on 1.24 and only deprecated on
1.25+. `enable-nginx.sh` now reports the nginx version and warns on 1.25+.
Verified: `nginx -t` passes against real nginx 1.24.0.

> **Correction, 2026-08-20 (host inspection).** The premise of this finding was
> wrong. The production host is **Ubuntu 25.04 with nginx 1.26.3**, not 24.04
> with 1.24.0 — the version had been inferred from the OS rather than measured,
> and this review's own "not verified" table flagged that. On 1.26.3
> `listen ... ssl http2` is accepted but deprecated, so the repository now ships
> the modern `listen 443 ssl;` + `http2 on;` pair and `enable-nginx.sh` rewrites
> its **staged** copy back to the old form when it detects an nginx below
> 1.25.1. Compatibility is therefore kept deliberately rather than dropped, and
> `infra/tests/nginx-syntax-matrix.sh` proves both paths against real 1.26.3 and
> 1.24.0 binaries. The 1.24.0 evidence above remains accurate for what it
> tested.

### B2 — Fifteen live URLs would have returned 404

The redirect matrix had been written from the files on disk. Probing the live
site showed twelve reachable pages under `/static/landing/` with no mapping —
`integrationen`, `kunden`, `loesungen`, `loesungen-finanzleitung`,
`loesungen-handel-filialnetz`, `loesungen-steuerberater`, `preise`,
`referenzen`, `ressourcen`, `security`, `service-knowledge-os`, `support` — plus
three top-level entry points that answered 200: `/landing`, `/preise`,
`/loesungen`. A mapping also existed for `/static/landing/sicherheit.html`,
which never existed; the real page is `security.html`.

**Fixed.** All fifteen mapped, plus a catch-all for each legacy prefix so a 404
under them is structurally impossible. Verified through real nginx: 29 legacy
paths checked, all 301 to a live destination.

### B3 — Deployment built on the production host

`infra/scripts/deploy.sh` ran `npm ci` and `next build` on a 1 vCPU / 1.9 GiB host
that also runs the live invoice application. A Next.js build peaks well above a
gigabyte; an out-of-memory kill would have taken `invoice-app` with it.

**Fixed.** Replaced by `deploy-artifact.sh`, which only verifies and activates a
pre-built artifact. See `deployment.md`.

---

## HIGH

### H1 — The internal URL space was served under any hostname

A request carrying an unrecognised `Host` — including the bare IP — returned 200
for `/industrie/produkte`:

```
Host: evil.example.com   /industrie/produkte  ->  200
Host: 207.154.200.239    /industrie/produkte  ->  200
```

The proxy fell through for unknown hosts, and no nginx `default_server` existed,
so an unmatched Host landed on whichever server block nginx parsed first. The
consequence is duplicate content and a leaked internal routing scheme.

**Fixed** in two layers: the proxy returns 404 for the internal prefixes under
any unrecognised hostname (loopback exempt, so development and CI still work by
path prefix), and nginx gained a `default_server` that answers `444`.
`enable-nginx.sh` detects a pre-existing `default_server` and strips its own
rather than causing a conflict. Verified: all three probes now 404, and a
division host also 404s the *other* division's prefix.

### H2 — Security headers silently dropped on `/_next/static/`

nginx does not merge `add_header` across levels: a location that declares any
`add_header` discards every inherited one. The `/_next/static/` location set
`Cache-Control`, which meant every script and stylesheet shipped without CSP,
HSTS, `X-Content-Type-Options` or the rest.

**Fixed.** The header set lives in its own snippet, included both at server level
and inside each location that adds a header. Verified against the running build:
the static chunk now carries HSTS, CSP, nosniff and Cache-Control together.

### H3 — Duplicate and contradictory security headers

Testing through nginx showed four headers with two values each, because the
application set its own in `next.config.mjs` and nginx added more. Worst case:

```
x-frame-options: SAMEORIGIN     (from Next)
x-frame-options: DENY           (from nginx)
```

**Fixed.** nginx strips the upstream copies with `proxy_hide_header` and is
authoritative at the edge; the application keeps a baseline set so it is still
safe if run without a proxy, and its `X-Frame-Options` was aligned to `DENY`.
Verified: exactly one of each header, correct values, on both pages and assets.

### H4 — HSTS `includeSubDomains` from the apex

The audit recorded `chat.sbsdeutschland.com` serving an **expired certificate**.
`Strict-Transport-Security: … includeSubDomains` from `sbsdeutschland.com` would
have pinned every subdomain to HTTPS for a year, turning that expired
certificate into a hard failure with no user-side bypass, and would do the same
to any future internal subdomain without TLS.

**Fixed.** `includeSubDomains` removed, with the condition for re-enabling it
recorded in the snippet: every subdomain confirmed to serve valid TLS.

---

## MEDIUM

| # | Finding | Disposition |
| --- | --- | --- |
| M1 | `JsonLd` passed raw `JSON.stringify` to `dangerouslySetInnerHTML`. Data is not user-controlled, but a `</script>` in any future product string would break out of the element. | **Fixed** — escapes `<`, `>`, `&`. Verified: a payload containing `</script><img onerror=1>` serialises safely and parses back intact. |
| M2 | Cross-origin redirect target built by string concatenation. Not exploitable — `pathname` always begins with `/` — but the class of bug is avoidable. | **Fixed** — built with `new URL()`. |
| M3 | `www` and the apex both returned 200, separated only by a canonical tag. | **Fixed** — `www` now 301s to the apex. Verified through nginx. |
| M4 | CSP lacked `frame-src`, `worker-src`, `manifest-src`, `media-src` and `upgrade-insecure-requests`; `frame-ancestors` was `'self'` although the site is never framed. | **Fixed** — all added, `frame-ancestors 'none'`. |
| M5 | No rate limiting on a 1.9 GiB host shared with a live application. | **Fixed** — `limit_req` 20 r/s with burst 40, `limit_conn` 24. Verified that 30 rapid requests all pass. |
| M6 | `gzip_types` omitted XML, so `sitemap.xml` was served uncompressed. | **Fixed** — verified `content-encoding: gzip` on the sitemap. |
| M7 | `ExecStart=/usr/bin/node` hardcodes the interpreter path. | **Fixed** — `/usr/bin/env node`, and `deploy-artifact.sh` verifies node ≥ 20 before deploying. Extended 2026-08-20: `env node` resolves against *systemd's* PATH, so the script now resolves and checks that interpreter too, and runs the staging health check with it rather than with root's node. |
| M8 | `'unsafe-inline'` in `script-src`. | **Accepted.** Next.js App Router inlines its bootstrap; a nonce policy would force per-request rendering and give up static rendering entirely. Exposure is bounded: no user-generated content, no third-party script, no remote font, no inline event handler, and the one `dangerouslySetInnerHTML` now escapes. Recorded in the snippet. |
| M9 | The application trusts the `Host` header to select a site. | **Accepted** — that is the design, and it is now defended on both layers (H1). nginx sets `Host $host` from `server_name`-matched requests; unmatched hosts never reach the upstream. |

---

## LOW

| # | Finding | Disposition |
| --- | --- | --- |
| L1 | `server_tokens` left at default, leaking the nginx version. | **Fixed** — `server_tokens off`. |
| L2 | systemd unit lacked syscall filtering and namespace restrictions. | **Fixed** — `SystemCallFilter=@system-service`, `RestrictNamespaces`, `LockPersonality`, `RestrictSUIDSGID`, plus `MemoryHigh`, `CPUWeight` and `TasksMax` so the layer yields to `invoice-app`. Verified with `systemd-analyze verify`. |
| L3 | Next telemetry not disabled. | **Fixed** — `NEXT_TELEMETRY_DISABLED=1` in the unit. |
| L4 | `qa-report.md` still described the previous session's run. | **Fixed** — regenerated. |

---

## Areas reviewed with no finding

**Architecture.** Server/static boundaries are correct: 36 of 38 routes are
statically rendered; only `/robots.txt` and `/sitemap.xml` render per request,
because both read the `Host` header, and both are excluded from the proxy
matcher so they reach their route handlers directly. Corporate, industry and
legal isolation was probed in both directions.

**SEO.** Per-host sitemaps carry 11, 12 and 12 URLs with no cross-host leakage;
`robots.txt` advertises the matching sitemap per host; canonicals are generated
from the same `publicUrl()` the sitemap uses, so they cannot disagree.
Breadcrumb and organisation structured data emit only fields that can be
verified. Redirect chains were checked for loops — none.

**Security — secrets.** No `process.env` usage in `src/`, no `.env` file, no
credential in the repository or the artifact. `build-artifact.sh` refuses to
pack a tree containing `.env*`, `*.pem` or `id_rsa*`.

**Security — dependencies.** Three production dependencies (`next`, `react`,
`react-dom`), 32 transitively. `npm audit --omit=dev`: **0 vulnerabilities**.

**Security — external assets.** The only external hosts referenced anywhere in
`src/` are the SBS product domains linked from the pages, `schema.org` as a
JSON-LD context URI, and `ec.europa.eu` inside the verbatim Impressum text. No
CDN, no font host, no analytics, no chat widget.

**Security — open redirect.** Redirect targets come from a hardcoded origin map;
probes with `//evil.com`, `@evil.com` and `%2f%2fevil.com` all stayed on the
intended origin.

**Accessibility.** 25 routes: landmarks, contiguous heading order from a single
`h1`, accessible names on every link and button, no duplicate `id`, skip link as
first tab stop and visible on focus, visible focus on subsequent stops, mega
menu and mobile drawer operable by keyboard with Escape closing both, and zero
running animations under `prefers-reduced-motion`. **A11Y CLEAN.**

**Visual / UX.** 27 routes at six viewports — 162 renders: no horizontal
overflow, no interactive element under 36 px, exactly one `h1`, no page errors.
**ALL CLEAN.** Division consistency and distinctiveness were re-checked after the
product rename.

**Infrastructure.** The systemd unit is valid; the artifact runs on a fully
read-only release tree, which is what `ProtectSystem=strict` with an empty
`ReadWritePaths` produces. `enable-nginx.sh` backs up, tests and self-reverts;
`app.sbsdeutschland.com` is never read or written.

**Deployment.** The artifact is deterministic — fixed mtime, owner and sort
order — carries a provenance manifest, and is marked `-dirty` if the tree was
not clean. All twelve staging health checks were executed against a real
artifact. Rollback is a symlink move and is performed automatically if the
service fails to come up or if `invoice-app` is not active afterwards. The
artifact has no dependency on the source repository.

---

## Not verified in this review

| | Why |
| --- | --- |
| Behaviour under the host's own nginx configuration | No shell on the host. `enable-nginx.sh --check` must be run there before applying; it detects a `default_server` conflict and IPv6 availability, the two host-specific unknowns. It is genuinely read-only — it stages a complete candidate in a temporary prefix and validates it there — and `infra/tests/check-only-immutability.sh` hashes the whole tree before and after to prove it. |
| ~~Whether the host's nginx is really 1.24.0~~ | **Resolved 2026-08-20** — measured on the host: Ubuntu 25.04, nginx 1.26.3. The inference was wrong; see the correction under B1. |
| Lighthouse scores | Not available in this environment. |
| Automated colour-contrast measurement | Palette designed against WCAG 2.2 AA ratios but not machine-verified. |
| Real-user performance | Only lab measurements exist. |
