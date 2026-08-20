import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { Section, SectionHeader } from "@/components/ui/Section";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("compliancehub")!;

export const metadata: Metadata = pageMetadata({
  path: "/legal/produkte/compliancehub",
  title: "ComplianceHub",
  description:
    "ComplianceHub verbindet ein mandantenfähiges KI-System-Inventar mit Risikoklassifikation nach EU-AI-Act-Logik, Policy-Auswertung, Verstößen, Vier-Augen-Freigaben und Board-Reporting.",
});

const registers = [
  {
    title: "Transparenzregister",
    body: "Art.-50- und DSGVO-Transparenznachweise mit Verantwortlichen, Prüfenden, Nachweis und Prüfdatum — nicht als Anlage, sondern als Datensatz.",
  },
  {
    title: "Folgenabschätzungen",
    body: "Versionierte DSFA- und FRIA-Datensätze mit eigener Scope-Entscheidung, nachweisnahen Prüffeldern, Vier-Augen-Freigabe und Konsultations-Gates.",
  },
  {
    title: "Kontrollen und Maßnahmen",
    body: "Kontrollen hängen an registrierten Systemen und Pflichten; Maßnahmen tragen Zuständigkeit, Frist und Status.",
  },
  {
    title: "Entscheidungshistorie",
    body: "Policy-Auswertungen und Lifecycle-Änderungen werden mit Akteur, Aktion, Objekt und Verstoßanzahl protokolliert.",
  },
];

export default function ComplianceHubPage() {
  return (
    <SiteChrome siteKey="legal" path="/legal/produkte/compliancehub">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Legal", path: "/legal" },
          { name: "Produkte", path: "/legal/produkte" },
          { name: "ComplianceHub", path: "/legal/produkte/compliancehub" },
        ])}
      />
      <ProductPage
        product={product}
        currentPath="/legal/produkte/compliancehub"
        divisionLabel="SBS Legal"
        divisionHref="/legal"
        extraSections={
          <Section tone="sunken" labelledBy="prozess-titel" id="prozess">
            <SectionHeader
              id="prozess-titel"
              eyebrow="Register"
              title="Vier Bestände, die zusammen den Nachweis tragen"
              lead="Governance scheitert selten an fehlenden Kontrollen, sondern an fehlenden Nachweisen für getroffene Entscheidungen. Deshalb sind diese vier als Datenbestände geführt, nicht als Dokumente."
              className="mb-9"
            />
            <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2">
              {registers.map((entry) => (
                <li key={entry.title} className="flex flex-col gap-2.5 border-t border-[var(--sbs-border)] pt-5">
                  <h3 className="sbs-h4">{entry.title}</h3>
                  <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
                </li>
              ))}
            </ul>
            <p className="mt-9 max-w-[46rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
              ComplianceHub unterstützt Governance und Dokumentation. Es erteilt keine
              Rechtsauskunft, ersetzt keine qualifizierte Prüfung und trifft keine verbindliche
              Freigabeentscheidung. Öffentliche Routen, Enterprise-Routen und Release-Profile bleiben
              technisch getrennt.
            </p>
          </Section>
        }
      />
    </SiteChrome>
  );
}
