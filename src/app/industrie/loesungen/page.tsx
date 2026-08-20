import Link from "next/link";
import type { Metadata } from "next";
import { linkFor } from "@/content/site";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { solutionsByDivision } from "@/content/solutions";
import { productBySlug } from "@/content/products";
import { pageMetadata } from "@/lib/seo";

const PAGE_PATH = "/industrie/loesungen";

export const metadata: Metadata = pageMetadata({
  path: "/industrie/loesungen",
  title: "Lösungen",
  description:
    "Lösungen von SBS Industrie nach Aufgabe: Audit-Readiness, technische Dokumentation, Service und Instandhaltung, Operations und Document Intelligence.",
});

export default function IndustrySolutions() {
  const solutions = solutionsByDivision("industry");
  return (
    <SiteChrome siteKey="industry" path="/industrie/loesungen">
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="SBS Industrie · Lösungen"
          title="Fünf Aufgaben, für die mehr als ein Produkt nötig ist"
          lead="Diese Seiten beginnen mit dem Problem, nicht mit dem Produktnamen. Sie zeigen den Weg vom Ausgangszustand zum prüfbaren Ergebnis."
          className="mb-11"
        />
        <ul className="flex flex-col">
          {solutions.map((solution) => {
            const involved = solution.productSlugs
              .map((slug) => productBySlug(slug)?.name)
              .filter(Boolean);
            return (
              <li key={solution.slug} className="border-t border-[var(--sbs-border)] last:border-b">
                <Link
                  href={linkFor(PAGE_PATH, solution.href)}
                  className="group grid grid-cols-[minmax(0,1fr)] gap-3 py-7 transition-colors duration-[var(--sbs-motion-fast)] lg:grid-cols-[minmax(0,0.6fr)_minmax(0,1fr)_auto] lg:items-baseline lg:gap-8"
                >
                  <h2 className="sbs-h3 text-[var(--sbs-text-primary)] group-hover:text-[var(--sbs-accent-strong)]">
                    {solution.title}
                  </h2>
                  <div className="flex flex-col gap-2">
                    <p className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
                      {solution.outcome}
                    </p>
                    <p className="sbs-mono text-[0.6875rem] text-[var(--sbs-text-muted)]">
                      {involved.join(" · ")}
                    </p>
                  </div>
                  <span
                    aria-hidden="true"
                    className="text-[var(--sbs-accent)] transition-transform duration-[var(--sbs-motion-fast)] group-hover:translate-x-1 motion-reduce:transition-none"
                  >
                    →
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </Section>
    </SiteChrome>
  );
}
