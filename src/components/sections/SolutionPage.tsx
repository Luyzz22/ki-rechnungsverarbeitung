import Link from "next/link";
import type { Solution } from "@/content/types";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { productBySlug } from "@/content/products";
import { linkFor } from "@/content/site";

/**
 * Solution page template (§24, §33). A solution is a job, not a product: the
 * page opens with the problem in the visitor's words and only then names the
 * products that carry parts of the answer.
 */
export function SolutionPage({
  solution,
  currentPath,
  divisionLabel,
  divisionHref,
  contactHref,
}: {
  solution: Solution;
  /** Route this page is published at; decides relative vs cross-site hrefs. */
  currentPath: string;
  divisionLabel: string;
  divisionHref: string;
  contactHref: string;
}) {
  const involved = solution.productSlugs
    .map((slug) => productBySlug(slug))
    .filter((product): product is NonNullable<typeof product> => Boolean(product));

  return (
    <>
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section">
          <div className="flex max-w-[42rem] flex-col gap-5">
            <nav aria-label="Brotkrumen">
              <ol className="sbs-eyebrow flex min-h-9 flex-wrap items-center gap-x-2 gap-y-1">
                <li>
                  <Link href={linkFor(currentPath, divisionHref)} className="inline-flex min-h-9 items-center hover:underline">
                    {divisionLabel}
                  </Link>
                </li>
                <li aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">/</li>
                <li>
                  <Link href={linkFor(currentPath, `${divisionHref}/loesungen`)} className="inline-flex min-h-9 items-center hover:underline">
                    Lösungen
                  </Link>
                </li>
                <li aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">/</li>
                <li aria-current="page" className="text-[var(--sbs-text-inverse)]">
                  {solution.title}
                </li>
              </ol>
            </nav>
            <h1 className="sbs-display--sm text-[var(--sbs-text-inverse)]">{solution.title}</h1>
            <p className="sbs-lead">{solution.problem}</p>
          </div>
        </div>
      </section>

      <Section tone="page" labelledBy="ergebnis">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14">
          <SectionHeader id="ergebnis" eyebrow="Ergebnis" title="Was danach anders ist" lead={solution.outcome} />
          <div>
            <p className="sbs-eyebrow mb-4 text-[var(--sbs-text-muted)]">Weg dorthin</p>
            <ol className="flex flex-col">
              {solution.steps.map((step, index) => (
                <li key={step} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4">
                  <div className="flex flex-col items-center">
                    <span
                      aria-hidden="true"
                      className="mt-[0.4rem] flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--sbs-accent)] bg-[var(--sbs-accent-soft)]"
                    >
                      <span className="sbs-mono text-[0.625rem] text-[var(--sbs-accent-strong)]">{index + 1}</span>
                    </span>
                    {index < solution.steps.length - 1 ? (
                      <span
                        aria-hidden="true"
                        className="w-px flex-1"
                        style={{ background: "var(--sbs-signal-line)", minHeight: "1rem" }}
                      />
                    ) : null}
                  </div>
                  <p className="pb-5 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </Section>

      <Section tone="sunken" labelledBy="produkte">
        <SectionHeader
          id="produkte"
          eyebrow="Beteiligte Produkte"
          title={involved.length > 1 ? "Diese Produkte tragen den Ablauf" : "Dieses Produkt trägt den Ablauf"}
          className="mb-8"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-2">
          {involved.map((product) => (
            <li key={product.slug}>
              <Link
                href={linkFor(currentPath, product.href)}
                className="group flex h-full flex-col gap-2.5 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] p-6 transition-[border-color,box-shadow] duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-border-strong)] hover:shadow-[var(--sbs-shadow-md)]"
              >
                <h3 className="sbs-h4 flex items-center gap-2">
                  {product.name}
                  <span
                    aria-hidden="true"
                    className="text-[var(--sbs-accent)] opacity-0 transition-opacity duration-[var(--sbs-motion-fast)] group-hover:opacity-100"
                  >
                    →
                  </span>
                </h3>
                <p className="text-[0.875rem] leading-[1.55] text-[var(--sbs-text-secondary)]">{product.tagline}</p>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="page" rhythm="tight">
        <div className="flex flex-col gap-5 rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
          <div className="max-w-[34rem]">
            <Eyebrow>Nächster Schritt</Eyebrow>
            <h2 className="sbs-h3 mt-2">{solution.title} im eigenen Kontext prüfen</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Wir gehen den Ablauf an einem konkreten Ausschnitt durch — mit Ihren Unterlagen oder
              mit synthetischen Beispieldaten.
            </p>
          </div>
          <Button href={linkFor(currentPath, `${contactHref}?solution=${solution.slug}`)} size="lg">
            Gespräch vereinbaren
          </Button>
        </div>
      </Section>
    </>
  );
}
