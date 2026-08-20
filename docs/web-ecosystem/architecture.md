# Web Ecosystem Architecture

## What this is

`sbs-web` is the public marketing and navigation layer for SBS Deutschland. It
serves three hostnames from one Next.js application:

```
sbsdeutschland.com              Corporate, platform, academy, labs, legal pages
industrie.sbsdeutschland.com    SBS Industrie
legal.sbsdeutschland.com        SBS Legal
```

It is deliberately **not** part of any product. The product applications keep
their own repositories, their own deployments and their own domains:

```
app.sbsdeutschland.com          FlowCheck AI+ (FastAPI, port 8000)  — untouched
app.normpilot-industrie.de      NormPilot
www.kanzlei-ai.com              KanzleiAI
releaseproof.com                ReleaseProof
pythonpfad.de / sqlpfad.de      SBS Academy
```

## Where it lives, and where it should live

The application is a self-contained workspace at `sbs-web/` inside
`Luyzz22/ki-rechnungsverarbeitung`. It has its own `package.json`, its own
build, its own systemd unit and its own nginx configuration; nothing in it
imports from the invoice application, and nothing in the invoice application
imports from it. The only coupling is the git repository.

That coupling is transitional. The brief asks for a dedicated `sbs-web`
repository, and no such repository exists in this session's scope. Creating a
new GitHub repository is an outward-facing action that was not part of the
branch mandate, so the code was placed where it is guaranteed to be reviewable
today, with a one-command extraction path:

```bash
# From a clone of ki-rechnungsverarbeitung
git subtree split --prefix=sbs-web -b sbs-web-extract
git push git@github.com:Luyzz22/sbs-web.git sbs-web-extract:main
```

After extraction the only change needed is the `Documentation=` line in
`infra/systemd/sbs-web.service`. Nothing else references the parent repository.

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Framework | Next.js 16, App Router | Static rendering for every marketing page, one small proxy for host routing |
| Language | TypeScript, strict | The product registry is typed; a wrong product slug fails the build |
| Styling | Tailwind CSS v4 with CSS custom properties | Division themes re-map tokens at runtime via `[data-division]`; no per-site stylesheet |
| Icons | Inline SVG | No icon library, no emoji as interface chrome |
| Motion | CSS keyframes and transitions only | No animation library ships to the browser; see `motion` in `design-system.md` |
| Fonts | Inter and IBM Plex Mono via `next/font/google` | Self-hosted at build time, no runtime request to a font CDN |

There is no client-side data fetching, no analytics vendor, no chat widget and
no third-party script. Two components are client components: the site header
(menu state) and the contact composer (form state). Everything else renders on
the server.

## Multi-site routing

One build, three hostnames, one public URL per page.

```
Internal route                              Public URL
/                                        →  sbsdeutschland.com/
/plattform/flowcheck                     →  sbsdeutschland.com/plattform/flowcheck
/industrie/produkte/normpilot            →  industrie.sbsdeutschland.com/produkte/normpilot
/legal/produkte/kanzleiai                →  legal.sbsdeutschland.com/produkte/kanzleiai
```

`src/proxy.ts` performs the mapping:

- On a **division host**, a clean path is rewritten to the internal path, and
  the internal path permanently redirects (308) to the clean one.
- On the **corporate host**, an internal division path permanently redirects to
  the division host, so the corporate origin never serves division content.
- On an **unknown host** (localhost, preview, health checks) nothing happens, so
  the whole ecosystem stays testable at a single origin.

`linkFor(currentPath, targetPath)` in `src/content/site.ts` is the single
function that decides how a link is rendered: relative and prefix-free within a
site, absolute across sites. Every link in the codebase goes through it — the
link checker crawls all three hostnames and fails if one does not.

### Why not three builds

Separate Next.js builds with `basePath` would give the same URLs and would also
work. One build was chosen because:

1. the design system, the product registry and the section primitives are shared
   verbatim, and a single build makes drift impossible;
2. one systemd unit and one nginx upstream is less to operate on a single
   4-core host than three;
3. adding a fourth site later is a route group plus one map entry.

The cost is that all three sites deploy together. That is acceptable for a
marketing layer and is what makes the homogeneity requirement (§99) enforceable
rather than aspirational.

## Content model

`src/content/` is the source of truth for everything the sites say about a
product:

```
types.ts        Product, Solution, PipelineStage, AcademyCourse
products.ts     The product registry — 6 entries
solutions.ts    10 problem-first solution pages
academy.ts      PythonPfad, SQLPfad
site.ts         Origins, titles, linkFor(), publicUrl()
legal/          Impressum and Datenschutz, extracted verbatim from the
                reviewed source documents by scripts/extract-legal.mjs
```

Navigation (`src/lib/nav.ts`), the footer, product listings, cross-sell blocks,
the sitemap and the link checker are all derived from these files. A product
appears on the site by being added to `products.ts`; nothing else needs editing.

## Directory layout

```
src/
├── app/                    Routes. /industrie/** and /legal/** are the division sites.
├── components/
│   ├── navigation/         Header, mega menu, mobile drawer, footer, wordmark
│   ├── sections/           Division split, foundation grid, solution page, contact
│   ├── product/            Product card, product page template
│   ├── graphics/           One graphic per product mechanism + shared frame
│   └── ui/                 Button, section primitives, rail divider
├── content/                Typed registries (above)
├── design-system/          tokens.css — the only place colours and spacing are defined
├── lib/                    nav, seo, routes
└── proxy.ts                Host-based routing
infra/
├── nginx/                  Site config, shared snippets, legacy redirect matrix
├── systemd/                sbs-web.service
└── scripts/                deploy.sh, enable-nginx.sh, issue-certs.sh
scripts/
├── check-links.mjs         Crawls all three hostnames, verifies external product URLs
├── check-content.mjs       Fails on unverifiable claims and marketing filler
└── extract-legal.mjs       Regenerates the legal content modules from the source documents
```

## Relationship to the invoice application

The new layer does not read, write, import or restart anything belonging to the
invoice application. In particular:

- `web/sbshomepage/` and `web/static/landing/` stay in place and keep working
  until the nginx switch is applied.
- The legacy redirect matrix lives in nginx, not in the application, so it can
  be rolled back independently of a deployment.
- `app.sbsdeutschland.com` has its own server block, which
  `infra/scripts/enable-nginx.sh` never touches. The deploy script verifies
  `invoice-app` is still active after every run.
