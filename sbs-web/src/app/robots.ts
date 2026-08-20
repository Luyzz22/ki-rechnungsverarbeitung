import type { MetadataRoute } from "next";
import { headers } from "next/headers";
import { sites, type SiteKey } from "@/content/site";

export const dynamic = "force-dynamic";

const HOST_TO_SITE: Record<string, SiteKey> = {
  "industrie.sbsdeutschland.com": "industry",
  "industry.sbsdeutschland.com": "industry",
  "legal.sbsdeutschland.com": "legal",
};

export default async function robots(): Promise<MetadataRoute.Robots> {
  const host = ((await headers()).get("host") ?? "").split(":")[0].toLowerCase();
  const siteKey: SiteKey = HOST_TO_SITE[host] ?? "corporate";
  const site = sites[siteKey];

  return {
    rules: [{ userAgent: "*", allow: "/" }],
    sitemap: `${site.origin}/sitemap.xml`,
    host: site.origin.replace("https://", ""),
  };
}
