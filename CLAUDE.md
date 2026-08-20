# sbs-web — Agent Instructions

> **Repository:** `SBS-Nexus/sbs-web` (private)
> **Scope:** public marketing and navigation layer for SBS Deutschland
> **Classification:** Internal — Engineering

---

## 1. What this repository is

One Next.js application serving three public hostnames:

```
sbsdeutschland.com              Corporate, platform, academy, labs, legal pages
industrie.sbsdeutschland.com    SBS Industrie
legal.sbsdeutschland.com        SBS Legal
```

It contains **no product logic**. It reads no product database, calls no product
API and holds no credentials. Every product application lives in its own
repository with its own deployment.

## 2. What this repository must never do

| Never | Why |
| --- | --- |
| Touch `app.sbsdeutschland.com` or the `invoice-app` service | It is a live application on the same host, on port 8000, with its own nginx server block. This layer runs on port 3100 and is independent. |
| Run `npm ci` or `next build` on the production host | The host has 1 vCPU and 2 GB RAM and runs a live application. Builds happen in CI; the host receives a verified artifact. See §7. |
| Add a secret, token, API key or `.env` value | The site is fully static and needs none. If a feature appears to need one, that feature belongs in a product repository. |
| Introduce a third-party script, tracker, font CDN or chat widget | The CSP forbids it and the pages are designed without it. |
| Publish a form without a working backend | The contact flow composes a pre-filled mail and says so. Do not replace it with a form that silently drops submissions. |
| Edit `src/content/legal/*` by hand | Generated verbatim from the reviewed source documents. Update the source and re-run `node scripts/extract-legal.mjs`. |

## 3. Content truth rules — enforced, not aspirational

`npm run check:content` fails the build on all of the following. Do not weaken
the patterns to make a claim pass; change the claim.

- Accuracy, time-saving or recognition quotas without a published measurement.
- Latency promises (`< 3 Sekunden` and similar).
- ISO / SOC 2 / BSI C5 / TÜV claims, until an audit is actually complete.
- Absolute security assurances (`100 % sicher`, `military grade`).
- `DSGVO-konform` or `GoBD-konform` as a product property. Conformity depends on
  contract, legal basis, DPIA, works council and operation — not on code. The
  checker allows the terms inside an explicit disclaimer, which is how the
  security and governance pages name what is *not* claimed.
- Marketing superlatives (`revolutionär`, `bahnbrechend`, `Marktführer`).
- Public status downgrades (`Coming Soon`, `Pre-Production`). Internal
  pre-production status is **not** a reason to grey out a product publicly —
  that is an explicit owner decision.
- The superseded product name `BelegFlow`.
- Emoji in page text.

Never invent customers, logos, certifications, KPIs, accuracy figures,
testimonials, benchmarks or SLAs. Every graphic showing data carries a `DEMO`
marker and uses synthetic values.

## 4. Product naming

| Product | Public name | Division |
| --- | --- | --- |
| Audit evidence | NormPilot Industrie | industry |
| Technical documentation | HydraulikDoc | industry |
| Contract analysis | KanzleiAI | legal |
| AI governance | ComplianceHub | legal |
| Invoice processing | **FlowCheck AI+** | cross_vertical |
| Release readiness | ReleaseProof | independent (SBS Labs) |
| Learning | PythonPfad, SQLPfad | academy |

Standing product-truth decisions, not to be reversed without evidence:

- **Service Knowledge OS** is the retrieval layer of HydraulikDoc, not a
  separate public product.
- **Contract Intelligence** is a component set inside KanzleiAI, not a separate
  public product.
- **AuftragsKI** is not published. No code, deployment or domain has been found
  for it. Publish only once one exists.
- `belegflow-ai.de`, `Luyzz22/belegflow-ai-site`, `ki-rechnungsverarbeitung`,
  `invoice-app` keep their names. Only the *public product name* is
  FlowCheck AI+.

## 5. Design system rules

- Colours, spacing, radii and durations are declared **only** in
  `src/design-system/tokens.css`. No component declares a raw value.
- Surfaces, text roles and borders are identical across all three sites. Only
  the accent ramp changes, via `[data-division]`.
- `--sbs-gold` marks exactly one thing anywhere on any site: **the step where a
  human decides**. Do not use it decoratively.
- Every animation needs a stated purpose (orient, explain, confirm, focus,
  reveal, delight) and a meaningful static state under
  `prefers-reduced-motion: reduce`.
- No animation library, no icon library, no raster images.
- Single-column grids must pin their base track to `minmax(0, 1fr)`, and wide
  content scrolls inside `.sbs-scroll-x`. Without both, a table or a rail sizes
  its grid track and pushes the page sideways on a phone.

## 6. Adding content

Everything the sites say about a product comes from `src/content/products.ts`.
Adding an entry there updates navigation, mega menus, cards, the footer,
listings, cross-sell, the sitemap and the link checker. A new product also needs
a route file, which is ~30 lines because the page is `ProductPage` plus any
product-specific section.

Solution pages are fully generated from `src/content/solutions.ts` and need no
route file at all.

Every claim added to the registry must be traceable to a source in the product's
own repository. Record it in `docs/web-ecosystem/product-map.md`.

## 7. Deployment rules

Artifact-based, always:

```
CI  →  npm ci  →  typecheck  →  lint  →  build  →  checks  →  tarball + SHA256
                                                                    ↓
host  →  verify SHA256  →  atomic release swap  →  systemctl restart  →  health check
```

- The production host receives an already verified runtime artifact. It does not
  install dependencies and does not compile.
- Releases are atomic: unpack beside the running one, health-check on a staging
  port, then swap.
- `infra/scripts/enable-nginx.sh` backs up the current nginx configuration,
  runs `nginx -t`, and restores automatically if the test fails. It never reads
  or writes the `app.sbsdeutschland.com` server block.
- Every deployment verifies that `invoice-app` is still active afterwards.
- Rollback is defined for every step and documented in
  `docs/web-ecosystem/deployment.md`.

## 8. Definition of done

Before reporting a change complete, run against a live build:

```bash
npm run typecheck
npm run lint
npm run build
npm start &
npm run check:links   -- http://127.0.0.1:3100
npm run check:content -- http://127.0.0.1:3100
```

For anything touching layout, navigation or a graphic, additionally verify in a
browser at 375, 768 and 1440 px: no horizontal overflow, one `h1`, visible
focus, keyboard-operable menus, and reduced motion.

State which gates ran and which did not. Do not report a gate as passing on the
strength of a successful compile.

## 9. Documentation

`docs/web-ecosystem/` is part of the deliverable, not an afterthought:

| File | Keep current when… |
| --- | --- |
| `architecture.md` | routing, stack or content model changes |
| `repository-map.md` | a product repository is added, retired or reclassified |
| `product-map.md` | any claim on any product page changes |
| `design-system.md` | tokens, type scale, motif or motion rules change |
| `domain-routing.md` | hostnames, DNS, TLS or canonicals change |
| `redirects.md` | a legacy URL is added or retargeted |
| `deployment.md` | the release or rollback procedure changes |
| `qa-report.md` | after every full verification pass |
