import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { ProductCard } from "@/components/product/ProductCard";
import { productBySlug, productsByDivision } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/industrie/produkte",
  title: "Produkte",
  description:
    "Die Produkte von SBS Industrie: NormPilot für Audit-Evidence, HydraulikDoc für quellengebundene technische Antworten — sowie FlowCheck AI+ als geschäftsübergreifende Backoffice-Automatisierung.",
});

export default function IndustryProducts() {
  const products = productsByDivision("industry");
  const flowcheck = productBySlug("flowcheck")!;

  return (
    <SiteChrome siteKey="industry" path="/industrie/produkte">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Industrie", path: "/industrie" },
          { name: "Produkte", path: "/industrie/produkte" },
        ])}
      />
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="SBS Industrie · Produkte"
          title="Produkte für technische Nachweis- und Dokumentenprozesse"
          lead="Zwei Produkte mit eigener Fachlogik und ein geschäftsübergreifendes Automatisierungsprodukt. Alle drei folgen demselben Ablauf: Dokument, Extraktion, Nachweis, menschliche Prüfung, Ausgabe."
          className="mb-10"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          {products.map((product) => (
            <ProductCard key={product.slug} product={product} currentPath="/industrie/produkte" headingLevel="h2" />
          ))}
        </div>
      </Section>

      <Section tone="sunken" labelledBy="shared">
        <SectionHeader
          id="shared"
          eyebrow="Geschäftsübergreifend"
          title="Backoffice-Automatisierung im industriellen Umfeld"
          lead="FlowCheck AI+ wird auf Unternehmensebene geführt und hier verlinkt, weil Belegverarbeitung im produzierenden Mittelstand regelmäßig dazugehört — ohne die Kernidentität dieses Geschäftsbereichs zu sein."
          className="mb-8"
        />
        <div className="max-w-[38rem]">
          <ProductCard product={flowcheck} currentPath="/industrie/produkte" />
        </div>
      </Section>
    </SiteChrome>
  );
}
