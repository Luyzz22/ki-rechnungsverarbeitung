import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { Section, SectionHeader } from "@/components/ui/Section";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("normpilot")!;

export const metadata: Metadata = pageMetadata({
  path: "/industrie/produkte/normpilot",
  title: "NormPilot Industrie",
  description:
    "NormPilot ordnet Bestandsdokumente einzelnen Anforderungen zu, markiert fehlende Nachweise als Gap Finding und überführt sie in reviewbare Maßnahmen — mit Fundstelle, Provenienz und Evidence-Pack-Export.",
});

const boundaries = [
  {
    title: "Kein Norm-Volltext",
    body: "NormPilot speichert und liefert keine ISO-, DIN-, IATF- oder VDA-Volltexte aus. Anforderungen werden als eigene Requirement Items geführt, die Sie selbst verantworten.",
  },
  {
    title: "Kein Zertifizierungsurteil",
    body: "Das System bewertet Nachweislage, nicht Konformität. Es sagt nicht, ob ein Audit bestanden wird, und ersetzt keine Zertifizierungsstelle.",
  },
  {
    title: "Kein ERP- oder QMS-Ersatz",
    body: "NormPilot schreibt nicht in ERP- oder QM-Systeme zurück. Es arbeitet mit dem, was dort bereits dokumentiert ist.",
  },
];

export default function NormPilotPage() {
  return (
    <SiteChrome siteKey="industry" path="/industrie/produkte/normpilot">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Industrie", path: "/industrie" },
          { name: "Produkte", path: "/industrie/produkte" },
          { name: "NormPilot Industrie", path: "/industrie/produkte/normpilot" },
        ])}
      />
      <ProductPage
        product={product}
        currentPath="/industrie/produkte/normpilot"
        divisionLabel="SBS Industrie"
        divisionHref="/industrie"
        extraSections={
          <Section tone="page" rhythm="tight" labelledBy="grenzen-titel" id="grenzen">
            <SectionHeader
              id="grenzen-titel"
              eyebrow="Abgrenzung"
              title="Was NormPilot bewusst nicht tut"
              lead="Diese Grenzen sind im Produkt verankert, nicht nur im Text. Sie bestimmen, welche Aussagen ein Evidence Pack tragen kann."
              className="mb-8"
            />
            <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-7 md:grid-cols-3">
              {boundaries.map((entry) => (
                <li key={entry.title} className="flex flex-col gap-2 border-t border-[var(--sbs-border)] pt-4">
                  <h3 className="sbs-h4">{entry.title}</h3>
                  <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry.body}</p>
                </li>
              ))}
            </ul>
          </Section>
        }
      />
    </SiteChrome>
  );
}
