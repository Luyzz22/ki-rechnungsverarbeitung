import Link from "next/link";
import type { ReactNode } from "react";
import type { Product } from "@/content/types";
import { Section, SectionHeader, Eyebrow } from "@/components/ui/Section";
import { Button } from "@/components/ui/Button";
import { ProductGraphic } from "@/components/graphics";
import { relatedProducts } from "@/content/products";
import { solutions } from "@/content/solutions";
import { linkFor } from "@/content/site";

/**
 * Shared information architecture for every product page (§36). The sections
 * are the same everywhere; the content, the graphic and the pipeline are the
 * product's own, so two product pages never read as the same page recoloured.
 */
export function ProductPage({
  product,
  currentPath,
  divisionLabel,
  divisionHref,
  extraSections,
}: {
  product: Product;
  /** Route this page is published at; decides relative vs cross-site hrefs. */
  currentPath: string;
  divisionLabel: string;
  divisionHref: string;
  /** Product-specific sections inserted after the mechanism section. */
  extraSections?: ReactNode;
}) {
  const related = relatedProducts(product);
  const linkedSolutions = solutions.filter((solution) => solution.productSlugs.includes(product.slug));

  return (
    <>
      {/* 1 + 2 — eyebrow with division context, outcome hero */}
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section sbs-section--hero">
          <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-center lg:gap-14">
            <div className="flex max-w-[38rem] flex-col gap-5">
              <nav aria-label="Brotkrumen">
                <ol className="sbs-eyebrow flex min-h-9 flex-wrap items-center gap-x-2 gap-y-1">
                  <li>
                    <Link href={linkFor(currentPath, "/")} className="inline-flex min-h-9 items-center hover:underline">
                      SBS Deutschland
                    </Link>
                  </li>
                  <li aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">
                    /
                  </li>
                  <li>
                    <Link href={linkFor(currentPath, divisionHref)} className="inline-flex min-h-9 items-center hover:underline">
                      {divisionLabel}
                    </Link>
                  </li>
                  <li aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">
                    /
                  </li>
                  <li aria-current="page" className="text-[var(--sbs-text-inverse)]">
                    {product.shortName}
                  </li>
                </ol>
              </nav>

              <h1 className="sbs-display--sm text-[var(--sbs-text-inverse)]">{product.outcome}</h1>
              <p className="sbs-lead">{product.description}</p>

              <div className="flex flex-wrap gap-3 pt-1">
                <Button
                  href={linkFor(currentPath, product.primaryAction.href)}
                  external={product.primaryAction.external}
                  size="lg"
                >
                  {product.primaryAction.label}
                </Button>
                {product.secondaryAction ? (
                  <Button
                    href={linkFor(currentPath, product.secondaryAction.href)}
                    external={product.secondaryAction.external}
                    variant="inverse"
                    size="lg"
                  >
                    {product.secondaryAction.label}
                  </Button>
                ) : null}
              </div>
            </div>

            {/* 3 — real product graphic */}
            <div>
              <ProductGraphic graphic={product.graphic} />
            </div>
          </div>
        </div>
      </section>

      {/* 4 — mechanism */}
      <Section tone="page" labelledBy={`${product.slug}-mechanismus`}>
        <SectionHeader
          id={`${product.slug}-mechanismus`}
          eyebrow="Mechanismus"
          title="Wie es funktioniert"
          lead={`Der Ablauf von ${product.name} in den Schritten, die im Produkt tatsächlich existieren. Der Schritt in Gold ist der, an dem ein Mensch entscheidet.`}
          className="mb-10"
        />
        <ol className="grid grid-cols-[minmax(0,1fr)] gap-x-6 gap-y-7 sm:grid-cols-2 lg:grid-cols-4">
          {product.pipeline.map((stage, index) => (
            <li key={stage.id} className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: stage.human ? "var(--sbs-gold)" : "var(--sbs-accent)" }}
                />
                <span aria-hidden="true" className="h-px flex-1 bg-[var(--sbs-signal-line)]" />
                <span className="sbs-mono text-[0.625rem] uppercase tracking-[0.1em] text-[var(--sbs-text-muted)]">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <h3 className="text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">{stage.label}</h3>
              <p className="text-[0.8125rem] leading-[1.55] text-[var(--sbs-text-secondary)]">{stage.detail}</p>
              {stage.annotation ? (
                <p
                  className="sbs-mono text-[0.6875rem]"
                  style={{ color: stage.human ? "var(--sbs-gold)" : "var(--sbs-text-muted)" }}
                >
                  {stage.annotation}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </Section>

      {extraSections}

      {/* 5 — capabilities */}
      <Section tone="sunken" labelledBy={`${product.slug}-funktionen`}>
        <SectionHeader
          id={`${product.slug}-funktionen`}
          eyebrow="Funktionen"
          title="Was das Produkt konkret leistet"
          className="mb-10"
        />
        <ul className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {product.capabilities.map((capability) => (
            <li key={capability.title} className="flex flex-col gap-2.5 border-t border-[var(--sbs-border)] pt-5">
              <h3 className="sbs-h4 text-[var(--sbs-text-primary)]">{capability.title}</h3>
              <p className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
                {capability.description}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      {/* 6 — workflow before/after */}
      <Section tone="page" labelledBy={`${product.slug}-vorher-nachher`}>
        <SectionHeader
          id={`${product.slug}-vorher-nachher`}
          eyebrow="Veränderung"
          title="Vorher, mit SBS, nachher"
          className="mb-10"
        />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-px overflow-hidden rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border)] bg-[var(--sbs-border)] lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
          <div className="bg-[var(--sbs-bg-elevated)] p-6 lg:p-8">
            <p className="sbs-eyebrow mb-4 text-[var(--sbs-text-muted)]">Vorher</p>
            <ul className="flex flex-col gap-3">
              {product.workflow.before.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-border-strong)]" />
                  <span className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center justify-center bg-[var(--sbs-bg-sunken)] px-6 py-4 lg:px-6">
            <p className="sbs-mono whitespace-nowrap text-[0.6875rem] uppercase tracking-[0.12em] text-[var(--sbs-accent)]">
              {product.shortName}
            </p>
          </div>

          <div className="bg-[var(--sbs-bg-elevated)] p-6 lg:p-8">
            <p className="sbs-eyebrow mb-4">Nachher</p>
            <ul className="flex flex-col gap-3">
              {product.workflow.after.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                  <span className="text-[0.875rem] leading-[1.6] text-[var(--sbs-text-primary)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      {/* 8 — integrations / audience */}
      <Section tone="sunken" rhythm="tight" labelledBy={`${product.slug}-umgebung`}>
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <h2 id={`${product.slug}-umgebung`} className="sbs-h3 mb-4">
              Für wen es gebaut ist
            </h2>
            <ul className="flex flex-col gap-2">
              {product.audience.map((entry) => (
                <li key={entry} className="flex items-start gap-2.5">
                  <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]" />
                  <span className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">{entry}</span>
                </li>
              ))}
            </ul>
          </div>
          {product.integrations?.length ? (
            <div>
              <h2 className="sbs-h3 mb-4">Umgebung und Anbindung</h2>
              <ul className="flex flex-wrap gap-2">
                {product.integrations.map((integration) => (
                  <li
                    key={integration}
                    className="sbs-mono rounded-[var(--sbs-radius-sm)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-elevated)] px-2.5 py-1.5 text-[0.75rem] text-[var(--sbs-text-secondary)]"
                  >
                    {integration}
                  </li>
                ))}
              </ul>
              <p className="mt-4 max-w-[32rem] text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
                Aufgeführt sind ausschließlich Anbindungen, die im Produkt umgesetzt sind. Weitere
                Schnittstellen klären wir vor einem Pilot statt sie hier zu behaupten.
              </p>
            </div>
          ) : null}
        </div>
      </Section>

      {/* 9 — governance */}
      <Section tone="inverse" labelledBy={`${product.slug}-governance`}>
        <div className="grid grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-16">
          <SectionHeader
            id={`${product.slug}-governance`}
            eyebrow="Governance"
            title="Grenzen und Nachweise"
            lead="Was das Produkt sicherstellt — und was es ausdrücklich nicht entscheidet."
          />
          <ul className="flex flex-col gap-4">
            {product.governance.map((item) => (
              <li key={item} className="flex items-start gap-3 border-t border-[var(--sbs-border-inverse)] pt-4">
                <span aria-hidden="true" className="mt-[0.55rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent-on-inverse)]" />
                <span className="text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-inverse-secondary)]">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      {/* Solutions this product appears in */}
      {linkedSolutions.length ? (
        <Section tone="page" rhythm="tight" labelledBy={`${product.slug}-loesungen`}>
          <h2 id={`${product.slug}-loesungen`} className="sbs-h3 mb-5">
            {product.shortName} in Lösungen
          </h2>
          <ul className="flex flex-wrap gap-3">
            {linkedSolutions.map((solution) => (
              <li key={solution.slug}>
                <Link
                  href={linkFor(currentPath, solution.href)}
                  className="inline-flex min-h-11 items-center gap-2 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] px-4 text-[0.875rem] font-[540] text-[var(--sbs-text-primary)] transition-colors duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)]"
                >
                  {solution.title}
                  <span aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      {/* Cross-sell with a reason, not a random product wall (§95) */}
      {related.length ? (
        <Section tone="sunken" labelledBy={`${product.slug}-weiter`}>
          <SectionHeader
            id={`${product.slug}-weiter`}
            eyebrow="Weiterführend"
            title={`Was gut mit ${product.shortName} zusammenarbeitet`}
            lead={product.relatedReason}
            className="mb-8"
          />
          <div className={`grid grid-cols-[minmax(0,1fr)] gap-4 ${related.length > 1 ? "md:grid-cols-2" : "max-w-[34rem]"}`}>
            {related.map((entry) => (
              <Link
                key={entry.slug}
                href={linkFor(currentPath, entry.href)}
                className="group flex flex-col gap-2 rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] p-6 transition-[border-color,box-shadow] duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-border-strong)] hover:shadow-[var(--sbs-shadow-md)]"
              >
                <h3 className="sbs-h4 flex items-center gap-2">
                  {entry.name}
                  <span
                    aria-hidden="true"
                    className="text-[var(--sbs-accent)] opacity-0 transition-opacity duration-[var(--sbs-motion-fast)] group-hover:opacity-100"
                  >
                    →
                  </span>
                </h3>
                <p className="text-[0.875rem] leading-[1.55] text-[var(--sbs-text-secondary)]">{entry.tagline}</p>
              </Link>
            ))}
          </div>
        </Section>
      ) : null}

      {/* 10 — CTA */}
      <Section tone="page" rhythm="tight">
        <div className="flex flex-col gap-5 rounded-[var(--sbs-radius-xl)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
          <div className="max-w-[34rem]">
            <Eyebrow>Nächster Schritt</Eyebrow>
            <h2 className="sbs-h3 mt-2">{product.name} im eigenen Kontext prüfen</h2>
            <p className="mt-2 text-[0.9375rem] leading-[1.6] text-[var(--sbs-text-secondary)]">
              Wir zeigen den Ablauf an Ihren Unterlagen — oder an synthetischen Beispieldaten, wenn
              das für einen ersten Termin passender ist.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button href={linkFor(currentPath, product.primaryAction.href)} external={product.primaryAction.external} size="lg">
              {product.primaryAction.label}
            </Button>
            {product.secondaryAction ? (
              <Button href={linkFor(currentPath, product.secondaryAction.href)} variant="secondary" size="lg">
                {product.secondaryAction.label}
              </Button>
            ) : null}
          </div>
        </div>
      </Section>
    </>
  );
}
