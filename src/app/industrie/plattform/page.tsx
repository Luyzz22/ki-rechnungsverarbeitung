import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { ArchitectureFlow } from "@/components/graphics/ArchitectureFlow";
import { FoundationGrid } from "@/components/sections/FoundationGrid";
import { linkFor } from "@/content/site";
import { pageMetadata } from "@/lib/seo";

const PAGE_PATH = "/industrie/plattform";

export const metadata: Metadata = pageMetadata({
  path: "/industrie/plattform",
  title: "Plattform & Architektur",
  description:
    "Die technische Grundlage hinter SBS Industrie: Dokumentvalidierung, Layout-Extraktion, mandantengefiltertes Retrieval, menschliche Prüfung als Zustand und ein Audit Trail mit vollständiger Provenienz.",
});

const guarantees = [
  {
    title: "Extraktion vor Modell",
    body: "Layout- und Tabellenextraktion ist ein eigener, deterministischer Schritt. Ein Modell sieht nie das rohe PDF, sondern strukturierte Evidenz.",
  },
  {
    title: "Mandantenfilter ist nicht optional",
    body: "Retrieval-Abfragen ohne Mandantenfilter existieren im Produktionspfad nicht. Die Trennung liegt in der Datenbank, nicht in einem Anwendungsschalter.",
  },
  {
    title: "Fehlende Quelle bricht ab",
    body: "Ein Ergebnis ohne gültige Quellenmarke wird verworfen, nicht abgeschwächt formuliert. Es entsteht kein Datensatz.",
  },
  {
    title: "Freigabe ist ein Zustand",
    body: "Entwurf, angenommen, abgelehnt und eskaliert sind unterschiedliche Zustände mit unterschiedlichen Berechtigungen — nicht ein Häkchen im Frontend.",
  },
  {
    title: "Löschung wirkt überall",
    body: "Löschung und Fristablauf werden über Objektspeicher, Suchindex und Datenbank propagiert und protokolliert.",
  },
  {
    title: "Grenzen sind implementiert",
    body: "Gesperrte Verwendungszwecke, Prompt-Injection-Abwehr und ausgeschlossene Funktionen greifen vor dem Modellaufruf, nicht danach.",
  },
];

export default function IndustryPlatform() {
  return (
    <SiteChrome siteKey="industry" path="/industrie/plattform">
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="SBS Industrie · Plattform"
          title="Die Grundlage unter beiden Produkten"
          lead="NormPilot und HydraulikDoc lösen verschiedene Aufgaben, aber sie verarbeiten, prüfen und protokollieren nach denselben Regeln. Diese Regeln stehen hier."
          className="mb-11"
        />
        <FoundationGrid headingLevel="h2" />
      </Section>

      <Section tone="inverse" labelledBy="ablauf">
        <SectionHeader
          id="ablauf"
          eyebrow="Ablauf"
          title="Vom Eingang bis zum Nachweis"
          lead="Sechs Stationen, an denen Station vier immer ein Mensch ist."
          className="mb-12"
        />
        <ArchitectureFlow tone="inverse" />
      </Section>

      <Section tone="page" labelledBy="zusagen">
        <SectionHeader
          id="zusagen"
          eyebrow="Verhalten"
          title="Sechs Eigenschaften, die im Code stehen"
          lead="Keine dieser Aussagen ist eine Absichtserklärung. Jede lässt sich im Produkt zeigen."
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {guarantees.map((entry) => (
            <li key={entry.title} className="flex flex-col gap-2.5 border-l-2 border-[var(--sbs-accent)] pl-4">
              <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">{entry.title}</h3>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
            </li>
          ))}
        </ul>
        <p className="mt-9 max-w-[46rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
          Zertifizierungen, Testate, Penetrationstest-Ergebnisse und Verfügbarkeitszusagen werden
          hier nicht behauptet. Sie sind instanz- und vertragsbezogene Nachweise und werden pro
          Deployment erbracht.
        </p>
        <div className="mt-8">
          <Button href={linkFor(PAGE_PATH, "/industrie/kontakt?anliegen=architecture")} variant="secondary">
            Architektur im Detail besprechen
          </Button>
        </div>
      </Section>
    </SiteChrome>
  );
}
