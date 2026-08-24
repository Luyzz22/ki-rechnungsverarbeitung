# QA Report

Date: 2026-08-20 (second pass, after extraction, rename and hardening)
Build: `next build` (Next.js 16.3.1), 38 routes, all statically rendered except
`/robots.txt` and `/sitemap.xml`, which read the `Host` header.
Environment: local production build (`output: standalone`) on 127.0.0.1:3100,
Chromium 1194 via Playwright, and — new in this pass — real nginx 1.24.0 in
front of the build on all three hostnames. (1.24.0 was the version assumed for
the host at the time. The host was later measured as nginx 1.26.3; see the
third pass at the end of this document. The evidence below is accurate for what
it tested.)

Findings from the independent review are in
[`pre-production-review.md`](pre-production-review.md). All BLOCKER and HIGH
findings were fixed before these gates were re-run.

---

## Summary

| Gate | Result | Basis |
| --- | --- | --- |
| Corporate | **PASS** | Home + 10 subpages render, navigate and pass every automated check |
| Industry | **PASS** | Home + 9 pages incl. 2 product pages and 5 solution pages |
| Legal | **PASS** | Home + 9 pages incl. 2 product pages and 5 solution pages |
| Academy | **PASS** | Integrated at company level, both platforms reachable (HTTP 200) |
| Responsive | **PASS** | 27 routes × 6 breakpoints, zero horizontal overflow, zero undersized tap targets |
| Accessibility | **PASS** | 25 routes: landmarks, heading order, names, focus, skip link, keyboard menus |
| Reduced Motion | **PASS** | Zero running animations under `prefers-reduced-motion: reduce` |
| SEO | **PASS** | Per-host canonicals, sitemaps and robots; breadcrumb + organisation schema |
| Build | **PASS** | `next build` clean; `tsc --noEmit` clean; `eslint .` 0 errors, 0 warnings |
| Link Check | **PASS** | 55 pages across 3 hostnames, 0 dead internal links, 6/6 external product URLs 200 |
| Content Check | **PASS** | 23 routes, no unverifiable claims, no marketing filler, no emoji in page text |
| Security | **PASS** | 0 dependency vulnerabilities; headers verified through nginx; no secrets; no open redirect |
| nginx configuration | **PASS** | `nginx -t` against real nginx 1.24.0; routing, headers and 29 legacy redirects verified live. Re-validated in the third pass against nginx 1.26.3, the host's actual version |
| Release artifact | **PASS** | Deterministic tarball, runs standalone on a read-only tree, 12/12 deploy health checks |
| Production Deployment | **NOT RUN** | No shell on the target host in this session — see below |
| DNS | **NOT RUN** | The two `A` records do not exist yet — see below |
| TLS | **NOT RUN** | Certificate cannot be expanded before DNS resolves — see below |

---

## 1. Repository gates

```
tsc --noEmit          0 errors
eslint .              0 errors, 0 warnings
next build            38 routes
nginx -t              syntax ok, test successful (nginx 1.24.0)
systemd-analyze verify  no findings
build-artifact.sh     deterministic tarball + SHA256 + manifest
```

There is no test runner in this project; the automated gates are the three
scripts under `scripts/`, all of which run against a live build:

```
npm run check:links    -- http://127.0.0.1:3100
npm run check:content  -- http://127.0.0.1:3100
```

## 2. Primary journey

Exercised in Chromium with the three production hostnames mapped to the local
build through a TLS terminator, so `Host`-based routing, absolute cross-site
links and canonicals behaved exactly as they will in production:

| Step | Result |
| --- | --- |
| `https://sbsdeutschland.com/` | 200, canonical `https://sbsdeutschland.com` |
| Click "SBS Industrie ansehen" | → `https://industrie.sbsdeutschland.com/` |
| Click "Produkte ansehen" | → `.../produkte`, h1 "Produkte für technische Nachweis- und Dokumentenprozesse" |
| Click "NormPilot Industrie" | → `.../produkte/normpilot` |
| `https://legal.sbsdeutschland.com/` | 200, canonical `https://legal.sbsdeutschland.com` |
| Click "Produkte ansehen" → "KanzleiAI" | → `.../produkte/kanzleiai` |
| `industrie…/industrie/produkte/hydraulikdoc` | 308 → `industrie…/produkte/hydraulikdoc` |
| `sbsdeutschland.com/industrie/produkte/hydraulikdoc` | 308 → the industry host |
| `industrie…/governance` (a legal-only route) | 404 — correctly isolated |
| `industrie…/gibtsnicht` | 404 with the designed not-found page |

The contact flow was exercised on all three sites. It composes a pre-filled mail
carrying division, product or solution from the URL. **No form is published
against a backend that does not exist** (§61) — nothing is submitted anywhere,
and the page says so.

## 3. Responsive review

27 routes at 375×812, 430×932, 768×1024, 1024×768, 1440×900 and 1920×1080 —
162 page renders. Checked per render: document horizontal overflow, elements
extending past the viewport, interactive elements under 36px tall, exactly one
`h1`, and uncaught page errors.

**Result: ALL CLEAN.**

Two real defects were found and fixed during this pass:

1. The header CTA used `hidden sm:inline-flex` on a component whose base class
   already set `inline-flex`. Both are display utilities in the same cascade
   layer, so the unconditional one won and the button stayed visible at 375px,
   pushing the header 94px past the viewport. Fixed by wrapping rather than
   fighting specificity.
2. Single-column grids default to `auto` tracks, so a horizontally scrollable
   child (a table, a rail, a product graphic) sized the track and pushed the
   page sideways. Every base track is now pinned to `minmax(0, 1fr)`, and
   `.sbs-scroll-x` carries `min-width: 0`.

A third issue was a content problem rather than a layout one: the German
compound *Instandhaltungsentscheidung* could not fit a 375px line box at display
size. Fixed on both fronts — the display ceiling dropped from 82px to 72px with
`hyphens: auto` below `48rem`, and the headline was rewritten.

## 4. Accessibility

25 routes checked for: `<header>`/`<main>`/`<footer>`/labelled `<nav>`
landmarks, contiguous heading order starting at `h1`, accessible names on every
link and button, `<svg>` either `aria-hidden` or titled, no duplicate `id`,
skip link as the first tab stop and visible when focused, and visible focus on
the next eight tab stops.

**Result: A11Y CLEAN.**

Additionally verified once each:

| Check | Result |
| --- | --- |
| Mega menu via keyboard | Enter opens (`aria-expanded=true`), Escape closes and restores focus |
| Mobile drawer via keyboard | Enter opens the drawer, Escape closes it |
| Reduced motion | 0 running animations after load with `prefers-reduced-motion: reduce` |
| Colour independence | Every status uses a word plus a shape; the pass/fail marks in the ReleaseProof matrix carry `sr-only` text |
| Hover-only information | None — the product network updates its capability line on focus and announces it via `aria-live` |

Four defects were found and fixed:

1. The mobile drawer's group labels were `<h2>` elements sitting ahead of the
   page `<h1>` in document order. They are navigation group labels, so they are
   now `<p>` inside a labelled `<nav>` per group.
2. Duplicate `id` values where a `<Section id>` and its `SectionHeader id`
   collided (`academy`, `grenzen`, `datenweg`, `prozess`, `architektur`,
   `consulting`).
3. The skip link used `:focus-visible`; it now uses `:focus`.
4. Heading jumps `h1 → h3` on index pages. `ProductCard` and `FoundationGrid`
   now take a `headingLevel`, and the legal documents promote a leading `h3` to
   `h2` when no `h2` precedes it.

**Not verified:** automated colour-contrast measurement against WCAG 2.2 AA.
The palette was designed against the ratios (body text `#46606f` on `#ffffff`
is 6.1:1; inverse secondary `#a9c3d1` on `#001a29` is 9.6:1) but no axe or
Lighthouse contrast run was performed. This is the one accessibility claim in
this report that rests on design intent rather than measurement.

## 5. States and resilience

| State | Status |
| --- | --- |
| 404 | Designed page with six entry points and a report link; verified on all three hosts |
| Error boundary | `app/error.tsx` with a retry action, a home link and the error digest; uses a plain anchor deliberately so it survives a broken router |
| Empty | The product network's capability line has a defined resting message |
| Loading | Every page is statically rendered; `Suspense` boundaries wrap the contact composer, which reads search params |
| Broken media | No raster images ship — every graphic is inline SVG or CSS, so there is no broken-image state |
| Missing external target | `check:links` verifies all six external product URLs on every run |

## 6. Content and trust

`npm run check:content` fails the build on: accuracy or time-saving quotas,
latency promises, ISO/SOC 2/BSI C5/TÜV claims, absolute security assurances,
"DSGVO-konform"/"GoBD-konform" as a product property, marketing superlatives,
public status downgrades, and emoji in page text. Terms that appear inside an
explicit disclaimer are allowed, which is how the security and governance pages
are able to name what is *not* claimed.

**23 routes checked, 0 findings.**

Claims removed from the previous site and their replacements are documented in
`product-map.md`. In summary: "99.9 % Genauigkeit", "< 3s pro Dokument",
"94 % der deutschen Mittelständler" and the badge wall are gone, replaced by
mechanisms that can be shown in the product.

No customer logos, testimonials, certifications, awards, adoption numbers,
benchmarks or SLAs appear anywhere. Every graphic showing data is marked `DEMO`
and uses synthetic values. The Impressum and Datenschutzerklärung are rendered
verbatim from the reviewed source documents.

**AuftragsKI is not on the site.** It does not exist in any repository in
session scope — no source, no deployment, no domain. Building a product page
for it would have meant inventing a product.

## 7. Motion and media

Every animation is classified in `design-system.md` with its purpose and its
reduced-motion fallback. Verified:

- Entrance reveals complete within ~500ms; no primary content waits on one.
  (The Legal hero's review strip originally appeared at 1000ms and was
  shortened to 440ms during the polish pass.)
- No scroll hijacking, no pinned sections, no fake scroll container.
- No animation library ships — all motion is CSS keyframes and transitions.
- No WebGL, no 3D, no video, no canvas.

## 8. Performance

**Measured in the lab, not in the field.** These are local numbers from a
production build over loopback; they are not real-user data and should not be
presented as such.

Corporate homepage, first load, gzip — re-measured on this HEAD:

```
HTML                27 KB
JS + CSS           189 KB   (10 requests)
Fonts               66 KB   (3 woff2, self-hosted by next/font)
Total              283 KB
```

Server process: ~159 MB RSS under load in this environment, against
`MemoryHigh=384M` / `MemoryMax=512M` in the unit.

Uncompressed, per page: 564 KB JS, 56 KB CSS, 67 KB fonts, 0 KB images. The JS
is the Next.js App Router and React 19 baseline — the application adds two small
client components (site header, contact composer) and no libraries.

Navigation timings over loopback, six pages: DOMContentLoaded 31–49 ms,
**cumulative layout shift 0.0000 on every page**, 591–1152 DOM nodes.

**Not measured:** Lighthouse scores, LCP (no `largest-contentful-paint` entry is
recorded because the largest element is text that paints with the document),
and any field data. The §65 targets (Performance ≥ 90, Accessibility ≥ 95, Best
Practices ≥ 95, SEO ≥ 95, LCP < 2.5s, CLS < 0.1) are therefore **not claimed as
achieved** — only CLS has an actual measurement, and it is 0.

## 9. Visual polish

Two full passes were run after the first working render.

**Pass A — desktop.** Findings and fixes:

- Display type was too large for German headlines; the ceiling dropped from 82px
  to 72px and a `--triplet` variant was added for multi-sentence headlines.
- The hero grid was unbalanced; column ratios adjusted and the hero measure
  tightened to 39rem.
- The product network's rails did not meet the product nodes and the two
  division labels sat at different heights. The graphic was rebuilt with rails
  in the grid gaps and a shared label row.
- "SBS ENTERPRISE CORE" wrapped mid-phrase; the core panel was widened.
- The industry hero's fan connectors were nearly invisible; height and stroke
  increased.
- The cross-sell block rendered a single card in a two-column grid; it now
  switches to a single constrained column when only one product is related.

**Pass B — mobile.** Findings are listed under §3 above. All fixed.

## 10. What was not done, and why

| Item | Status | Reason |
| --- | --- | --- |
| Production deployment | Not run | This session had no shell on `207.154.200.239`. `CLAUDE.md` §2.1 restricts the workspace to `/var/www/invoice-app` and forbids `/etc`. Rather than working around that, the change is prepared as repository-managed configuration with an exact diff, a health-gated deploy script and a rollback — see `deployment.md`. |
| DNS records | Not created | `industrie.` and `legal.` do not resolve. Two `A` records at STRATO are needed; the exact values are in `domain-routing.md`. No existing record is modified. |
| TLS certificates | Not requested | Certbot cannot validate a hostname that does not resolve. `infra/scripts/issue-certs.sh` refuses to run until DNS is in place, then expands the existing certificate rather than issuing a second one. |
| Lighthouse | Not run | Lighthouse is not available in this environment. The measurements above are what was actually recorded. |
| Colour-contrast audit | Not run | See §4. |
| `SBS-Nexus/*` repositories | Not audited | Outside this session's repository scope. They are listed in `repository-map.md` with the note that none of them is the deployment target of a live domain found during the audit. |
| AuftragsKI product page | Not built | The product does not exist in any accessible repository. |
| Analytics | Not installed | §62 forbids adding an invasive tracker unasked. Event names are prepared as `data-analytics-event` attributes on the contact CTA; wiring them to a provider is a deliberate decision, not a default. |

## 11. Homogeneity and distinctiveness (§99, §100)

Three desktop screenshots side by side — corporate, industry, legal — share the
wordmark position, header height, grid, type scale, button shapes, section
rhythm, footer structure and motion vocabulary. What differs is the accent
(blue / teal / indigo), the hero graphic and the product content.

The distinctiveness test is met by content rather than by layout: within three
seconds an industry visitor sees documents, evidence matrices and asset
references; a legal visitor sees a contract, clause findings and a local-vs-cloud
data path. Neither could be mistaken for the other, and neither looks like a
different company.

## 12. Evidence

Screenshots captured at 1440×900 and 375×812 for: corporate, industrie, legal,
NormPilot, HydraulikDoc, KanzleiAI, ComplianceHub, Academy, Plattform,
FlowCheck AI+. They live in the session scratch directory rather than in the
repository, because committing 20 full-page PNGs would add several megabytes to
a repository that ships no raster assets by design. Regenerate them with:

```bash
npm run build && npm start &
node scripts/... # or any headless browser against http://127.0.0.1:3100
```

---

# Third pass — production-host hardening

Date: 2026-08-24. Branch `claude/production-host-hardening`. Run against the
**unpacked release artifact** on 127.0.0.1:3100 and, for the nginx gates,
through real nginx 1.26.3 — the production host's actual version.

Scope: infrastructure and deployment only. No application design or content was
changed. The one application-code change is `generateBuildId` in
`next.config.mjs`, which affects the build's identity, not its output.

| Gate | Result | Evidence |
| --- | --- | --- |
| `npm ci` | **PASS** | 0 vulnerabilities |
| Typecheck | **PASS** | `tsc --noEmit`, 0 errors |
| Lint | **PASS** | `eslint .`, 0 errors, 0 warnings |
| Build | **PASS** | 38 routes |
| Artifact reproducibility | **PASS** | `scripts/verify-reproducible.sh` — two clean builds, identical except three per-build key files |
| Links | **PASS** | 0 dead internal links, external product URLs 200 |
| Content / claim guard | **PASS** | 23 routes, 0 findings |
| Responsive | **PASS at 375+** | `npm run check:ui` — 150 page checks; see the 320px note below |
| Accessibility | **PASS** | 50 page checks; landmarks, lang, alt, svg labels, link names, heading order, visible focus |
| Reduced motion | **PASS** | no animation or transition over 100ms under `prefers-reduced-motion: reduce` |
| Security headers | **PASS** | `infra/tests/nginx-gates.sh` — six headers, exactly one value each, through real nginx; version not advertised |
| Legacy redirects | **PASS** | 41 paths, all 301; 35 destinations verified live, 6 point at `app.sbsdeutschland.com` and are deliberately not probed |
| Unknown Host | **PASS** | internal URL space unreachable |
| `--check` immutability | **PASS** | `infra/tests/check-only-immutability.sh`, plus a self-test proving the detector catches a mutating `--check` |
| nginx HTTP/2 syntax | **PASS** | `infra/tests/nginx-syntax-matrix.sh` against real 1.26.3 and 1.24.0 |
| Deployment scenarios B–F | **PASS** | `infra/tests/deploy-invoice-gate.sh` against the real artifact |

## Open finding: horizontal overflow at 320px

Five routes overflow horizontally at a 320px viewport:

```
sbsdeutschland.com/                                  14px
industrie.sbsdeutschland.com/                        52px
industrie.sbsdeutschland.com/produkte/hydraulikdoc   13px
legal.sbsdeutschland.com/                            31px
legal.sbsdeutschland.com/produkte/compliancehub      31px
```

**Not a regression.** The declared floor has always been 375px — the second
pass swept 375, 430, 768, 1024, 1440 and 1920, and all six still pass. 320px was
added to the sweep in this pass and had never been claimed.

Not fixed here: this hardening pass was scoped to the production host, and
changing five page layouts is a design change outside it. 320px is a real device
class (iPhone SE first generation and small Android phones), so this is worth
scheduling — it is recorded as open, not closed.

## Two sweeps that were ad-hoc are now scripts

The responsive, accessibility, header and redirect sweeps used to be written by
hand each pass. Re-writing them this time produced three findings that turned
out to be defects in the sweep, not the site:

- a route that does not exist (`/loesungen` on the corporate host — solutions
  live per division),
- `sr-only` radio inputs reported as 1×1 tap targets, when the 44px `<label>`
  around them is what a finger actually hits,
- every redirect destination re-requested on the corporate host, so the ones
  pointing at a division host or at `app.sbsdeutschland.com` looked dead.

They are now `scripts/check-ui.mjs` (`npm run check:ui`) and
`infra/tests/nginx-gates.sh`, so the numbers above can be reproduced rather than
taken on trust.
