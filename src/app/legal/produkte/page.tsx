import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader } from "@/components/ui/Section";
import { ProductCard } from "@/components/product/ProductCard";
import { productsByDivision } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/legal/produkte",
  title: "Produkte",
  description:
    "Die Produkte von SBS Legal: KanzleiAI für strukturierte Vertragsanalyse mit Human Review und ComplianceHub für KI-System-Inventar, Risikoklassifikation und Nachweise.",
});

export default function LegalProducts() {
  const products = productsByDivision("legal");
  return (
    <SiteChrome siteKey="legal" path="/legal/produkte">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Legal", path: "/legal" },
          { name: "Produkte", path: "/legal/produkte" },
        ])}
      />
      <Section tone="page" rhythm="wide" labelledBy="titel">
        <SectionHeader
          as="h1"
          id="titel"
          eyebrow="SBS Legal · Produkte"
          title="Produkte für Vertrags-, Compliance- und Governance-Arbeit"
          lead="Zwei Produkte, die dasselbe Nachweismodell teilen: Finding, Schweregrad, Zuständigkeit, Prüfentscheidung, Protokoll."
          className="mb-10"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          {products.map((product) => (
            <ProductCard key={product.slug} product={product} currentPath="/legal/produkte" headingLevel="h2" />
          ))}
        </div>
      </Section>

      <Section tone="sunken" rhythm="tight" labelledBy="ci">
        <div className="max-w-[46rem]">
          <h2 id="ci" className="sbs-h3">
            Und Contract Intelligence?
          </h2>
          <p className="mt-3 text-[0.9375rem] leading-[1.65] text-[var(--sbs-text-secondary)]">
            Contract Intelligence ist kein eigenes Produkt, sondern der Teil von KanzleiAI, der
            strukturierte Vertragsfelder, fehlende Klauseln, Risikoübersicht und Signaturstatus
            zusammenführt. Ein früheres eigenständiges Analyse-Backend ist inzwischen in diese
            Produktarchitektur aufgegangen. Wir führen es deshalb dort, wo es liegt — und nicht als
            drittes Produkt in dieser Liste.
          </p>
        </div>
      </Section>
    </SiteChrome>
  );
}
