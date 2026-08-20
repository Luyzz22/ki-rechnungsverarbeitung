/**
 * Content model for the SBS web ecosystem.
 *
 * Everything the three sites render about a product — navigation, listings,
 * cross-sell, footer, sitemap — is derived from `products.ts`. Product facts
 * are never duplicated in page components.
 */

export type Division =
  | "corporate"
  | "industry"
  | "legal"
  | "academy"
  | "cross_vertical"
  | "independent";

/** A capability we can point at a concrete mechanism in the product code. */
export type Capability = {
  title: string;
  description: string;
};

/** One stage of a product's real processing path. Drives the flow graphics. */
export type PipelineStage = {
  id: string;
  label: string;
  detail: string;
  /** Optional short annotation rendered in mono next to the stage. */
  annotation?: string;
  /** Marks the stage where a human decides. Rendered distinctly everywhere. */
  human?: boolean;
};

export type ProductLink = {
  label: string;
  href: string;
  /** External links open in a new tab and get a rel policy. */
  external?: boolean;
};

export type Product = {
  slug: string;
  name: string;
  /** Shown in eyebrows: "SBS INDUSTRIE / NORMPILOT". */
  shortName: string;
  division: Division;
  /** One line, outcome-first. Used in nav and cards. */
  tagline: string;
  /** Two to three sentences. Mechanism, not adjectives. */
  description: string;
  /** The outcome headline on the product page. */
  outcome: string;
  /** Who this is for. Rendered as a plain list, not badges. */
  audience: string[];
  capabilities: Capability[];
  pipeline: PipelineStage[];
  /** Before / after for the workflow section of the product page. */
  workflow: { before: string[]; after: string[] };
  /** Real, code-backed governance mechanisms. No certifications. */
  governance: string[];
  /** Only integrations that exist in the product source. */
  integrations?: string[];
  /** Which graphic component renders this product's mechanism. */
  graphic:
    | "evidence-matrix"
    | "manual-retrieval"
    | "contract-analysis"
    | "risk-governance"
    | "invoice-automation"
    | "release-evidence";
  primaryAction: ProductLink;
  secondaryAction?: ProductLink;
  /** Repositories this product is built from. Rendered nowhere; used in docs. */
  repositories: string[];
  /** Related products for the cross-sell block, with the reason for the pair. */
  relatedSlugs: string[];
  relatedReason: string;
  /** Page route within this web ecosystem. */
  href: string;
};

export type Solution = {
  slug: string;
  division: Extract<Division, "industry" | "legal">;
  title: string;
  /** The problem in the visitor's words. */
  problem: string;
  outcome: string;
  /** What changes, step by step. */
  steps: string[];
  productSlugs: string[];
  href: string;
};

export type AcademyCourse = {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  topics: string[];
  url: string;
  domain: string;
};
