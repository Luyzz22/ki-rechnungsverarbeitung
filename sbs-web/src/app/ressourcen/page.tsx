import Link from "next/link";
import type { Metadata } from "next";
import { linkFor } from "@/content/site";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { products } from "@/content/products";
import { solutions } from "@/content/solutions";
import { pageMetadata } from "@/lib/seo";

const PAGE_PATH = "/ressourcen";

export const metadata: Metadata = pageMetadata({
  path: "/ressourcen",
  title: "Ressourcen",
  description:
    "Einstiegspunkte in das SBS-Ökosystem: Produkte, Lösungen, technische Grundlage, Sicherheit und Datenwege sowie die laufenden Anwendungen.",
});

const entries = [
  {
    title: "Technische Grundlage",
    body: "Wie Dokumente verarbeitet, Ergebnisse validiert, Prüfungen protokolliert und Läufe versioniert werden.",
    href: "/plattform",
  },
  {
    title: "Sicherheit & Datenwege",
    body: "Umgesetzte Kontrollen je Bereich — und die Aussagen, die wir bewusst nicht treffen.",
    href: "/sicherheit",
  },
  {
    title: "Governance im Legal-Bereich",
    body: "Mandantentrennung, lokale Redaction, Prompt-Governance, Vier-Augen-Freigaben.",
    href: "/legal/governance",
  },
  {
    title: "Plattform im Industrie-Bereich",
    body: "Extraktion vor Modell, erzwungener Mandantenfilter, Abbruch bei fehlender Quelle.",
    href: "/industrie/plattform",
  },
];

export default function ResourcesPage() {
  const liveApps = products.filter((product) => product.primaryAction.external);

  return (
    <SiteChrome siteKey="corporate" path="/ressourcen">
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="Ressourcen"
          title="Einstiegspunkte in das SBS-Ökosystem"
          lead="Kein Blog und keine Whitepaper-Sammlung, sondern die Seiten, auf denen der Mechanismus steht — und die Anwendungen, die bereits laufen."
          className="mb-11"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2">
          {entries.map((entry) => (
            <li key={entry.href} className="border-t border-[var(--sbs-border)] pt-5">
              <Link href={linkFor(PAGE_PATH, entry.href)} className="group flex flex-col gap-2">
                <h2 className="sbs-h4 flex items-center gap-2 text-[var(--sbs-text-primary)]">
                  {entry.title}
                  <span
                    aria-hidden="true"
                    className="text-[var(--sbs-accent)] opacity-0 transition-opacity duration-[var(--sbs-motion-fast)] group-hover:opacity-100"
                  >
                    →
                  </span>
                </h2>
                <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="sunken" labelledBy="anwendungen">
        <SectionHeader
          id="anwendungen"
          eyebrow="Laufende Anwendungen"
          title="Produkte, die Sie direkt öffnen können"
          lead="Diese Adressen sind erreichbar. Für einen Zugang sprechen Sie uns an — die Startseiten sind auch ohne Konto einsehbar."
          className="mb-8"
        />
        <ul className="flex flex-col">
          {liveApps.map((product) => (
            <li key={product.slug} className="border-t border-[var(--sbs-border)] last:border-b">
              <div className="grid grid-cols-[minmax(0,1fr)] gap-2 py-5 sm:grid-cols-[minmax(0,0.5fr)_minmax(0,1fr)_auto] sm:items-baseline sm:gap-6">
                <Link href={linkFor(PAGE_PATH, product.href)} className="sbs-h4 inline-flex min-h-9 items-center text-[var(--sbs-text-primary)] hover:text-[var(--sbs-accent-strong)]">
                  {product.name}
                </Link>
                <p className="text-[0.875rem] leading-[1.55] text-[var(--sbs-text-secondary)]">{product.tagline}</p>
                <a
                  href={linkFor(PAGE_PATH, product.primaryAction.href)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="sbs-mono inline-flex min-h-9 items-center text-[0.75rem] text-[var(--sbs-accent)] underline-offset-4 hover:underline"
                >
                  {product.primaryAction.href.replace("https://", "")}
                  <span className="sr-only"> (öffnet in neuem Tab)</span>
                </a>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="page" labelledBy="loesungsindex">
        <SectionHeader id="loesungsindex" eyebrow="Index" title="Alle Lösungsseiten" className="mb-7" />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((solution) => (
            <li key={solution.href}>
              <Link
                href={linkFor(PAGE_PATH, solution.href)}
                className="flex min-h-11 items-center text-[0.9375rem] text-[var(--sbs-text-secondary)] hover:text-[var(--sbs-accent-strong)]"
              >
                <span className="sbs-mono mr-2.5 text-[0.6875rem] uppercase tracking-[0.08em] text-[var(--sbs-text-muted)]">
                  {solution.division === "industry" ? "IND" : "LEG"}
                </span>
                {solution.title}
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </SiteChrome>
  );
}
