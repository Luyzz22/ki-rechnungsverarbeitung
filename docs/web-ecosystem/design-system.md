# Design System

## Visual thesis

> European enterprise AI infrastructure drawn as a documented signal path — every
> claim on the page is anchored to a mechanism the reader can trace.

Every visual decision either supports that sentence or improves legibility. The
sites should read as engineering documentation with the composure of a product
company, not as an agency landing page with technical vocabulary sprinkled on.

## Experience briefs

| | Corporate | Industrie | Legal | Academy |
| --- | --- | --- | --- | --- |
| **Primary visitor** | Decision maker orienting on what SBS is | QM, Operations, Instandhaltung | Kanzlei, Legal Ops, Compliance, AI Governance | Individual learner |
| **Primary job** | Understand the company and find the right division | Get evidence out of documents that already exist | Understand contracts and document decisions | Learn Python or SQL properly |
| **Desired action** | Enter Industrie or Legal | Request a pilot / open the app | Book a demo / review the data path | Open the learning platform |
| **Strongest proof** | The shared processing path, drawn | Evidence Matrix with source locations | Local redaction pipeline, prompt governance | The live platforms themselves |
| **Brand tone** | Precise, restrained, factual | Technical, operational | Careful, governance-literate | Plain, encouraging |
| **Visual premise** | Two rails converging on one core | Documents entering one processing layer, fanning into three uses | A document with findings appearing beside it | Clean and code-adjacent |

Primary experience mode: **product evidence**. Supporting mode: **technical
precision**. No third mode is used anywhere.

## Tokens

All tokens live in `src/design-system/tokens.css`. Nothing else in the codebase
declares a raw colour, radius, duration or spacing value.

### Surfaces, text, borders

Shared by all three sites without exception. This is what makes them read as one
company: put three screenshots side by side and the paper, the ink and the rules
are identical.

```
--sbs-bg-page / -sunken / -elevated / -emphasis
--sbs-bg-inverse / -inverse-elevated / -inverse-sunken
--sbs-text-primary / -secondary / -muted
--sbs-text-inverse / -inverse-secondary / -inverse-muted
--sbs-border-subtle / --sbs-border / --sbs-border-strong
--sbs-border-inverse / --sbs-border-inverse-strong
```

### Accents — the only thing that changes per division

```
                     accent      bright      on-inverse   associations
corporate (default)  #0b6ea8     #38a3dc     #6cc6f2      company, platform
[data-division=industry]  #0a7f96  #22b3c9   #4fd4e6      production, evidence, machines
[data-division=legal]     #4a45b8  #7a74e8   #a49ef7      contracts, governance, review
[data-division=academy]   #0d7a5f  #23b48c   #4fd9ae      learning, code
```

The two corporate constants — SBS Navy `#003856` and SBS Gold `#FFB900` — are
kept as brand anchors rather than as page colours. Navy is the wordmark and the
inverse ground; gold marks exactly one thing on the entire site: **the step
where a human decides**. That is the only place gold appears in a pipeline, a
flow, an architecture diagram or a product card, on all three sites.

Applying a division theme is one attribute:

```tsx
<div data-division="industry">…</div>
```

### Type scale

```
.sbs-display            clamp(2.375rem, 1.35rem + 3.6vw, 4.5rem)   lh 1.04  ls -0.032em
.sbs-display--triplet   clamp(2.125rem, 1.3rem  + 2.9vw, 3.5rem)   lh 1.08  ls -0.028em
.sbs-display--sm        clamp(2rem,     1.25rem + 2.6vw, 3.25rem)  lh 1.06  ls -0.032em
.sbs-h2                 clamp(1.75rem,  1.15rem + 2.3vw, 2.875rem) lh 1.10  ls -0.028em
.sbs-h3                 clamp(1.3125rem,1.05rem + 1vw,   1.75rem)  lh 1.20  ls -0.021em
.sbs-h4                 1.0625rem                                  lh 1.35
.sbs-lead               clamp(1.0625rem, 1rem + 0.3vw, 1.25rem)    lh 1.55  max 44rem
.sbs-eyebrow            0.6875rem mono, uppercase, ls 0.13em
```

The display ceiling is 72px, not the 82px a comparable English-language scale
would take. German compound nouns — *Instandhaltungsentscheidung*,
*Nachvollziehbarkeit* — overflow a 375px line box at larger sizes. Below
`48rem` the display classes also enable `hyphens: auto`, which works because the
document carries `lang="de"`.

`.sbs-display--triplet` exists for headlines built from several short sentences,
such as the Legal hero. Hero copy is capped at `39rem` (`.sbs-measure-hero`).

### Spacing, radii, motion

```
--sbs-space-1 … -12     4px → 160px
--sbs-radius-sm/md/lg/xl  6 / 10 / 16 / 24px
--sbs-motion-fast        140ms   hover, focus, button feedback
--sbs-motion-normal      240ms   menus, card elevation
--sbs-motion-slow        460ms   entrance reveals
--sbs-motion-rail         11s    continuous rail flow
--sbs-ease-standard      cubic-bezier(0.2, 0.7, 0.3, 1)
```

## Grid and rhythm

```
max-width  1280px          (prose 68ch, narrow 940px)
columns    4 / 8 / 12      at mobile / tablet / desktop
gutter     20 / 32 / 40px
```

Section padding is intentionally uneven — `--tight`, default, `--wide`, `--hero`
— so the page moves through dense, spacious, visual, technical, spacious and
conversion phases rather than repeating one rhythm.

Every single-column grid pins its base track to `minmax(0, 1fr)`. Without it a
wide child — a table, a rail, a product graphic — sizes the track and pushes the
page sideways on a phone. Wide content always scrolls inside `.sbs-scroll-x`,
which carries `min-width: 0` for the same reason.

## The ownable motif: SBS Signal Rail

A thin line carrying labelled nodes, with the human-decision node in gold. It
recurs at five scales:

| Scale | Where | Component |
| --- | --- | --- |
| Mark | Wordmark: two inputs joining one path | `navigation/Wordmark.tsx` |
| Miniature | Mega-menu featured panel | `navigation/MegaPanelGraphic.tsx` |
| Section | Division split, page dividers | `sections/DivisionSplit.tsx`, `ui/Divider.tsx` |
| Hero | Product network, industry fan-in/fan-out | `graphics/SbsNetworkGraphic.tsx`, `IndustryHeroGraphic.tsx` |
| Diagram | Architecture flow, product pipelines | `graphics/ArchitectureFlow.tsx`, product page mechanism section |

The rail transforms per division, exactly as §9 asks:

```
Industrie   Dokument → Extraktion → Evidence → Prüfung → Maßnahme → System
Legal       Vertrag  → Extraktion → Finding  → Risiko  → Review   → Audit Trail
Corporate   Industrie ┐
                      ├→ SBS Enterprise Core
            Legal     ┘
```

## Graphics policy

Six product graphics, one per product, each drawn from that product's real
mechanism:

| Component | Product | What it shows that a generic illustration would not |
| --- | --- | --- |
| `EvidenceMatrixGraphic` | NormPilot | A row with **no** evidence, its GAP severity, and the corrective action it produced |
| `ManualRetrievalGraphic` | HydraulikDoc | The **rejected** answer next to the accepted one — no source mark, not persisted |
| `ContractAnalysisGraphic` | KanzleiAI | A finding that is still `offen` because nobody has reviewed it |
| `HybridProcessingGraphic` | KanzleiAI | Ten stations, nine local, one at the cloud boundary |
| `RiskGovernanceGraphic` | ComplianceHub | The Art. 6 decision path and the violation it produced, with an owner |
| `InvoiceAutomationGraphic` | FlowCheck AI+ | Two of four invoices **blocked** from export |
| `ReleaseEvidenceGraphic` | ReleaseProof | Seven rules per issue, two issues failing |

The test from §80 — *would this graphic work for any other AI SaaS?* — is failed
by all of them, which is the point. Every graphic that shows data carries a
`DEMO` marker (`graphics/primitives.tsx`) and uses synthetic values only.

What is deliberately absent: stock photography, abstract brains, robots, neural
networks, glow blobs, gradient cards, fake dashboards, customer logos, emoji as
interface chrome. The content guard (`npm run check:content`) fails the build if
emoji reappear in page text.

## Motion

Every effect has a stated purpose and a static fallback.

| Effect | Purpose | Fallback under reduced motion |
| --- | --- | --- |
| Dashed rail flow | explain — data moves through one shared path | Static dashed line |
| Staggered entrance of table rows and findings | explain — the sequence of the workflow | All rows visible immediately |
| Mega-menu fade and slide | orient | Instant |
| Button arrow shift on hover | focus | No shift |
| Card elevation and border change | focus | Border change only |
| Chevron rotation | confirm | Instant |

Constraints held throughout:

- Entrance reveals never exceed ~500ms in total; no primary content waits on one.
- No scroll hijacking, no pinned sections, no scroll-driven page takeover.
- Nothing is discoverable by hover alone — the product-network capability line is
  updated on focus as well and is announced via `aria-live`.
- `@media (prefers-reduced-motion: reduce)` reduces every animation and
  transition to 1µs and removes the reveals. Verified: zero running animations.

## Responsive logic

Mobile is a recomposition, not a scale-down:

- The mega menu becomes a full-screen drawer with one labelled `<nav>` per group.
- The product network stacks into labelled columns; the rails are hidden below
  `md` because a connector with nothing to connect is noise.
- The industry hero's five input cards become a two-column grid.
- Tables and rails scroll inside their own container.
- Display type drops to 38px and hyphenates.
- Every interactive element is at least 36px tall; primary actions are 44px.

Verified at 375×812, 430×932, 768×1024, 1024×768, 1440×900 and 1920×1080.
