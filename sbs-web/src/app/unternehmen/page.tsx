import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { RailDivider } from "@/components/ui/Divider";
import { pageMetadata } from "@/lib/seo";
import { ORG_LEGAL_NAME } from "@/content/site";

export const metadata: Metadata = pageMetadata({
  path: "/unternehmen",
  title: "Unternehmen",
  description:
    "SBS Deutschland baut KI-Systeme für Industrie und Recht und berät weiterhin in SAP, IT sowie Quality & Risk Management. Wie wir arbeiten, was wir behaupten und was nicht.",
});

const principles = [
  {
    title: "Mechanismus vor Adjektiv",
    body: "Wir beschreiben, wie ein System arbeitet, statt es als intelligent, revolutionär oder marktführend zu bezeichnen. Wer den Mechanismus kennt, kann selbst beurteilen, ob er passt.",
  },
  {
    title: "Grenzen gehören zum Produkt",
    body: "Was ein System nicht entscheidet, steht in unseren Produkten und auf diesen Seiten. Eine ausgelassene Grenze ist ein Versprechen, das später jemand einlösen muss.",
  },
  {
    title: "Der Mensch bleibt im Ablauf",
    body: "In jedem unserer Produkte gibt es einen Punkt, an dem eine berechtigte Person entscheidet. Dieser Punkt ist keine Bremse, sondern die Stelle, an der Verantwortung sichtbar wird.",
  },
  {
    title: "Nachweise vor Marketing",
    body: "Zertifikate, Kundenlogos und Kennzahlen erscheinen erst, wenn sie belegbar sind. Bis dahin fehlen sie hier lieber, als dass sie unbelegt stehen.",
  },
];

const consulting = [
  {
    title: "SAP Consulting",
    body: "Konzeption, Implementierung und Optimierung in SAP MM, PP und QM — von der Prozessaufnahme bis zum Go-Live.",
  },
  {
    title: "IT Consulting",
    body: "Digitalisierungsstrategie, Cloud-Migration und IT-Infrastruktur für mittelständische Organisationen.",
  },
  {
    title: "Quality & Risk Management",
    body: "Qualitätssicherung, Risikomanagement und Projektsteuerung nach etablierten Standards, einschließlich Projektbüro-Aufbau.",
  },
];

export default function CompanyPage() {
  return (
    <SiteChrome siteKey="corporate" path="/unternehmen">
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section sbs-section--hero">
          <div className="sbs-measure-hero flex flex-col gap-6">
            <Eyebrow>Unternehmen</Eyebrow>
            <h1 className="sbs-display--sm text-[var(--sbs-text-inverse)]">
              Ein Softwareunternehmen, das aus Beratungsarbeit entstanden ist.
            </h1>
            <p className="sbs-lead">
              {ORG_LEGAL_NAME} baut Systeme für Aufgaben, die wir vorher selbst begleitet haben:
              Auditvorbereitung, technische Dokumentation, Vertragsprüfung, Belegverarbeitung. Das
              erklärt, warum unsere Produkte so viel Wert auf Nachweise legen — in diesen Aufgaben
              ist ein Ergebnis ohne Herkunft wertlos.
            </p>
          </div>
        </div>
      </section>

      <Section tone="page" labelledBy="arbeitsweise">
        <SectionHeader
          id="arbeitsweise"
          eyebrow="Arbeitsweise"
          title="Vier Grundsätze, an denen wir gemessen werden können"
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-9 md:grid-cols-2">
          {principles.map((principle) => (
            <li key={principle.title} className="flex flex-col gap-3 border-t border-[var(--sbs-border)] pt-5">
              <h3 className="sbs-h3 text-[var(--sbs-text-primary)]">{principle.title}</h3>
              <p className="text-[0.9375rem] leading-[1.65] text-[var(--sbs-text-secondary)]">{principle.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="sunken" rhythm="tight">
        <RailDivider labels={["Beratung", "Prozessverständnis", "Produkt", "Nachweis"]} />
      </Section>

      <Section tone="page" labelledBy="consulting-titel" id="consulting">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] lg:gap-14">
          <SectionHeader
            id="consulting-titel"
            eyebrow="Beratung & Services"
            title="Beratung neben der Produktarbeit"
            lead="Die Beratungsleistungen laufen weiter, aber sie stehen nicht auf derselben Ebene wie die Produkte. Sie sind der Grund, warum wir die Prozesse kennen, die wir automatisieren."
          />
          <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 sm:grid-cols-3">
            {consulting.map((entry) => (
              <li key={entry.title} className="flex flex-col gap-2.5 border-t border-[var(--sbs-border)] pt-5">
                <h3 className="sbs-h4">{entry.title}</h3>
                <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section tone="inverse" rhythm="tight">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between lg:gap-12">
          <div className="max-w-[38rem]">
            <h2 className="sbs-h3 text-[var(--sbs-text-inverse)]">Zusammenarbeit beginnt mit einer konkreten Aufgabe</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-inverse-secondary)]">
              Nicht mit einer Plattformentscheidung. Wählen Sie den Bereich, der Ihrem Vorhaben
              entspricht — oder schreiben Sie uns allgemein, wenn die Zuordnung noch offen ist.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href="/kontakt" size="lg">
              Kontakt aufnehmen
            </Button>
            <Button href="/sicherheit" variant="inverse" size="lg">
              Sicherheit &amp; Datenwege
            </Button>
          </div>
        </div>
      </Section>
    </SiteChrome>
  );
}
