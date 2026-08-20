import type { Metadata } from "next";
import { publicUrl, siteForPath, sites } from "@/content/site";

type PageMeta = {
  path: string;
  title: string;
  description: string;
  /** Optional override for the OpenGraph title when the tab title is terse. */
  ogTitle?: string;
  noIndex?: boolean;
};

/**
 * Per-page metadata with the canonical pinned to the site the page belongs to,
 * so the three hostnames never compete for the same content (§53).
 */
export function pageMetadata({ path, title, description, ogTitle, noIndex }: PageMeta): Metadata {
  const site = siteForPath(path);
  const canonical = publicUrl(path);
  const fullTitle = site.titleTemplate.replace("%s", title);

  return {
    title,
    description,
    metadataBase: new URL(site.origin),
    alternates: { canonical },
    robots: noIndex ? { index: false, follow: false } : { index: true, follow: true },
    openGraph: {
      type: "website",
      locale: "de_DE",
      url: canonical,
      siteName: site.key === "corporate" ? "SBS Deutschland" : `SBS ${site.brandSuffix}`,
      title: ogTitle ?? fullTitle,
      description,
      images: [{ url: `${site.origin}/og/${site.key}.svg`, width: 1200, height: 630, alt: fullTitle }],
    },
    twitter: {
      card: "summary_large_image",
      title: ogTitle ?? fullTitle,
      description,
    },
  };
}

/**
 * Organization schema. Only fields we can verify from the existing public site
 * are emitted — no ratings, no addresses we cannot confirm, no employee counts.
 */
export function organizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "SBS Deutschland",
    url: sites.corporate.origin,
    description: sites.corporate.defaultDescription,
    sameAs: [sites.industry.origin, sites.legal.origin],
  };
}

export function breadcrumbSchema(trail: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: trail.map((entry, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: entry.name,
      item: publicUrl(entry.path),
    })),
  };
}

export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      // Schema payloads are built from typed literals above, never user input.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
