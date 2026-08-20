import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { LegalDocument } from "@/components/sections/LegalDocument";
import { impressumBlocks } from "@/content/legal/impressum";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/impressum",
  title: "Impressum",
  description: "Impressum und Anbieterkennzeichnung der SBS Deutschland GmbH & Co. KG gemäß § 5 DDG.",
});

export default function ImpressumPage() {
  return (
    <SiteChrome siteKey="corporate" path="/impressum">
      <LegalDocument blocks={impressumBlocks} />
    </SiteChrome>
  );
}
