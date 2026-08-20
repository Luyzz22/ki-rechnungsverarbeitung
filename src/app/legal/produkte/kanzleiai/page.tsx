import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { Section, SectionHeader } from "@/components/ui/Section";
import { HybridProcessingGraphic } from "@/components/graphics/ContractAnalysisGraphic";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("kanzleiai")!;

export const metadata: Metadata = pageMetadata({
  path: "/legal/produkte/kanzleiai",
  title: "KanzleiAI",
  description:
    "KanzleiAI analysiert Verträge in zwei schemavalidierten Stufen, redigiert lokal vor jedem Cloud-Aufruf und hält Prompt-Version, Modell, Anbieter und Prüfentscheidung pro Lauf fest.",
});

const intelligence = [
  { title: "Typbezogene Felder", body: "Vertragsart bestimmt, welche Felder erwartet werden – statt eines generischen Extraktionsschemas für alles." },
  { title: "Fehlende Klauseln", body: "Nicht nur was im Vertrag steht, sondern was für diesen Vertragstyp fehlt." },
  { title: "Risikoübersicht", body: "Findings verdichtet nach Schweregrad, mit Zugriff auf den einzelnen Befund." },
  { title: "Signaturstatus", body: "Der Zeichnungsstand als sichtbarer Zustand am Dokument, nicht als Nebeninformation." },
];

export default function KanzleiAiPage() {
  return (
    <SiteChrome siteKey="legal" path="/legal/produkte/kanzleiai">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Legal", path: "/legal" },
          { name: "Produkte", path: "/legal/produkte" },
          { name: "KanzleiAI", path: "/legal/produkte/kanzleiai" },
        ])}
      />
      <ProductPage
        product={product}
        currentPath="/legal/produkte/kanzleiai"
        divisionLabel="SBS Legal"
        divisionHref="/legal"
        extraSections={
          <>
            <Section tone="sunken" labelledBy="datenweg-titel" id="datenweg">
              <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14">
                <div className="flex flex-col gap-5">
                  <SectionHeader
                    id="datenweg-titel"
                    eyebrow="Datenweg"
                    title="Was den Server verlässt — und was nicht"
                    lead="Die lokale Redaction-Pipeline ist der Schutzwall des hybriden Modells. Sie entscheidet nicht über den Cloud-Versand; sie liefert die Evidenz, auf deren Basis ein Policy Gate entscheidet."
                  />
                  <ul className="flex flex-col gap-3 border-t border-[var(--sbs-border)] pt-5">
                    {[
                      "Gesundheits- und Mandatsbegriffe führen zu einem roten Gate — der Versand unterbleibt.",
                      "Liegt die Texterkennung unter der geforderten Abdeckung, wird das Ergebnis als unsicher markiert statt als sauber.",
                      "Kein Textlayer und keine Texterkennung bedeutet Konfidenz null, nicht „leer, also unbedenklich“.",
                      "Ein zusätzlicher Prüfschritt ersetzt Restbefunde im Endtext, auch wenn Koordinaten fehlen.",
                      "Eine Ausgabevalidierung verbietet Original, Mapping und sprechende Kennungen im Payload.",
                    ].map((item) => (
                      <li key={item} className="flex items-start gap-2.5">
                        <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                        <span className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
                    Die Personen- und Organisationserkennung arbeitet bewusst als deterministische
                    Heuristik statt als statistisches Modell, weil Nachvollziehbarkeit hier Vorrang
                    vor Trefferquote hat. Diese Einschränkung benennen wir, statt sie zu verschweigen.
                  </p>
                </div>
                <HybridProcessingGraphic />
              </div>
            </Section>

            <Section tone="page" rhythm="tight" labelledBy="ci">
              <SectionHeader
                id="ci"
                eyebrow="Contract Intelligence"
                title="Vier Bausteine innerhalb von KanzleiAI"
                lead="Contract Intelligence ist kein separates Produkt, sondern die Auswertungsschicht über der Analyse."
                className="mb-8"
              />
              <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-7 sm:grid-cols-2 lg:grid-cols-4">
                {intelligence.map((entry) => (
                  <li key={entry.title} className="flex flex-col gap-2 border-t border-[var(--sbs-border)] pt-4">
                    <h3 className="sbs-h4">{entry.title}</h3>
                    <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
                  </li>
                ))}
              </ul>
            </Section>
          </>
        }
      />
    </SiteChrome>
  );
}
