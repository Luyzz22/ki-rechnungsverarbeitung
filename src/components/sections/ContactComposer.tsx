"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { CONTACT_EMAIL } from "@/content/site";
import { productBySlug } from "@/content/products";
import { solutions } from "@/content/solutions";

const divisionLabels = {
  industry: "SBS Industrie",
  legal: "SBS Legal",
  corporate: "SBS Deutschland",
} as const;

const topics = [
  { id: "demo", label: "Demo ansehen" },
  { id: "pilot", label: "Pilot besprechen" },
  { id: "architecture", label: "Technische Architektur" },
  { id: "other", label: "Anderes Anliegen" },
] as const;

/**
 * Builds a pre-filled mail with the same context a form would have posted.
 * Nothing is submitted anywhere, so nothing can be silently lost — the visitor
 * sees exactly what leaves their machine.
 */
export function ContactComposer({ division }: { division: "industry" | "legal" | "corporate" }) {
  const params = useSearchParams();
  const [topic, setTopic] = useState<(typeof topics)[number]["id"]>("demo");
  const [organisation, setOrganisation] = useState("");
  const [message, setMessage] = useState("");

  const productSlug = params.get("product");
  const solutionSlug = params.get("solution");
  const product = productSlug ? productBySlug(productSlug) : undefined;
  const solution = solutionSlug ? solutions.find((entry) => entry.slug === solutionSlug) : undefined;

  const context = useMemo(() => {
    const lines = [`Bereich: ${divisionLabels[division]}`];
    if (product) lines.push(`Produkt: ${product.name}`);
    if (solution) lines.push(`Lösung: ${solution.title}`);
    lines.push(`Anliegen: ${topics.find((entry) => entry.id === topic)?.label ?? ""}`);
    if (organisation.trim()) lines.push(`Organisation: ${organisation.trim()}`);
    return lines;
  }, [division, product, solution, topic, organisation]);

  const subject = product
    ? `Anfrage ${product.name} — ${divisionLabels[division]}`
    : solution
      ? `Anfrage ${solution.title} — ${divisionLabels[division]}`
      : `Anfrage — ${divisionLabels[division]}`;

  const body = [...context, "", message.trim() || "Kurz zum Hintergrund:", ""].join("\n");

  const href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  const fieldClass =
    "w-full rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-page)] px-3.5 py-2.5 text-[0.9375rem] text-[var(--sbs-text-primary)] placeholder:text-[var(--sbs-text-muted)]";

  return (
    <div className="rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-6 lg:p-8">
      <p className="sbs-eyebrow mb-1">Anfrage vorbereiten</p>
      <p className="mb-6 text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
        Die Angaben werden nirgendwo gespeichert oder übertragen. Sie öffnen am Ende eine
        vorbereitete E-Mail in Ihrem eigenen Mailprogramm.
      </p>

      <div className="flex flex-col gap-5">
        <fieldset className="flex flex-col gap-2.5 border-0 p-0">
          <legend className="mb-1 text-[0.875rem] font-[580] text-[var(--sbs-text-primary)]">Anliegen</legend>
          <div className="flex flex-wrap gap-2">
            {topics.map((entry) => (
              <label
                key={entry.id}
                className={`inline-flex min-h-11 cursor-pointer items-center rounded-[var(--sbs-radius-md)] border px-3.5 text-[0.875rem] transition-colors duration-[var(--sbs-motion-fast)] ${
                  topic === entry.id
                    ? "border-[var(--sbs-accent)] bg-[var(--sbs-accent-soft)] text-[var(--sbs-accent-strong)]"
                    : "border-[var(--sbs-border)] bg-[var(--sbs-bg-page)] text-[var(--sbs-text-secondary)]"
                }`}
              >
                <input
                  type="radio"
                  name="anliegen"
                  value={entry.id}
                  checked={topic === entry.id}
                  onChange={() => setTopic(entry.id)}
                  className="sr-only"
                />
                {entry.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-2">
          <label htmlFor="organisation" className="text-[0.875rem] font-[580] text-[var(--sbs-text-primary)]">
            Organisation <span className="font-[400] text-[var(--sbs-text-muted)]">(optional)</span>
          </label>
          <input
            id="organisation"
            type="text"
            value={organisation}
            onChange={(event) => setOrganisation(event.target.value)}
            className={fieldClass}
            placeholder="Musterwerk GmbH"
            autoComplete="organization"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="nachricht" className="text-[0.875rem] font-[580] text-[var(--sbs-text-primary)]">
            Hintergrund <span className="font-[400] text-[var(--sbs-text-muted)]">(optional)</span>
          </label>
          <textarea
            id="nachricht"
            rows={4}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className={`${fieldClass} resize-y`}
            placeholder="Worum geht es konkret?"
          />
        </div>

        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-page)] p-3.5">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Wird übernommen</p>
          <ul className="flex flex-col gap-1">
            {context.map((line) => (
              <li key={line} className="sbs-mono text-[0.75rem] leading-[1.5] text-[var(--sbs-text-secondary)]">
                {line}
              </li>
            ))}
          </ul>
        </div>

        <a
          href={href}
          data-analytics-event="contact_submit"
          data-analytics-division={division}
          className="group inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--sbs-radius-md)] bg-[var(--sbs-accent)] px-6 text-[1rem] font-[560] text-[var(--sbs-accent-contrast)] shadow-[var(--sbs-shadow-sm)] transition-colors duration-[var(--sbs-motion-fast)] hover:bg-[var(--sbs-accent-strong)]"
        >
          E-Mail vorbereiten
          <span
            aria-hidden="true"
            className="transition-transform duration-[var(--sbs-motion-fast)] group-hover:translate-x-[3px] motion-reduce:transition-none"
          >
            →
          </span>
        </a>
      </div>
    </div>
  );
}
