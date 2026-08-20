import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { CONTACT_EMAIL } from "@/content/site";
import { ContactComposer } from "./ContactComposer";

/**
 * Contact (§61).
 *
 * There is no lead-capture backend for this marketing layer yet, so this page
 * does not publish a form that silently drops submissions. It composes a
 * pre-filled mail instead, carrying the same context a form would have sent:
 * division, product or solution from the URL.
 */
export function ContactPage({
  divisionLabel,
  division,
  intro,
  expectations,
}: {
  divisionLabel: string;
  division: "industry" | "legal" | "corporate";
  intro: string;
  expectations: string[];
}) {
  return (
    <>
      <Section tone="page" rhythm="wide" labelledBy="kontakt">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-16">
          <div className="flex flex-col gap-6">
            <SectionHeader
              as="h1"
              id="kontakt"
              eyebrow={`${divisionLabel} · Kontakt`}
              title="Gespräch vereinbaren"
              lead={intro}
            />
            <div className="flex flex-col gap-3 border-t border-[var(--sbs-border)] pt-6">
              <Eyebrow>Was Sie erwartet</Eyebrow>
              <ul className="flex flex-col gap-2.5">
                {expectations.map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                    <span className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col gap-1.5 border-t border-[var(--sbs-border)] pt-6">
              <Eyebrow>Direkt</Eyebrow>
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="sbs-mono inline-flex min-h-9 items-center text-[0.9375rem] text-[var(--sbs-accent)] underline-offset-4 hover:underline"
              >
                {CONTACT_EMAIL}
              </a>
            </div>
          </div>

          <ContactComposer division={division} />
        </div>
      </Section>
    </>
  );
}
