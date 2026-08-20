import Link from "next/link";
import { linkFor } from "@/content/site";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";

const destinations = [
  { label: "Startseite", href: "/" },
  { label: "SBS Industrie", href: "/industrie" },
  { label: "SBS Legal", href: "/legal" },
  { label: "Technische Grundlage", href: "/plattform" },
  { label: "SBS Academy", href: "/academy" },
  { label: "Kontakt", href: "/kontakt" },
];

const PAGE_PATH = "/404";

export default function NotFound() {
  return (
    <SiteChrome siteKey="corporate" path="/404">
      <Section tone="page" rhythm="wide">
        <div className="flex max-w-[38rem] flex-col gap-5">
          <Eyebrow>Fehler 404</Eyebrow>
          <h1 className="sbs-display--sm">Diese Seite gibt es hier nicht.</h1>
          <p className="sbs-lead">
            Möglicherweise wurde die Adresse im Zuge des Website-Umbaus verschoben. Die folgenden
            Einstiegspunkte führen zu den wichtigsten Bereichen.
          </p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {destinations.map((destination) => (
              <li key={destination.href}>
                <Link
                  href={linkFor(PAGE_PATH, destination.href)}
                  className="inline-flex min-h-11 items-center rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] px-4 text-[0.875rem] font-[540] text-[var(--sbs-text-primary)] transition-colors duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)]"
                >
                  {destination.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <Button href="/kontakt">Seite melden</Button>
          </div>
        </div>
      </Section>
    </SiteChrome>
  );
}
