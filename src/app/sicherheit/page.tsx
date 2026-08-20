import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/sicherheit",
  title: "Sicherheit & Datenwege",
  description:
    "Wie SBS-Produkte Mandantentrennung, Rollen, Protokollierung, Löschwege und Modellaufrufe umsetzen — und welche Aussagen zu Zertifizierung und Konformität bewusst nicht getroffen werden.",
});

const areas = [
  {
    title: "Identität und Zugriff",
    items: [
      "Anmeldung über etablierte Identitätsanbieter (OIDC, Microsoft Entra ID, Google) statt eigener Passwortlogik, wo verfügbar.",
      "Rollenmodelle trennen Upload, Prüfung, Freigabe, Export und Verwaltung.",
      "Sitzungen laufen nach definierter Inaktivität ab.",
    ],
  },
  {
    title: "Mandanten- und Nutzertrennung",
    items: [
      "Row-Level-Security beziehungsweise verpflichtende Nutzerfilter auf Datenbankebene.",
      "Retrieval-Abfragen ohne Mandantenfilter existieren im Produktionspfad nicht.",
      "Automatisierte Tests prüfen die Isolation, statt sie vorauszusetzen.",
    ],
  },
  {
    title: "Dokumente",
    items: [
      "Upload-Validierung und Malware-Prüfung vor der Verarbeitung.",
      "Entfernen eingebetteter Skripte, Dateien und Metadaten vor jeder weiteren Stufe.",
      "Private Speicherung ohne öffentlich adressierbare Objekt-URLs.",
    ],
  },
  {
    title: "Modellaufrufe",
    items: [
      "Versionierte Prompts aus einer Registry statt freier Inline-Prompts im Produktionspfad.",
      "Anbieter, Modell und Auswahlgrund werden pro Lauf protokolliert.",
      "Abwehr von Prompt-Injection und gesperrte Verwendungszwecke greifen vor dem Aufruf.",
      "Bei KanzleiAI erreicht das Modell nur einen lokal redigierten, minimierten Payload.",
    ],
  },
  {
    title: "Nachvollziehbarkeit",
    items: [
      "Audit-Events mit Akteur, Aktion und Objekt für audit-relevante Vorgänge.",
      "Provenienz — Quelle, Modell, Prompt-Version, Zeitpunkt, Prüfer — bleibt am Ergebnis.",
      "Erneute Analysen erzeugen neue Läufe statt frühere Ergebnisse zu überschreiben.",
    ],
  },
  {
    title: "Löschung und Aufbewahrung",
    items: [
      "Löschung wird über Objektspeicher, Suchindex und Datenbank propagiert.",
      "Fristablauf wird durch einen eigenen Lauf mit getrennter Datenbankrolle umgesetzt.",
      "Löschvorgänge werden protokolliert.",
    ],
  },
];

const notClaimed = [
  "ISO-, SOC-2- oder BSI-C5-Testate — wir führen keine, solange kein abgeschlossenes Prüfverfahren vorliegt.",
  "Penetrationstest- oder Wiederherstellungsnachweise ohne konkreten Bericht.",
  "Verfügbarkeits- oder Reaktionszusagen außerhalb eines Vertrags.",
  "Die Aussage, ein Einsatz sei DSGVO-konform — das entscheidet sich an Vertrag, Rechtsgrundlage, Folgenabschätzung, Betriebsrat und Betrieb, nicht am Quellcode.",
  "Genauigkeits-, Zeit- oder Einsparquoten ohne veröffentlichte Messgrundlage.",
];

export default function SecurityPage() {
  return (
    <SiteChrome siteKey="corporate" path="/sicherheit">
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section sbs-section--hero">
          <div className="sbs-measure-hero flex flex-col gap-6">
            <Eyebrow>Sicherheit</Eyebrow>
            <h1 className="sbs-display--sm text-[var(--sbs-text-inverse)]">
              Datenwege, Rollen und Protokolle — beschreibbar statt beteuert.
            </h1>
            <p className="sbs-lead">
              Diese Seite listet keine Siegel. Sie beschreibt, welche Kontrollen in den Produkten
              umgesetzt sind, wo die Grenzen liegen und welche Aussagen erst nach einem
              abgeschlossenen Prüfverfahren möglich sind.
            </p>
          </div>
        </div>
      </section>

      <Section tone="page" rhythm="wide" labelledBy="kontrollen">
        <SectionHeader
          id="kontrollen"
          eyebrow="Umgesetzte Kontrollen"
          title="Sechs Bereiche"
          className="mb-11"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-10 md:grid-cols-2 lg:grid-cols-3">
          {areas.map((area) => (
            <li key={area.title} className="flex flex-col gap-3 border-t border-[var(--sbs-border)] pt-5">
              <h3 className="sbs-h4 text-[var(--sbs-text-primary)]">{area.title}</h3>
              <ul className="flex flex-col gap-2">
                {area.items.map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                    <span className="text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        <p className="mt-10 max-w-[46rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
          Der Umfang unterscheidet sich je Produkt. Welche Kontrollen für ein konkretes Produkt und
          eine konkrete Instanz gelten, klären wir vor einem Pilot verbindlich, statt es hier zu
          verallgemeinern.
        </p>
      </Section>

      <Section tone="inverse" labelledBy="nicht">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
          <SectionHeader
            id="nicht"
            eyebrow="Abgrenzung"
            title="Was hier bewusst nicht steht"
            lead="Diese Liste ist Teil der Aussage. Ihr Fehlen wäre die eigentliche Ungenauigkeit."
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
            <h2 className="sbs-h3">Prüfung durch Ihre Sicherheits- und Datenschutzfunktion</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Wir stellen die Architektur- und Kontrollunterlagen für ein konkretes Produkt gern vor
              einer Produktdemonstration bereit.
            </p>
          </div>
          <Button href="/kontakt?anliegen=architecture" size="lg">
            Unterlagen anfragen
          </Button>
        </div>
      </Section>
    </SiteChrome>
  );
}
