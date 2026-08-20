import { products } from "@/content/products";
import { solutions } from "@/content/solutions";
import type { SiteKey } from "@/content/site";

/**
 * Every indexable route, grouped by the site that publishes it. Used by the
 * sitemap, the robots policy and the link checker so all three stay in sync
 * with the content registry.
 */
export const routesBySite: Record<SiteKey, { path: string; priority: number; changeFrequency: "weekly" | "monthly" }[]> = {
  corporate: [
    { path: "/", priority: 1, changeFrequency: "weekly" },
    { path: "/plattform", priority: 0.8, changeFrequency: "monthly" },
    { path: "/plattform/belegflow", priority: 0.8, changeFrequency: "monthly" },
    { path: "/academy", priority: 0.7, changeFrequency: "monthly" },
    { path: "/labs/releaseproof", priority: 0.6, changeFrequency: "monthly" },
    { path: "/unternehmen", priority: 0.6, changeFrequency: "monthly" },
    { path: "/sicherheit", priority: 0.7, changeFrequency: "monthly" },
    { path: "/ressourcen", priority: 0.5, changeFrequency: "monthly" },
    { path: "/kontakt", priority: 0.7, changeFrequency: "monthly" },
    { path: "/impressum", priority: 0.3, changeFrequency: "monthly" },
    { path: "/datenschutz", priority: 0.3, changeFrequency: "monthly" },
  ],
  industry: [
    { path: "/industrie", priority: 1, changeFrequency: "weekly" },
    { path: "/industrie/produkte", priority: 0.9, changeFrequency: "monthly" },
    ...products
      .filter((product) => product.division === "industry")
      .map((product) => ({ path: product.href, priority: 0.9, changeFrequency: "monthly" as const })),
    { path: "/industrie/loesungen", priority: 0.8, changeFrequency: "monthly" },
    ...solutions
      .filter((solution) => solution.division === "industry")
      .map((solution) => ({ path: solution.href, priority: 0.7, changeFrequency: "monthly" as const })),
    { path: "/industrie/plattform", priority: 0.7, changeFrequency: "monthly" },
    { path: "/industrie/kontakt", priority: 0.7, changeFrequency: "monthly" },
  ],
  legal: [
    { path: "/legal", priority: 1, changeFrequency: "weekly" },
    { path: "/legal/produkte", priority: 0.9, changeFrequency: "monthly" },
    ...products
      .filter((product) => product.division === "legal")
      .map((product) => ({ path: product.href, priority: 0.9, changeFrequency: "monthly" as const })),
    { path: "/legal/loesungen", priority: 0.8, changeFrequency: "monthly" },
    ...solutions
      .filter((solution) => solution.division === "legal")
      .map((solution) => ({ path: solution.href, priority: 0.7, changeFrequency: "monthly" as const })),
    { path: "/legal/governance", priority: 0.7, changeFrequency: "monthly" },
    { path: "/legal/kontakt", priority: 0.7, changeFrequency: "monthly" },
  ],
};

export const allRoutes = Object.values(routesBySite).flatMap((entries) => entries.map((entry) => entry.path));
