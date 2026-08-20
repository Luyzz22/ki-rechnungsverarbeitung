# AGENTS.md

Repository-level instructions for coding agents working on `SBS-Nexus/sbs-web`.

The full instruction set is in [`CLAUDE.md`](CLAUDE.md); this file is the
short form for tools that read `AGENTS.md`. Where the two appear to differ,
`CLAUDE.md` is authoritative.

## What this is

The public marketing and navigation layer for SBS Deutschland — one Next.js 16
application serving `sbsdeutschland.com`, `industrie.sbsdeutschland.com` and
`legal.sbsdeutschland.com`. No product logic, no credentials, no database.

## Setup

```bash
npm ci
npm run dev        # http://localhost:3100
```

During development the three sites are reachable by path prefix at one origin:
`/`, `/industrie/…`, `/legal/…`. In production the same routes are served
without the prefix under their own hostnames.

## Checks that must pass

```bash
npm run typecheck                                  # tsc --noEmit
npm run lint                                       # eslint
npm run build                                      # next build
npm start &                                        # port 3100
npm run check:links   -- http://127.0.0.1:3100     # 3 hostnames, external URLs
npm run check:content -- http://127.0.0.1:3100     # claim and naming guard
```

`check:content` is a truth gate, not a style gate. If it fails, correct the
claim — do not relax the pattern.

## Hard rules

1. Never touch the `invoice-app` service or `app.sbsdeutschland.com`.
2. Never run `npm ci` or `next build` on the production host — it has 2 GB RAM
   and runs a live application. Build in CI, ship a verified artifact.
3. Never add a secret, tracker, third-party script or font CDN.
4. Never invent customers, logos, certifications, KPIs or accuracy figures.
5. Never edit `src/content/legal/*` by hand — regenerate with
   `node scripts/extract-legal.mjs`.
6. Declare colours, spacing and durations only in
   `src/design-system/tokens.css`.
7. `--sbs-gold` marks one thing only: the step where a human decides.
8. The public product name for invoice processing is **FlowCheck AI+**.

## Where things live

```
src/content/      Typed registries — products, solutions, academy, site config
src/design-system/tokens.css   The only place design values are declared
src/components/   navigation, sections, product, graphics, ui
src/proxy.ts      Host-based routing for the three sites
infra/            nginx, systemd, deployment scripts
docs/web-ecosystem/   Architecture, product claims, design system, deployment
scripts/          Link checker, content checker, legal extraction, artifact build
```

## Reporting

State which gates ran and which did not. A successful compile is not evidence
that a page renders, that a link resolves or that a claim is true.
