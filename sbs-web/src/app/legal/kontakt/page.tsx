import { Suspense } from "react";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ContactPage } from "@/components/sections/ContactPage";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/legal/kontakt",
  title: "Kontakt",
  description:
    "Kontakt zu SBS Legal: Demo, Pilot oder Datenwege zu KanzleiAI und ComplianceHub. Für einen ersten Termin genügen synthetische Beispielverträge.",
});

export default function LegalContact() {
  return (
    <SiteChrome siteKey="legal" path="/legal/kontakt">
      <Suspense fallback={null}>
        <ContactPage
          division="legal"
          divisionLabel="SBS Legal"
          intro="Sagen Sie uns, welche Vertragsart oder welche Governance-Pflicht gerade die meiste Arbeit macht. Wir antworten mit einem konkreten Vorschlag, nicht mit einer Standardpräsentation."
          expectations={[
            "Ein erster Termin von rund 30 Minuten, ohne Vorbereitung Ihrerseits.",
            "Der Ablauf wird an einem synthetischen Beispielvertrag gezeigt — Mandantendaten sind dafür nicht nötig.",
            "Auf Wunsch gehen wir den vollständigen Datenweg durch, bevor über Inhalte gesprochen wird.",
          ]}
        />
      </Suspense>
    </SiteChrome>
  );
}
