import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { HybridProcessingGraphic } from "@/components/graphics/ContractAnalysisGraphic";
import { linkFor } from "@/content/site";
import { pageMetadata } from "@/lib/seo";

const PAGE_PATH = "/legal/governance";

export const metadata: Metadata = pageMetadata({
  path: "/legal/governance",
  title: "Governance & Datenwege",
  description:
    "Wie SBS Legal Mandantentrennung, lokale Redaction, Prompt-Governance, Human Review und Audit Trail umsetzt — und welche Aussagen bewusst nicht getroffen werden.",
});

const controls = [
  {
    title: "Mandantentrennung",
    body: "Row-Level-Security trennt Analyseläufe, Findings und Prüfentscheidungen je Mandant. Die Trennung liegt in der Datenbank, nicht in einem Filter der Anwendungsschicht.",
  },
  {
    title: "Lokale Redaction",
    body: "Sanitisierung, Texterkennung, Erkennung, Schwärzung und Minimierung laufen vor jedem Cloud-Aufruf lokal. Das Re-Identifikations-Mapping bleibt verschlüsselt auf dem eigenen Server.",
  },
  {
    title: "Fail-closed-Gate",
    body: "Unsichere Befunde blockieren den Versand. Der sichere Zustand ist der, in dem nichts hinausgeht — nicht der, in dem etwas durchkommt.",
  },
  {
    title: "Prompt-Governance",
    body: "Produktionsprompts kommen aus einer Registry mit Definition und Release. Fehlt ein Release, gilt der explizite Default; ein stiller Prompt-Drift ist ausgeschlossen.",
  },
  {
    title: "Protokollierte Modellwahl",
    body: "Pro Stufe werden Anbieter, Modell und Auswahlgrund am Lauf gespeichert. Ein Fallback ist sichtbar, nicht unsichtbar.",
  },
  {
    title: "Human Review",
    body: "Findings tragen eine eigene Bewertung mit Entscheidung, Kommentar und optional angepasstem Text — rollenbasiert und pro Finding.",
  },
  {
    title: "Vier-Augen-Freigaben",
    body: "Folgenabschätzungen und vergleichbare Nachweise verlangen eine zweite berechtigte Person, bevor sie als abgeschlossen gelten.",
  },
  {
    title: "Versionierte Läufe",
    body: "Jede erneute Analyse erzeugt einen neuen Lauf. Vorherige Ergebnisse und Entscheidungen bleiben erhalten.",
  },
  {
    title: "Evaluation ohne Mandantendaten",
    body: "Ein kuratiertes Golden Set prüft Schema, Extraktion und Findings — mit synthetischen Fällen, nicht mit echten Akten.",
  },
];

const notClaimed = [
  "Keine Zertifikate, Testate oder Prüfsiegel, solange kein abgeschlossenes Prüfverfahren vorliegt.",
  "Keine Genauigkeits-, Zeit- oder Einsparquoten ohne veröffentlichte Messgrundlage.",
  "Keine Kundenlogos, Referenzen oder Testimonials ohne dokumentierte Freigabe.",
  "Keine Aussage, dass ein Einsatz DSGVO-konform ist — das hängt an Vertrag, Rechtsgrundlage, Folgenabschätzung und Betrieb, nicht am Code.",
  "Keine Verfügbarkeits- oder Reaktionszusage außerhalb eines konkreten Vertrags.",
  "Keine automatische Rechts-, Konformitäts- oder Freigabeentscheidung durch das System.",
];

export default function LegalGovernance() {
  return (
    <SiteChrome siteKey="legal" path="/legal/governance">
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="SBS Legal · Governance"
          title="Neun Kontrollen, die im Produkt umgesetzt sind"
          lead="Vertrauen entsteht in diesem Bereich nicht durch Siegel, sondern dadurch, dass sich der Datenweg und die Entscheidungspunkte beschreiben und prüfen lassen."
          className="mb-11"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {controls.map((control) => (
            <li key={control.title} className="flex flex-col gap-2.5 border-t border-[var(--sbs-border)] pt-5">
              <h2 className="sbs-h4 text-[var(--sbs-text-primary)]">{control.title}</h2>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{control.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="sunken" labelledBy="datenweg">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14">
          <SectionHeader
            id="datenweg"
            eyebrow="Datenweg"
            title="Zehn Stationen zwischen Dokument und Prüfentscheidung"
            lead="Nur eine dieser Stationen liegt außerhalb der eigenen Infrastruktur — und sie sieht ausschließlich den minimierten Payload."
          />
          <HybridProcessingGraphic />
        </div>
      </Section>

      <Section tone="inverse" labelledBy="grenzen">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
          <SectionHeader
            id="grenzen"
            eyebrow="Abgrenzung"
            title="Was wir bewusst nicht behaupten"
            lead="Diese Liste steht hier, weil ihr Fehlen auf vielen Anbieterseiten das eigentliche Problem ist."
          />
          <ul className="flex flex-col gap-4">
            {notClaimed.map((item) => (
              <li key={item} className="flex items-start gap-3 border-t border-[var(--sbs-border-inverse)] pt-4">
                <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-gold)]" />
                <span className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-inverse-secondary)]">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section tone="page" rhythm="tight">
        <div className="flex flex-col gap-5 rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
          <div className="max-w-[36rem]">
            <h2 className="sbs-h3">Datenwege vor Inhalten besprechen</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Viele Gespräche in diesem Bereich beginnen sinnvollerweise mit der Frage, was den
              eigenen Server verlässt. Das können wir zuerst durchgehen.
            </p>
          </div>
          <Button href={linkFor(PAGE_PATH, "/legal/kontakt?anliegen=architecture")} size="lg">
            Termin vereinbaren
          </Button>
        </div>
      </Section>
    </SiteChrome>
  );
}
