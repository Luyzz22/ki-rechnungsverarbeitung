import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { FoundationGrid } from "@/components/sections/FoundationGrid";
import { ArchitectureFlow } from "@/components/graphics/ArchitectureFlow";
import { ProductCard } from "@/components/product/ProductCard";
import { productBySlug } from "@/content/products";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/plattform",
  title: "Technische Grundlage",
  description:
    "Die gemeinsame technische Grundlage hinter allen SBS-Produkten: Dokumentverarbeitung, typisierte Daten, versionierte Modellaufrufe, menschliche Prüfung als Zustand, Nachvollziehbarkeit und Integration.",
});

const decisions = [
  {
    title: "Extraktion ist ein eigener Schritt",
    body: "Wir schicken kein rohes PDF an ein Modell. Validierung, Sanitisierung und Layout-Extraktion laufen davor und sind deterministisch — sie liefern jedes Mal dasselbe Ergebnis.",
  },
  {
    title: "Ergebnisse sind typisiert",
    body: "Modellausgaben werden gegen ein Schema validiert, bevor sie gespeichert werden. Was das Schema nicht erfüllt, wird nicht zum Datensatz.",
  },
  {
    title: "Läufe statt Überschreiben",
    body: "Jede erneute Analyse erzeugt einen neuen Lauf. Frühere Ergebnisse und die daran hängenden Entscheidungen bleiben erhalten.",
  },
  {
    title: "Prüfung ist ein Zustand, kein Häkchen",
    body: "Entwurf, angenommen, abgelehnt, eskaliert sind unterschiedliche Zustände mit unterschiedlichen Berechtigungen und eigener Historie.",
  },
  {
    title: "Trennung liegt in der Datenbank",
    body: "Mandanten- und Nutzertrennung wird über Row-Level-Security beziehungsweise verpflichtende Filter erzwungen, nicht über Disziplin in der Anwendungsschicht.",
  },
  {
    title: "Fail-closed ist die Voreinstellung",
    body: "Fehlt eine Quelle, ist die Texterkennung unzureichend oder ist ein Befund unklar, bricht der Ablauf ab. Ein plausibles Ergebnis ohne Grundlage entsteht nicht.",
  },
];

export default function PlatformPage() {
  const belegflow = productBySlug("belegflow")!;
  const releaseproof = productBySlug("releaseproof")!;

  return (
    <SiteChrome siteKey="corporate" path="/plattform">
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="Plattform"
          title="Eine Grundlage, auf der beide Geschäftsbereiche stehen"
          lead="SBS betreibt keine Produktsammlung mit zufälligen Gemeinsamkeiten. Industrie und Legal teilen denselben Verarbeitungsweg, dieselben Prüfzustände und dasselbe Protokollmodell."
          className="mb-11"
        />
        <FoundationGrid headingLevel="h2" />
      </Section>

      <Section tone="inverse" labelledBy="ablauf">
        <SectionHeader
          id="ablauf"
          eyebrow="Ablauf"
          title="Sechs Stationen, überall gleich"
          lead="Was in NormPilot eine Evidence-Zeile ist und in KanzleiAI ein Finding, durchläuft dieselben Stationen. Station vier ist immer ein Mensch."
          className="mb-12"
        />
        <ArchitectureFlow tone="inverse" />
      </Section>

      <Section tone="page" labelledBy="entscheidungen">
        <SectionHeader
          id="entscheidungen"
          eyebrow="Architekturentscheidungen"
          title="Sechs Entscheidungen, die den Unterschied ausmachen"
          lead="Diese Entscheidungen kosten Geschwindigkeit und Bequemlichkeit. Sie sind der Grund, warum ein Ergebnis später prüfbar ist."
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {decisions.map((entry) => (
            <li key={entry.title} className="flex flex-col gap-2.5 border-l-2 border-[var(--sbs-accent)] pl-4">
              <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">{entry.title}</h3>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="sunken" labelledBy="darauf">
        <SectionHeader
          id="darauf"
          eyebrow="Auf dieser Grundlage"
          title="Geschäftsübergreifende und unabhängige Produkte"
          lead="Zwei Produkte gehören keinem der beiden Geschäftsbereiche allein. Sie werden deshalb hier geführt."
          className="mb-8"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          <ProductCard product={belegflow} currentPath="/plattform" />
          <ProductCard product={releaseproof} currentPath="/plattform" />
        </div>
      </Section>

      <Section tone="page" rhythm="tight">
        <div className="flex flex-col gap-5 rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
          <div className="max-w-[36rem]">
            <h2 className="sbs-h3">Architektur im Detail besprechen</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Wenn Informationssicherheit, Datenschutz oder IT-Betrieb mit am Tisch sitzen, gehen wir
              den Datenweg zuerst durch — vor jeder Produktdemonstration.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href="/sicherheit" variant="secondary" size="lg">
              Sicherheit &amp; Datenwege
            </Button>
            <Button href="/kontakt?anliegen=architecture" size="lg">
              Termin vereinbaren
            </Button>
          </div>
        </div>
      </Section>
    </SiteChrome>
  );
}
