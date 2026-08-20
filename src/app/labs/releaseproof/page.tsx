import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ProductPage } from "@/components/product/ProductPage";
import { productBySlug } from "@/content/products";
import { pageMetadata, breadcrumbSchema, JsonLd } from "@/lib/seo";

const product = productBySlug("releaseproof")!;

export const metadata: Metadata = pageMetadata({
  path: "/labs/releaseproof",
  title: "ReleaseProof",
  description:
    "ReleaseProof wertet einen definierten Jira-Release-Scope gegen sieben deterministische Regeln aus und liefert Score, Findings und eine Evidence-Matrix auf Issue-Ebene — ohne generative KI und ohne Schreibrechte.",
});

export default function ReleaseProofPage() {
  return (
    <SiteChrome siteKey="corporate" path="/labs/releaseproof">
      <JsonLd
        data={breadcrumbSchema([
          { name: "SBS Labs", path: "/labs/releaseproof" },
          { name: "ReleaseProof", path: "/labs/releaseproof" },
        ])}
      />
      <ProductPage product={product} currentPath="/labs/releaseproof" divisionLabel="SBS Labs" divisionHref="/plattform" />
    </SiteChrome>
  );
}
