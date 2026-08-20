import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { Section, SectionHeader } from "@/components/ui/Section";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("hydraulikdoc")!;

export const metadata: Metadata = pageMetadata({
  path: "/industrie/produkte/hydraulikdoc",
  title: "HydraulikDoc",
  description:
    "HydraulikDoc verbindet Anlagenregister, technische PDF-Dokumentation und Zustandsdaten zu einer kontrollierten Beweiskette: quellengebundene Antworten, deterministische Zustandsbewertung und review-gebundener Export.",
});

const architecture = [
  { layer: "Edge", detail: "Web Application Firewall, TLS, Rate Limiting und Bot-Regeln vor der Anwendung." },
  { layer: "Identität", detail: "Microsoft Entra ID mit App-Rollen und Idle-Timeout statt anwendungseigener Benutzerverwaltung." },
  { layer: "Compute", detail: "Container mit Managed Identity und schreibgeschütztem Dateisystem, mindestens zwei Replikate." },
  { layer: "Dokumente", detail: "Privater Objektspeicher mit Malware-Prüfung beim Upload; keine öffentlichen Objekt-URLs." },
  { layer: "Extraktion", detail: "Layout-Extraktion mit Tabellenerkennung als eigener Schritt vor jedem Modellaufruf." },
  { layer: "Retrieval", detail: "Hybride Volltext- und Vektorsuche mit verpflichtendem Tenant-Filter." },
  { layer: "Generierung", detail: "Temperatur 0, versionierter Prompt, Zitatvalidierung als harte Bedingung." },
  { layer: "Fachdaten", detail: "PostgreSQL mit erzwungener Row-Level-Security, private Netzwerkanbindung." },
  { layer: "Secrets", detail: "Key Vault und Managed Identity; statische Service-Keys sind in Produktion ausgeschlossen." },
  { layer: "Lifecycle", detail: "Täglicher Job mit eigener Datenbankrolle löscht abgelaufene Daten aus Index, Speicher und Datenbank." },
];

export default function HydraulikDocPage() {
  return (
    <SiteChrome siteKey="industry" path="/industrie/produkte/hydraulikdoc">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Industrie", path: "/industrie" },
          { name: "Produkte", path: "/industrie/produkte" },
          { name: "HydraulikDoc", path: "/industrie/produkte/hydraulikdoc" },
        ])}
      />
      <ProductPage
        product={product}
        currentPath="/industrie/produkte/hydraulikdoc"
        divisionLabel="SBS Industrie"
        divisionHref="/industrie"
        extraSections={
          <Section tone="sunken" labelledBy="architektur-titel" id="architektur">
            <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-14">
              <SectionHeader
                id="architektur-titel"
                eyebrow="Architektur"
                title="Zehn Ebenen, jede mit einer festgelegten Rolle"
                lead="Der Produktionspfad ist bewusst auf eine Cloud-Umgebung begrenzt, damit Identität, Speicherung, Suche und Löschung einem einzigen Berechtigungsmodell folgen."
              />
              <dl className="flex flex-col">
                {architecture.map((entry) => (
                  <div
                    key={entry.layer}
                    className="grid grid-cols-[minmax(0,1fr)] gap-1 border-t border-[var(--sbs-border)] py-3.5 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-4"
                  >
                    <dt className="sbs-mono text-[0.75rem] uppercase tracking-[0.08em] text-[var(--sbs-accent)]">
                      {entry.layer}
                    </dt>
                    <dd className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.detail}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <p className="mt-8 max-w-[46rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
              Die Architektur ist als Infrastructure-as-Code hinterlegt. Ob eine konkrete Instanz
              regional, vertraglich und organisatorisch geeignet ist, bleibt Deployment-Evidenz und
              wird pro Kundeninstanz nachgewiesen — nicht aus dem Code abgeleitet.
            </p>
          </Section>
        }
      />
    </SiteChrome>
  );
}
