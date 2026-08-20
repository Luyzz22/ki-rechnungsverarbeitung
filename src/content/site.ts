import type { Division } from "./types";

export type SiteKey = "corporate" | "industry" | "legal";

export type SiteConfig = {
  key: SiteKey;
  /** Value written to [data-division] so the token theme switches. */
  theme: Division;
  /** Public origin for canonical URLs, sitemap and OpenGraph. */
  origin: string;
  /** Path prefix inside this single Next.js app. "" for corporate. */
  basePath: "" | "/industrie" | "/legal";
  /** Wordmark: first part is always "SBS Deutschland". */
  brandSuffix?: string;
  titleTemplate: string;
  defaultTitle: string;
  defaultDescription: string;
};

export const ORG_NAME = "SBS Deutschland";
export const ORG_LEGAL_NAME = "SBS Deutschland GmbH & Co. KG";
export const CONTACT_EMAIL = "kontakt@sbsdeutschland.com";

export const sites: Record<SiteKey, SiteConfig> = {
  corporate: {
    key: "corporate",
    theme: "corporate",
    origin: "https://sbsdeutschland.com",
    basePath: "",
    titleTemplate: "%s | SBS Deutschland",
    defaultTitle: "SBS Deutschland — Enterprise-KI für nachvollziehbare Prozesse",
    defaultDescription:
      "SBS Deutschland baut KI-Systeme für Industrie und Recht, deren Ergebnisse bis zur Quelle nachvollziehbar bleiben: Dokumentintelligenz, Evidence, Human Review und Audit Trail.",
  },
  industry: {
    key: "industry",
    theme: "industry",
    origin: "https://industrie.sbsdeutschland.com",
    basePath: "/industrie",
    brandSuffix: "Industrie",
    titleTemplate: "%s | SBS Industrie",
    defaultTitle: "SBS Industrie — Aus technischen Dokumenten werden Entscheidungen",
    defaultDescription:
      "Dokumentintelligenz, Audit Evidence und KI-Workflows für Qualität, Service und industrielle Prozesse: NormPilot, HydraulikDoc und FlowCheck AI+ von SBS Deutschland.",
  },
  legal: {
    key: "legal",
    theme: "legal",
    origin: "https://legal.sbsdeutschland.com",
    basePath: "/legal",
    brandSuffix: "Legal",
    titleTemplate: "%s | SBS Legal",
    defaultTitle: "SBS Legal — Verträge verstehen, Risiken nachvollziehen",
    defaultDescription:
      "KI-gestützte Vertragsanalyse, Human Review und Compliance-Evidence für Rechts- und Governance-Prozesse: KanzleiAI und ComplianceHub von SBS Deutschland.",
  },
};

/** Resolve which site a route belongs to, from its in-app pathname. */
export function siteForPath(pathname: string): SiteConfig {
  if (pathname === "/industrie" || pathname.startsWith("/industrie/")) return sites.industry;
  if (pathname === "/legal" || pathname.startsWith("/legal/")) return sites.legal;
  return sites.corporate;
}

/**
 * Public URL for an in-app path.
 *
 * The three sites are one Next.js build addressed by three hostnames, so the
 * canonical URL has to drop the internal prefix: `/industrie/produkte/normpilot`
 * is published as `https://industrie.sbsdeutschland.com/produkte/normpilot`.
 */
export function publicUrl(pathname: string): string {
  const site = siteForPath(pathname);
  const rest = site.basePath ? pathname.slice(site.basePath.length) : pathname;
  // Next serialises canonicals without a trailing slash; match it so the
  // sitemap and the canonical never disagree about the same page.
  return rest === "/" || rest === "" ? site.origin : `${site.origin}${rest}`;
}

/**
 * Cross-site links must be absolute; same-site links stay relative and drop the
 * internal prefix, because that prefix is not part of the public URL space of a
 * division host. Idempotent: an already-absolute href is returned unchanged.
 */
export function linkFor(fromPath: string, targetPath: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(targetPath) || targetPath.startsWith("//")) return targetPath;
  if (targetPath.startsWith("#")) return targetPath;
  const from = siteForPath(fromPath);
  const to = siteForPath(targetPath);
  if (from.key === to.key) {
    const rest = to.basePath ? targetPath.slice(to.basePath.length) || "/" : targetPath;
    return rest || "/";
  }
  return publicUrl(targetPath);
}
