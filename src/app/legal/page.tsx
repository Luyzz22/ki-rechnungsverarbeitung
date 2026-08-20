import Link from "next/link";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { LegalHeroGraphic } from "@/components/graphics/LegalHeroGraphic";
import { HybridProcessingGraphic } from "@/components/graphics/ContractAnalysisGraphic";
import { ProductCard } from "@/components/product/ProductCard";
import { productsByDivision } from "@/content/products";
import { solutionsByDivision } from "@/content/solutions";
import { pageMetadata } from "@/lib/seo";
import { sites, linkFor } from "@/content/site";

const PAGE_PATH = "/legal";

export const metadata: Metadata = pageMetadata({
  path: "/legal",
  title: "Verträge verstehen. Risiken nachvollziehen. Entscheidungen dokumentieren.",
  ogTitle: sites.legal.defaultTitle,
  description: sites.legal.defaultDescription,
});

const audiences = [
  { role: "Kanzleien", job: "Vertragsprüfung skalieren, ohne die Herkunft eines Befunds aufzugeben." },
  { role: "Unternehmensjuristik", job: "Wiederkehrende Vertragsarten strukturiert erfassen statt jedes Mal neu zu lesen." },
  { role: "Legal Operations", job: "Analyseläufe, Prüfentscheidungen und Historie als Bestand führen statt als Postfach." },
  { role: "Compliance & Datenschutz", job: "Pflichten, Kontrollen und Nachweise mit benannter Verantwortlichkeit führen." },
  { role: "AI Governance", job: "KI-Systeme inventarisieren, klassifizieren und Verstöße nachverfolgen." },
  { role: "Einkauf & Vertragsmanagement", job: "Standardabweichungen in Lieferantenverträgen früh und begründet erkennen." },
];

export default function LegalHome() {
  const products = productsByDivision("legal");
  const solutions = solutionsByDivision("legal");

  return (
    <SiteChrome siteKey="legal" path="/legal">
      {/* Hero */}
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section sbs-section--hero">
          <div className="grid grid-cols-[minmax(0,1fr)] gap-11 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center lg:gap-14">
            <div className="sbs-measure-hero flex flex-col gap-6">
              <Eyebrow>SBS Deutschland · Legal</Eyebrow>
              <h1 className="sbs-display--triplet text-[var(--sbs-text-inverse)]">
                Verträge verstehen.<br />Risiken nachvollziehen.<br />Entscheidungen dokumentieren.
              </h1>
              <p className="sbs-lead">
                SBS Legal verbindet KI-gestützte Vertragsanalyse, Human Review und
                Compliance-Evidence für professionelle Rechts- und Governance-Prozesse. Jeder Befund
                führt mit, aus welchem Lauf, welchem Modell und welcher Prompt-Version er stammt.
              </p>
              <div className="flex flex-wrap gap-3 pt-1">
                <Button href={linkFor(PAGE_PATH, "/legal/produkte")} size="lg">
                  Produkte ansehen
                </Button>
                <Button href={linkFor(PAGE_PATH, "/legal/kontakt")} variant="inverse" size="lg">
                  Demo anfragen
                </Button>
              </div>
            </div>
            <div>
              <LegalHeroGraphic />
            </div>
          </div>
        </div>
      </section>

      {/* Products */}
      <Section tone="page" rhythm="wide" labelledBy="produkte">
        <SectionHeader
          id="produkte"
          eyebrow="Produkte"
          title="Zwei Produkte, ein Nachweismodell"
          lead="KanzleiAI arbeitet am einzelnen Dokument, ComplianceHub am Bestand aus Systemen, Pflichten und Kontrollen. Beide führen Findings mit Schweregrad, Zuständigkeit und Prüfentscheidung."
          className="mb-10"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          {products.map((product) => (
            <ProductCard key={product.slug} product={product} currentPath="/legal" />
          ))}
        </div>
      </Section>

      {/* The data path — the strongest thing this division can show */}
      <Section tone="sunken" labelledBy="datenweg-titel">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-14">
          <div className="flex flex-col gap-5">
            <SectionHeader
              id="datenweg-titel"
              eyebrow="Kernidee"
              title="Der Datenweg ist Teil des Produkts, nicht eine Zusicherung im Text"
              lead="Bei KanzleiAI verlassen Originaldokument, Seitenbilder und das Re-Identifikations-Mapping den eigenen Server nicht. In die Cloud geht ausschließlich ein minimierter Payload, dessen Felder standardmäßig gesperrt sind."
            />
            <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Bleibt ein Befund unsicher — unvollständige Texterkennung, erkannte Mandats- oder
              Gesundheitsbegriffe, nicht auflösbare Koordinaten — blockiert das Policy Gate den
              Versand. Der sichere Zustand ist der, in dem nichts hinausgeht.
            </p>
            <div>
              <Button href={linkFor(PAGE_PATH, "/legal/governance")} variant="secondary">
                Governance und Datenwege ansehen
              </Button>
            </div>
          </div>
          <HybridProcessingGraphic />
        </div>
      </Section>

      {/* Solutions */}
      <Section tone="page" labelledBy="loesungen">
        <SectionHeader
          id="loesungen"
          eyebrow="Lösungen"
          title="Nach Aufgabe statt nach Produkt"
          lead="Vertragsarbeit, Legal Operations und Governance greifen ineinander. Diese Seiten beschreiben den Weg vom Problem zum prüfbaren Ergebnis."
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
        <SectionHeader id="zielgruppen" eyebrow="Zielgruppen" title="Wer damit arbeitet" className="mb-10" />
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
            <h2 className="sbs-h3 mt-2">Mit welchem Vertragstyp fangen wir an?</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Für einen ersten Termin genügt ein synthetischer Beispielvertrag. Mandantendaten sind
              dafür ausdrücklich nicht nötig.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href={linkFor(PAGE_PATH, "/legal/kontakt?division=legal")} size="lg">
              Demo vereinbaren
            </Button>
            <Button href={linkFor(PAGE_PATH, "/legal/governance")} variant="secondary" size="lg">
              Datenwege ansehen
            </Button>
          </div>
        </div>
      </Section>
    </SiteChrome>
  );
}
