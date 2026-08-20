# Product Map

What each product page claims, and where in the source that claim comes from.
Nothing on the sites asserts a capability that is not traceable to one of these
locations. Where a mechanism is documented but its operational evidence is a
release gate, the page says so instead of implying the gate is passed.

---

## SBS Industrie

### NormPilot Industrie

- **Route** `industrie.sbsdeutschland.com/produkte/normpilot`
- **Repository** `Luyzz22/normpilot-industrie`
- **Application** `https://app.normpilot-industrie.de`
- **Graphic** `EvidenceMatrixGraphic`

| Claim on the page | Source |
| --- | --- |
| Requirement Sets and Requirement Items instead of standard full texts | `README.md` MVP scope; `src/lib/normpilot/matrix-core.ts` |
| Evidence Mapping with a recorded source location | `src/lib/normpilot/evidence-core.ts` |
| Gap Findings with severity | `src/lib/normpilot/gap-core.ts` |
| Corrective Actions with ownership and status | `src/lib/normpilot/action-core.ts` |
| Human Review before release | `src/lib/normpilot/evidence-pack-review.ts` |
| Evidence Pack export in Markdown and CSV, with provenance | `src/lib/normpilot/export-core.ts`, `export-structure.ts` |
| AuditEvent logging, tamper-evident trail | `README.md` GoBD section |
| Tenant isolation and provider-call protection covered by offline smoke tests | `README.md`; `scripts/normpilot-smoke-check.mjs` |
| No standard full texts, no certification verdict, no ERP/QMS write-back | `README.md` "Nicht enthalten" and "Normlizenz" |

**Not claimed**: audit pass guarantee, certification, ERP integration,
accuracy figures.

### HydraulikDoc

- **Route** `industrie.sbsdeutschland.com/produkte/hydraulikdoc`
- **Repository** `Luyzz22/sbs-service-knowledge-os` (canonical); predecessor
  `Luyzz22/sbs-hydraulikdoc`
- **Graphic** `ManualRetrievalGraphic`

| Claim on the page | Source |
| --- | --- |
| Asset registry with location and criticality | `PRODUCT.md` Kernabläufe 1 |
| Upload validation, malware scan, private storage | `hydraulikdoc/security.py`, `azure_ai.py` |
| Layout extraction preserving tables | `PRODUCT.md` Capability Contract |
| Hybrid retrieval with a mandatory tenant filter | `hydraulikdoc/azure_ai.py`; `PRODUCT.md` Kernabläufe 4 |
| An answer without a valid `[S1]` source mark is discarded and not persisted | `PRODUCT.md` Kernabläufe 5; `hydraulikdoc/governance.py` |
| Model, deployment, region, prompt, time, user and source provenance per draft | `PRODUCT.md` Kernabläufe 6 |
| Human review states; export only of accepted results | `hydraulikdoc/ui.py`, `repository.py` |
| Deterministic condition and fluid assessment | `hydraulikdoc/condition_monitoring.py`, `fluid_advisor.py` |
| PostgreSQL FORCE RLS including tenant master data, separate lifecycle role | `db/migrations/001_enterprise.sql` |
| Deletion propagated across blob, search index and database | `PRODUCT.md` Kernabläufe 8 |
| No autonomous machine control, no employee performance assessment | `PRODUCT.md` "Bewusste Grenzen" |

The ten-layer architecture section states explicitly that infrastructure is
declared as code and that whether a specific instance is regionally,
contractually and organisationally suitable remains deployment evidence — which
is exactly how `PRODUCT.md` frames it ("Implementiert in IaC", "Externes Gate").

**Not claimed**: ISO or C5 attestation, penetration test results, restore
evidence, SLA — all listed as external gates in the source.

---

## SBS Legal

### KanzleiAI

- **Route** `legal.sbsdeutschland.com/produkte/kanzleiai`
- **Repository** `Luyzz22/kanzlei-ai`
- **Application** `https://www.kanzlei-ai.com`
- **Graphics** `ContractAnalysisGraphic`, `HybridProcessingGraphic`

| Claim on the page | Source |
| --- | --- |
| Two-stage pipeline: structured extraction, then risk and guidance | `README.md` "KI-Vertragsanalyse (Multi-Provider)" |
| Zod-validated results stored as `AnalysisRun`, `AnalysisFinding`, `DocumentExtraction` | same |
| Provider routing with recorded selection reason | `AnalysisProviderDecision.selectionReason` |
| Prompt governance: registry, `PromptDefinition` + `PromptRelease`, explicit default | `src/lib/ai/prompt-governance.server.ts`, `prompt-registry/contract-defaults.ts` |
| Every analysis is a new run; earlier results are not overwritten | `AnalysisRun.runSequence` |
| Human review per finding, with decision, comment and adjusted text | `AnalysisFindingReview`; `analysis-finding-review-policy.ts` |
| Row-Level Security per tenant | `db/rls.sql` |
| Golden-set evaluation without client data | `evals/contracts/cases/*.json`; `pnpm eval:contracts` |

The data path section is drawn from `redaction_pipeline/README.md` and is only
shown because that pipeline exists:

| Claim | Source |
| --- | --- |
| Sanitize → OCR/layout → detect → redact → minimize | `redaction_pipeline/stages/` |
| Original, page images and re-identification mapping never leave the server | `redaction_pipeline/README.md` |
| Mapping encrypted with AES-256-GCM, per tenant, stored locally | same |
| Fail-closed: health and mandate terms force a red gate | same, "Fail-closed-Garantien" |
| OCR coverage below the threshold yields an amber gate | same |
| No text layer and no OCR means confidence 0, never "empty = clean" | same |
| A residual-PII safety net runs on the final text | same, stage D |
| Output validation forbids original, mapping and speaking identifiers | `validate_output` |
| Person and organisation detection is a deterministic heuristic, not a statistical model | same, "Bekannte Abweichung vom Handoff" |

That last row is a limitation the source states about itself, and the page
states it too rather than leaving it out.

### ComplianceHub

- **Route** `legal.sbsdeutschland.com/produkte/compliancehub`
- **Repository** `Luyzz22/Compliance-Hub`
- **Graphic** `RiskGovernanceGraphic`

| Claim on the page | Source |
| --- | --- |
| Multi-tenant AI system inventory | `PRODUCT.md` Capabilities |
| Risk classification along EU AI Act Art. 6, Annex I/III | `README.md` "EU AI Act Risk Classification" |
| Policy engine with rules such as "High risk requires DPIA" | same |
| Versioned violations retrievable for GRC workflows | same |
| Gap-analysis aggregation per risk level and category | same |
| Art. 50 and GDPR transparency assurance records | `docs/enterprise/wave60-article50-transparency-assurance.md` |
| Versioned DPIA/FRIA records, four-eyes approval, consultation gates | `docs/enterprise/wave61-dpia-fria-impact-assessment.md` |
| Audit events with actor, action, entity, violation count | `README.md` "Audit Events & Evidence" |
| Public, enterprise and release routes stay technically separated | `PRODUCT.md` Capabilities and Constraints |
| No legal advice, no conformity confirmation, no binding approval | `PRODUCT.md` Capabilities and Constraints |

The page states that no approved customer logos, testimonials, certifications or
production benchmarks exist. That is a verbatim commitment from `PRODUCT.md`
("Evidence on Hand"), and it is why none appear.

**Public status.** `Compliance-Hub/README.md` carries a "Pre-Production / nicht
freigegeben" banner. Per the owner's decision in §2 of the brief, that internal
status is **not** rendered as a public downgrade: there is no "Coming Soon"
badge and no greyed-out card. The product is presented at full weight, with a
CTA of "Pilotzugang anfragen" rather than a self-service purchase that does not
exist.

---

## Cross-vertical

### BelegFlow

- **Route** `sbsdeutschland.com/plattform/belegflow`
- **Repositories** `Luyzz22/ki-rechnungsverarbeitung`, `Luyzz22/belegflow-ai-site`
- **Application** `https://app.sbsdeutschland.com`
- **Graphic** `InvoiceAutomationGraphic`

| Claim on the page | Source |
| --- | --- |
| Structured extraction of the mandatory invoice fields | `README.md`; `rechnungen` schema in `CLAUDE.md` |
| Duplicate detection | `duplicate_detection.py` |
| Plausibility check on amounts and mandatory fields | `plausibility.py` |
| SKR03/SKR04 account proposal | `README.md` Kernfunktionen |
| Role model owner / admin / manager / member / viewer with separated rights | `CLAUDE.md` §3.2 permission matrix |
| DATEV-compatible export, Excel, CSV | `datev_exporter.py`, `export.py` |
| Editable monthly report as PPTX from the user's own data | `CLAUDE.md` §4.1 MBR |
| Audit trail of process and export events | `audit.py`; `README.md` |
| All queries filter by user/tenant | `CLAUDE.md` §2.3 |
| Statements about GDPR, GoBD, e-invoicing and the EU AI Act remain to be validated | `README.md` disclaimer, quoted in substance |

**Placed at company level, not inside a division.** Invoice processing is
neither industry-specific nor legal-specific; §10 of the brief asks for exactly
this treatment. It is additionally linked from the Industrie products page as a
back-office building block, with a sentence saying it is not the division's core
identity.

---

## SBS Labs

### ReleaseProof

- **Route** `sbsdeutschland.com/labs/releaseproof`
- **Repositories** `Luyzz22/releaseproof-web`, `Luyzz22/releaseproof-jira`
- **Site** `https://releaseproof.com`
- **Graphic** `ReleaseEvidenceGraphic`

Every claim comes from `releaseproof-web/PRODUCT.md`: the seven rules by name,
the two scope modes, the issue-level evidence matrix, the `read:jira-work` and
`storage:app` scopes with no write access, the deterministic evaluation without
generative AI, the abort on unexpected Jira structures, and the explicit
statement that ReleaseProof supports a decision rather than approving a release.

It is placed under **SBS Labs** because it belongs to neither division. §35 of
the brief permits an independent bracket only when a real product exists — this
one does, with a live site.

---

## SBS Academy

PythonPfad and SQLPfad keep their own brands and their own domains as the
primary destination. The academy page carries the two taglines taken from the
live sites' own `<title>` tags, a short description of what each pathway covers,
and a link out. Nothing about their content, pricing, user numbers or curriculum
depth is asserted beyond that.

---

## Claim audit of the previous site (§52)

| Claim on the old `/sbshomepage/` | Verified? | Disposition |
| --- | --- | --- |
| "99.9 % Genauigkeit" | No source anywhere in the repositories | **Removed.** Replaced by the citation-validation and human-review mechanisms |
| "< 3s pro Dokument" | No measurement | **Removed** |
| "94 % der deutschen Mittelständler haben noch keine KI-Lösung" | No cited study | **Removed** |
| "DSGVO-konform" as a product property | Depends on contract, legal basis, DPIA, works council and operation | **Reframed.** The site describes the data paths and states explicitly that conformity is not derived from code |
| "Enterprise-Grade", "Military Grade" style badges | Not evidence | **Removed.** The trust section lists mechanisms instead |
| "Frankfurt Server" | Plausible but instance-specific | **Reframed** as "PostgreSQL in EU regions" where the source supports it |
| Technology badge wall (GPT-4, Gemini, FastAPI, …) | Real, but not a customer benefit | **Replaced** by per-product integration lists limited to what the source implements |

An automated guard enforces this going forward:

```bash
npm run check:content -- http://127.0.0.1:3100
```

It fails on accuracy quotas, latency promises, certification claims, absolute
security assurances, marketing superlatives, public status downgrades and emoji
in page text — while allowing those terms where the surrounding sentence
explicitly disclaims them, which is how the security and governance pages talk
about them.
