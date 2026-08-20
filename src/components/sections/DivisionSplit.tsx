import Link from "next/link";
import { products } from "@/content/products";
import { linkFor } from "@/content/site";

/**
 * The corporate division split (§18.2). Each half gets roughly half the
 * viewport, its own accent theme and a rail motif in its own colour — the
 * fastest way for a visitor to see there are exactly two business areas.
 */
const halves = [
  {
    key: "industry" as const,
    eyebrow: "Geschäftsbereich",
    title: "SBS Industrie",
    lead: "Dokumentintelligenz, Audit Evidence und KI-Workflows für Qualität, Service und industrielle Prozesse.",
    href: "/industrie",
    cta: "SBS Industrie öffnen",
    stages: ["Dokument", "Extraktion", "Evidence", "Prüfung", "Maßnahme", "System"],
  },
  {
    key: "legal" as const,
    eyebrow: "Geschäftsbereich",
    title: "SBS Legal",
    lead: "Vertragsanalyse, Human Review und Compliance-Evidence für Rechts- und Governance-Prozesse.",
    href: "/legal",
    cta: "SBS Legal öffnen",
    stages: ["Vertrag", "Extraktion", "Finding", "Risiko", "Review", "Audit Trail"],
  },
];

export function DivisionSplit({ currentPath }: { currentPath: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-px overflow-hidden rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-border-subtle)] lg:grid-cols-2">
      {halves.map((half) => {
        const divisionProducts = products.filter((product) => product.division === half.key);
        return (
          <div
            key={half.key}
            data-division={half.key}
            className="group/half relative flex min-w-0 min-h-[26rem] flex-col justify-between gap-8 bg-[var(--sbs-bg-elevated)] p-7 transition-colors duration-[var(--sbs-motion-normal)] hover:bg-[var(--sbs-accent-soft)] motion-reduce:transition-none lg:min-h-[32rem] lg:p-10"
          >
            <div className="flex flex-col gap-4">
              <p className="sbs-eyebrow">{half.eyebrow}</p>
              <h3 className="sbs-h2 text-[var(--sbs-text-primary)]">{half.title}</h3>
              <p className="sbs-lead max-w-[30rem]">{half.lead}</p>
            </div>

            <DivisionRail stages={half.stages} />

            <div className="flex flex-col gap-5">
              <ul className="flex flex-col gap-2 border-t border-[var(--sbs-border)] pt-5">
                {divisionProducts.map((product) => (
                  <li key={product.slug} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                    <Link
                      href={linkFor(currentPath, product.href)}
                      className="inline-flex min-h-9 items-center text-[0.9375rem] font-[580] text-[var(--sbs-text-primary)] underline-offset-4 hover:text-[var(--sbs-accent-strong)] hover:underline"
                    >
                      {product.name}
                    </Link>
                    <span className="text-[0.8125rem] text-[var(--sbs-text-muted)]">{product.tagline}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={linkFor(currentPath, half.href)}
                className="inline-flex min-h-11 items-center gap-2 self-start text-[0.9375rem] font-[580] text-[var(--sbs-accent)] transition-colors hover:text-[var(--sbs-accent-strong)]"
              >
                {half.cta}
                <span
                  aria-hidden="true"
                  className="transition-transform duration-[var(--sbs-motion-fast)] group-hover/half:translate-x-1 motion-reduce:transition-none"
                >
                  →
                </span>
              </Link>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** The Signal Rail, transformed per division (§9). */
function DivisionRail({ stages }: { stages: string[] }) {
  return (
    <div className="sbs-scroll-x -mx-1 px-1">
      <ol className="flex min-w-max items-center">
        {stages.map((stage, index) => (
          <li key={stage} className="flex items-center">
            {index > 0 ? (
              <span
                aria-hidden="true"
                className="block h-px w-6 lg:w-9"
                style={{ background: "var(--sbs-signal-line)" }}
              />
            ) : null}
            <span className="flex flex-col items-center gap-1.5 px-1">
              <span
                aria-hidden="true"
                className="block h-[6px] w-[6px] rounded-full"
                style={{
                  background: index === stages.length - 2 ? "var(--sbs-gold)" : "var(--sbs-accent)",
                }}
              />
              <span className="sbs-mono whitespace-nowrap text-[0.6875rem] text-[var(--sbs-text-muted)]">
                {stage}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
