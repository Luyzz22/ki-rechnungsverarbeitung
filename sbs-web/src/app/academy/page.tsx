import type { Metadata } from "next";
import { SiteChrome } from "@/components/navigation/SiteChrome";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { academyCourses } from "@/content/academy";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  path: "/academy",
  title: "SBS Academy",
  description:
    "SBS Academy bündelt die eigenständigen Lernangebote von SBS Deutschland: PythonPfad und SQLPfad. Beide behalten ihre eigene Marke und ihre eigene Domain.",
});

export default function AcademyPage() {
  return (
    <SiteChrome siteKey="corporate" path="/academy">
      <div data-division="academy">
        <section className="sbs-inverse" data-surface="inverse">
          <div className="sbs-container sbs-section sbs-section--hero">
            <div className="sbs-measure-hero flex flex-col gap-6">
              <Eyebrow>SBS Deutschland · Academy</Eyebrow>
              <h1 className="sbs-display--sm text-[var(--sbs-text-inverse)]">
                Wissen nicht nur automatisieren, sondern aufbauen.
              </h1>
              <p className="sbs-lead">
                Die Lernangebote von SBS sind bewusst eigenständig. Sie gehören weder zu SBS
                Industrie noch zu SBS Legal, laufen unter eigener Marke und unter eigener Domain –
                und sind deshalb auch ohne Produktbezug nutzbar.
              </p>
            </div>
          </div>
        </section>

        <Section tone="page" rhythm="wide" labelledBy="lernpfade">
          <SectionHeader
            id="lernpfade"
            eyebrow="Lernpfade"
            title="Zwei Pfade, aufeinander aufbauend"
            lead="Beide Angebote folgen derselben Idee: nicht Videos ansehen, sondern selbst schreiben — bis der Code im Arbeitsalltag trägt."
            className="mb-10"
          />
          <ul className="grid grid-cols-[minmax(0,1fr)] gap-5 md:grid-cols-2">
            {academyCourses.map((course) => (
              <li
                key={course.slug}
                id={course.slug}
                className="flex flex-col justify-between gap-6 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] p-7"
              >
                <div className="flex flex-col gap-3">
                  <p className="sbs-mono text-[0.6875rem] uppercase tracking-[0.12em] text-[var(--sbs-accent)]">
                    {course.domain}
                  </p>
                  <h2 className="sbs-h3">{course.name}</h2>
                  <p className="text-[1rem] leading-[1.55] text-[var(--sbs-text-primary)]">{course.tagline}</p>
                  <p className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
                    {course.description}
                  </p>
                </div>
                <div className="flex flex-col gap-5">
                  <ul className="flex flex-wrap gap-2">
                    {course.topics.map((topic) => (
                      <li
                        key={topic}
                        className="sbs-mono rounded-[var(--sbs-radius-sm)] border border-[var(--sbs-border)] px-2.5 py-1.5 text-[0.75rem] text-[var(--sbs-text-secondary)]"
                      >
                        {topic}
                      </li>
                    ))}
                  </ul>
                  <Button href={course.url} external size="lg">
                    {course.domain} öffnen
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Section>

        <Section tone="sunken" labelledBy="einordnung">
          <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-2 lg:gap-16">
            <SectionHeader
              id="einordnung"
              eyebrow="Einordnung"
              title="Warum die Academy getrennt geführt wird"
              lead="Lernen und Produktnutzung haben unterschiedliche Zielgruppen, unterschiedliche Erwartungen und unterschiedliche Kaufwege. Eine Vermischung würde beiden schaden."
            />
            <ul className="flex flex-col gap-4">
              {[
                "Die Lernplattformen behalten ihre eigenen Domains als primäre Adresse; diese Seite verweist dorthin, statt sie zu ersetzen.",
                "Die Inhalte setzen kein SBS-Produkt voraus und sind unabhängig davon nutzbar.",
                "Umgekehrt setzt kein SBS-Produkt einen Lernpfad voraus.",
                "Die Verbindung ist die gemeinsame Herkunft — nicht ein gemeinsames Vertriebspaket.",
              ].map((item) => (
                <li key={item} className="flex items-start gap-2.5 border-t border-[var(--sbs-border)] pt-4">
                  <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                  <span className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      </div>
    </SiteChrome>
  );
}
