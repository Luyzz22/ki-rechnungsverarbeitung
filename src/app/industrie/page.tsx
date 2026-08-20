import Link from "next/link";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { IndustryHeroGraphic } from "@/components/graphics/IndustryHeroGraphic";
import { EvidenceMatrixGraphic } from "@/components/graphics/EvidenceMatrixGraphic";
import { ProductCard } from "@/components/product/ProductCard";
import { productBySlug, productsByDivision } from "@/content/products";
import { solutionsByDivision } from "@/content/solutions";
import { pageMetadata } from "@/lib/seo";
import { sites, linkFor } from "@/content/site";

const PAGE_PATH = "/industrie";

export const metadata: Metadata = pageMetadata({
  path: "/industrie",
  title: "Aus technischen Dokumenten werden Entscheidungen",
  ogTitle: sites.industry.defaultTitle,
  description: sites.industry.defaultDescription,
});

const audiences = [
  { role: "Qualitätsmanagement", job: "Nachweise für interne und externe Audits vorhalten und Lücken früh sehen." },
  { role: "Operations & Produktion", job: "Kaufmännische und dokumentennahe Abläufe entlasten, ohne Nachvollziehbarkeit zu verlieren." },
  { role: "Instandhaltung & Service", job: "Technische Fragen am Asset beantworten – mit Quelle statt Erfahrungswert." },
  { role: "Technische Dokumentation", job: "Bestandsdokumente auffindbar und belegbar machen, ohne sie neu zu schreiben." },
  { role: "Einkauf & Backoffice", job: "Belegprüfung und Freigaben in einen dokumentierten Ablauf bringen." },
  { role: "Informationssicherheit", job: "Rollen, Mandantentrennung, Protokollierung und Löschwege prüfen können." },
];

export default function IndustryHome() {
  const flowcheck = productBySlug("flowcheck")!;
  const products = productsByDivision("industry");
  const solutions = solutionsByDivision("industry");

  return (
    <SiteChrome siteKey="industry" path="/industrie">
      {/* Hero */}
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section sbs-section--hero">
          <div className="grid grid-cols-[minmax(0,1fr)] gap-11 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center lg:gap-14">
            <div className="sbs-measure-hero flex flex-col gap-6">
              <Eyebrow>SBS Deutschland · Industrie</Eyebrow>
              <h1 className="sbs-display text-[var(--sbs-text-inverse)]">
                Aus technischen Dokumenten werden Entscheidungen.
              </h1>
              <p className="sbs-lead">
                SBS Industrie verbindet Dokumentintelligenz, Audit Evidence und KI-Workflows für
                Qualität, Service und industrielle Prozesse. Ergebnisse führen ihre Quelle mit, und
                vor jeder Freigabe steht eine fachverantwortliche Person.
              </p>
              <div className="flex flex-wrap gap-3 pt-1">
                <Button href={linkFor(PAGE_PATH, "/industrie/produkte")} size="lg">
                  Produkte ansehen
                </Button>
                <Button href={linkFor(PAGE_PATH, "/industrie/kontakt")} variant="inverse" size="lg">
                  Demo anfragen
                </Button>
              </div>
            </div>
            <div>
              <IndustryHeroGraphic currentPath="/industrie" />
            </div>
          </div>
        </div>
      </section>

      {/* Products */}
      <Section tone="page" rhythm="wide" labelledBy="produkte">
        <SectionHeader
          id="produkte"
          eyebrow="Produkte"
          title="Zwei Produkte für den technischen Nachweis"
          lead="NormPilot arbeitet auf der Auditebene, HydraulikDoc am einzelnen Asset. Beide führen jedes Ergebnis auf eine Quelle zurück."
          className="mb-10"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          {products.map((product) => (
            <ProductCard key={product.slug} product={product} currentPath="/industrie" />
          ))}
        </div>

        <div className="mt-6 rounded-[var(--sbs-radius-lg)] border border-dashed border-[var(--sbs-border-strong)] bg-[var(--sbs-bg-sunken)] p-6">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Geschäftsübergreifend</p>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="max-w-[36rem]">
              <h3 className="sbs-h4">{flowcheck.name}</h3>
              <p className="mt-1.5 text-[0.875rem] leading-[1.55] text-[var(--sbs-text-secondary)]">
                {flowcheck.tagline} Geführt wird FlowCheck AI+ auf Unternehmensebene, weil es weder zur
                Industrie noch zum Recht allein gehört.
              </p>
            </div>
            <Button href={linkFor(PAGE_PATH, flowcheck.href)} variant="secondary">
              FlowCheck AI+ ansehen
            </Button>
          </div>
        </div>
      </Section>

      {/* Evidence in context */}
      <Section tone="sunken" labelledBy="evidenz">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-center lg:gap-14">
          <div className="flex flex-col gap-5">
            <SectionHeader
              id="evidenz"
              eyebrow="Kernidee"
              title="Ein Nachweis ist erst dann einer, wenn er seine Fundstelle mitbringt"
              lead="Der Unterschied zwischen einer plausiblen Aussage und einem prüfbaren Nachweis ist die Quelle. Deshalb ist sie in allen Industrie-Produkten Pflichtbestandteil des Ergebnisses – nicht eine Option im Export."
            />
            <div>
              <Button href={linkFor(PAGE_PATH, "/industrie/loesungen/audit-readiness")} variant="secondary">
                Audit-Workflow ansehen
              </Button>
            </div>
          </div>
          <EvidenceMatrixGraphic />
        </div>
      </Section>

      {/* Solutions */}
      <Section tone="page" labelledBy="loesungen">
        <SectionHeader
          id="loesungen"
          eyebrow="Lösungen"
          title="Nach Aufgabe statt nach Produkt"
          lead="Die meisten Vorhaben brauchen mehr als ein Produkt. Diese Seiten beschreiben den Weg vom Problem zum Ergebnis."
          className="mb-9"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-6 gap-y-7 md:grid-cols-2 lg:grid-cols-3">
          {solutions.map((solution) => (
            <li key={solution.slug} className="border-t border-[var(--sbs-border)] pt-5">
              <Link href={linkFor(PAGE_PATH, solution.href)} className="group flex flex-col gap-2.5">
                <h3 className="sbs-h4 flex items-center gap-2 text-[var(--sbs-text-primary)]">
                  {solution.title}
                  <span
                    aria-hidden="true"
                    className="text-[var(--sbs-accent)] opacity-0 transition-opacity duration-[var(--sbs-motion-fast)] group-hover:opacity-100"
                  >
                    →
                  </span>
                </h3>
                <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{solution.outcome}</p>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      {/* Audiences */}
      <Section tone="inverse" labelledBy="zielgruppen">
        <SectionHeader
          id="zielgruppen"
          eyebrow="Zielgruppen"
          title="Wer damit arbeitet"
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-7 md:grid-cols-2 lg:grid-cols-3">
          {audiences.map((audience) => (
            <li key={audience.role} className="flex flex-col gap-2 border-t border-[var(--sbs-border-inverse)] pt-4">
              <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-inverse)]">{audience.role}</h3>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-inverse-secondary)]">{audience.job}</p>
            </li>
          ))}
        </ul>
      </Section>

      {/* CTA */}
      <Section tone="page" rhythm="tight">
        <div className="flex flex-col gap-5 rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
          <div className="max-w-[36rem]">
            <Eyebrow>Nächster Schritt</Eyebrow>
            <h2 className="sbs-h3 mt-2">Mit welchem Dokumentenbestand fangen wir an?</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Ein Pilot beginnt mit dem, was schon da ist: vorhandene PDFs, Excel-Listen und
              Prüfberichte. Für einen ersten Termin reichen synthetische Beispieldaten.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href={linkFor(PAGE_PATH, "/industrie/kontakt?division=industry")} size="lg">
              Pilot besprechen
            </Button>
            <Button href={linkFor(PAGE_PATH, "/industrie/plattform")} variant="secondary" size="lg">
              Technische Architektur ansehen
            </Button>
          </div>
        </div>
      </Section>
    </SiteChrome>
  );
}
