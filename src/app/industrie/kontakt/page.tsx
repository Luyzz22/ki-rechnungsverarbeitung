import { Suspense } from "react";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ContactPage } from "@/components/sections/ContactPage";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/industrie/kontakt",
  title: "Kontakt",
  description:
    "Kontakt zu SBS Industrie: Demo, Pilot oder technische Architektur zu NormPilot, HydraulikDoc und der geschäftsübergreifenden Backoffice-Automatisierung.",
});

export default function IndustryContact() {
  return (
    <SiteChrome siteKey="industry" path="/industrie/kontakt">
      <Suspense fallback={null}>
        <ContactPage
          division="industry"
          divisionLabel="SBS Industrie"
          intro="Erzählen Sie uns, welcher Dokumentenbestand Ihnen aktuell Arbeit macht. Wir melden uns mit einem konkreten Vorschlag, nicht mit einer allgemeinen Präsentation."
          expectations={[
            "Ein erster Termin von rund 30 Minuten, ohne Vorbereitung Ihrerseits.",
            "Der Ablauf wird an einem konkreten Ausschnitt gezeigt – Ihre Unterlagen oder synthetische Beispieldaten.",
            "Eine ehrliche Einschätzung, ob und wo ein Pilot sinnvoll ist.",
          ]}
        />
      </Suspense>
    </SiteChrome>
  );
}
