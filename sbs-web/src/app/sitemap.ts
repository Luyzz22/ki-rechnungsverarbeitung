import type { MetadataRoute } from "next";
import { headers } from "next/headers";
import { publicUrl, type SiteKey } from "@/content/site";
import { routesBySite } from "@/lib/routes";

export const dynamic = "force-dynamic";

const HOST_TO_SITE: Record<string, SiteKey> = {
  "industrie.sbsdeutschland.com": "industry",
  "industry.sbsdeutschland.com": "industry",
  "legal.sbsdeutschland.com": "legal",
};

/**
 * One sitemap per hostname (§53). A division host must not advertise the
 * corporate URLs and vice versa, otherwise the three sites compete for the
 * same content in the index.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const host = ((await headers()).get("host") ?? "").split(":")[0].toLowerCase();
  const siteKey: SiteKey = HOST_TO_SITE[host] ?? "corporate";
  const lastModified = new Date();

  return routesBySite[siteKey].map((route) => ({
    url: publicUrl(route.path),
    lastModified,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}

