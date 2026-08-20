import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { LegalDocument } from "@/components/sections/LegalDocument";
import { datenschutzBlocks } from "@/content/legal/datenschutz";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/datenschutz",
  title: "Datenschutzerklärung",
  description:
    "Datenschutzerklärung der SBS Deutschland GmbH & Co. KG: Verarbeitungszwecke, Rechtsgrundlagen, Empfänger, Speicherdauer und Betroffenenrechte.",
});

export default function DatenschutzPage() {
  return (
    <SiteChrome siteKey="corporate" path="/datenschutz">
      <LegalDocument blocks={datenschutzBlocks} />
    </SiteChrome>
  );
}
