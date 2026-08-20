import { Suspense } from "react";
import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { ContactPage } from "@/components/sections/ContactPage";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/kontakt",
  title: "Kontakt",
  description:
    "Kontakt zu SBS Deutschland: allgemeine Anfragen, geschäftsübergreifende Automatisierung, Beratung sowie Weiterleitung an SBS Industrie oder SBS Legal.",
});

export default function CorporateContact() {
  return (
    <SiteChrome siteKey="corporate" path="/kontakt">
      <Suspense fallback={null}>
        <ContactPage
          division="corporate"
          divisionLabel="SBS Deutschland"
          intro="Für Anfragen, die keinem der beiden Geschäftsbereiche eindeutig zuzuordnen sind — oder wenn Sie einfach nicht sicher sind, wo Ihr Thema hingehört."
          expectations={[
            "Ein erster Termin von rund 30 Minuten, ohne Vorbereitung Ihrerseits.",
            "Bei klarer Zuordnung leiten wir intern an SBS Industrie oder SBS Legal weiter.",
            "Eine ehrliche Einschätzung, ob wir für Ihr Vorhaben die richtigen sind.",
          ]}
        />
      </Suspense>
    </SiteChrome>
  );
}
