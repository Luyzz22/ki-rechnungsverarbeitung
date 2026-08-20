# Repository Map

Read-only inventory of every SBS repository reachable from this session, with
the role each one plays in the new web ecosystem. The classification comes from
each repository's own README, `PRODUCT.md`, source modules and live deployment —
not from the repository name, which turned out to be misleading in two cases.

Legend for **Division**: `industry`, `legal`, `cross_vertical`, `academy`,
`independent`, `internal`.
Legend for **Role**: `product`, `frontend`, `backend`, `platform`,
`marketing_site`, `internal_tool`, `legacy`.

---

## Marketed products

| Repository | Product | Division | Role | Source of truth | Public/App domain | Used in the new web |
| --- | --- | --- | --- | --- | --- | --- |
| `Luyzz22/normpilot-industrie` | NormPilot Industrie | industry | product | yes | `app.normpilot-industrie.de` (200) | `industrie.sbsdeutschland.com/produkte/normpilot`, primary CTA links to the app |
| `Luyzz22/sbs-service-knowledge-os` | **HydraulikDoc** | industry | product | yes | no public marketing domain | `industrie.sbsdeutschland.com/produkte/hydraulikdoc` |
| `Luyzz22/sbs-hydraulikdoc` | HydraulikDoc (predecessor) | industry | legacy | no — superseded | — | Not marketed separately; documented as the earlier generation |
| `Luyzz22/kanzlei-ai` | KanzleiAI | legal | product | yes | `www.kanzlei-ai.com` (200) | `legal.sbsdeutschland.com/produkte/kanzleiai`, primary CTA links to the app |
| `Luyzz22/Compliance-Hub` | ComplianceHub | legal | product | yes | no public domain resolved | `legal.sbsdeutschland.com/produkte/compliancehub` |
| `Luyzz22/ki-rechnungsverarbeitung` | BelegFlow | cross_vertical | product + backend | yes | `app.sbsdeutschland.com` (200) | `sbsdeutschland.com/plattform/belegflow`, linked from Industrie |
| `Luyzz22/belegflow-ai-site` | BelegFlow (website generation) | cross_vertical | marketing_site | no — not deployed | `belegflow-ai.de` did not respond | Naming input only — see the open decision below |
| `Luyzz22/releaseproof-web` | ReleaseProof | independent | marketing_site | yes | `releaseproof.com` (200) | `sbsdeutschland.com/labs/releaseproof` |
| `Luyzz22/releaseproof-jira` | ReleaseProof (Forge app) | independent | product | yes (app side) | Atlassian Forge | Same page; the Forge trust boundary is described there |

## Not marketed as separate products

| Repository | Why not | Where it appears instead |
| --- | --- | --- |
| `Luyzz22/contract-analyzer-backend` | FastAPI contract-analysis backend, last commit 2026-02. Superseded by the KanzleiAI pipeline (`src/lib/ai/**`). Marketing it would create a fourth Legal "product" that is really an earlier backend. | Named as a predecessor on `legal.sbsdeutschland.com/produkte` |
| Contract Intelligence | Not a repository of its own in scope. It exists as a component set in `kanzlei-ai/src/components/contract-intelligence/` (and a copy in `normpilot-industrie`). | A section inside the KanzleiAI product page |
| `Luyzz22/sbs-workflow-autopilot` | Internal workflow/step-orchestration MVP (Invoice → Contract → Approval → DATEV → Audit). No public surface, no marketing claim we can evidence. | Not linked |
| `Luyzz22/sbs-gtm-automation` | Internal go-to-market tooling. | Not linked |
| `Luyzz22/sbs-workflows` | Repository contains no commits on the working branch. | Not linked |

## Products named in the brief that do not exist in accessible repositories

| Name | Finding | Consequence |
| --- | --- | --- |
| **AuftragsKI** | No match for `auftragski` / `auftrags-ki` in any file of the 13 repositories in session scope. No deployment, no domain, no source. | **Not built and not marketed.** Adding a product page would have meant inventing a product. Add the repository to the session and it can be modelled in `src/content/products.ts` in one commit. |
| **PythonPfad / SQLPfad** | No repository found in scope; both sites are live (`pythonpfad.de`, `www.sqlpfad.de`, HTTP 200). | Marketed as **SBS Academy** with their own brands and their own domains as the primary destination — as §34 requires. |

## Source-of-truth resolution: HydraulikDoc vs. Service Knowledge OS

The two repository names are swapped relative to their contents:

- `Luyzz22/sbs-hydraulikdoc` — `README.md` reads **"SBS Service Knowledge OS"**;
  `app.py` is a Streamlit app on LlamaIndex + LlamaParse + Qdrant + GPT-4o.
  Last commit 2026-01-28.
- `Luyzz22/sbs-service-knowledge-os` — `README.md` reads **"HydraulikDoc
  Enterprise"**; `PRODUCT.md` is the "HydraulikDoc Enterprise Product
  Definition", baseline 5.0 of 2026-08-14. Azure-only production path, Entra
  ID, PostgreSQL FORCE RLS, citation validation, human review, lifecycle job.
  Last commit 2026-08-15.

**Decision.** They are two generations of one product, not two products.
`sbs-service-knowledge-os` is the canonical, current implementation and is
marketed as **HydraulikDoc**. "Service Knowledge OS" is treated as the earlier
working title of the retrieval layer and is described as a capability inside
HydraulikDoc rather than as a third industry product. Criteria applied, in the
order given by §12: current production architecture, current product
functionality, commit activity, repository documentation.

The `SBS-Nexus/*` organisation copies named in the brief
(`sbs-nexus-platform`, `sbs-contract-intelligence`, `sbs-finance-intelligence`,
`SBS-Nexus/sbs-hydraulikdoc`, `SBS-Nexus/ki-rechnungsverarbeitung`) were **not**
in this session's repository scope and were therefore not inspected. They appear
in `list_repos`, so they can be added and audited in a follow-up without
changing any decision above — none of them is the deployment target of a live
domain we found.

## Open decision for the owner

`belegflow-ai-site` publishes itself as **"FlowCheck AI+"**
(`src/app/layout.tsx`, `metadataBase: https://belegflow-ai.de`), while the
running application at `app.sbsdeutschland.com` calls itself **"SBS
KI-Rechnungsverarbeitung"**. Neither `belegflow.de` nor `belegflow-ai.de`
responded during the audit.

The new web layer uses **BelegFlow**, because that is the name the brief itself
uses and the repository name of the marketing generation. Changing it is a
one-line edit in `src/content/products.ts` (`name`, `shortName`) — every
navigation entry, card, footer link and cross-sell follows automatically.

## Live status recorded during the audit (2026-08-20)

| URL | Result |
| --- | --- |
| `https://sbsdeutschland.com` | 200, redirects to `/sbshomepage/` |
| `https://www.sbsdeutschland.com` | 200, redirects to `/sbshomepage/` |
| `https://app.sbsdeutschland.com` | 200, redirects to `/login` |
| `https://industrie.sbsdeutschland.com` | does not resolve — DNS record required |
| `https://legal.sbsdeutschland.com` | does not resolve — DNS record required |
| `https://app.normpilot-industrie.de` | 200 — "Audit Evidence Command Center" |
| `https://www.kanzlei-ai.com` | 200 — "KanzleiAI — KI-Vertragsanalyse für juristische Teams" |
| `https://releaseproof.com` | 200 |
| `https://pythonpfad.de` | 200 |
| `https://www.sqlpfad.de` | 200 |
| `https://www.sbsnexus.de` | 200 |
| `https://chat.sbsdeutschland.com` | TLS certificate expired — **not linked from the new site** |

All DNS records for `sbsdeutschland.com`, `www` and `app` point at
`207.154.200.239`.
