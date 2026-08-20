import Link from "next/link";
import type { Product } from "@/content/types";
import { linkFor } from "@/content/site";

/**
 * Product card. Deliberately not a generic rounded box: the pipeline strip at
 * the bottom shows the product's real stages, so two cards next to each other
 * are visibly different products rather than the same card recoloured.
 */
export function ProductCard({
  product,
  currentPath,
  tone = "light",
  headingLevel: Heading = "h3",
}: {
  product: Product;
  /** Route the card is rendered on; decides relative vs cross-site href. */
  currentPath: string;
  tone?: "light" | "inverse";
  /** Use "h2" when the cards follow the page h1 directly. */
  headingLevel?: "h2" | "h3";
}) {
  const inverse = tone === "inverse";
  return (
    <Link
      href={linkFor(currentPath, product.href)}
      className={`group flex flex-col justify-between gap-6 rounded-[var(--sbs-radius-lg)] border p-6 transition-[border-color,box-shadow,transform] duration-[var(--sbs-motion-normal)] ease-[var(--sbs-ease-standard)] motion-reduce:transition-none ${
        inverse
          ? "border-[var(--sbs-border-inverse)] bg-[var(--sbs-bg-inverse-elevated)] hover:border-[var(--sbs-accent-on-inverse)]"
          : "border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] hover:-translate-y-[2px] hover:border-[var(--sbs-border-strong)] hover:shadow-[var(--sbs-shadow-md)] motion-reduce:hover:translate-y-0"
      }`}
    >
      <div className="flex flex-col gap-2.5">
        <Heading
          className={`sbs-h4 flex items-center gap-2 ${
            inverse ? "text-[var(--sbs-text-inverse)]" : "text-[var(--sbs-text-primary)]"
          }`}
        >
          {product.name}
          <span
            aria-hidden="true"
            className="translate-x-0 text-[var(--sbs-accent)] opacity-0 transition-[transform,opacity] duration-[var(--sbs-motion-fast)] group-hover:translate-x-1 group-hover:opacity-100 motion-reduce:transition-none"
          >
            →
          </span>
        </Heading>
        <p className={`text-[0.9375rem] leading-[1.55] ${inverse ? "text-[var(--sbs-text-inverse-secondary)]" : "text-[var(--sbs-text-secondary)]"}`}>
          {product.tagline}
        </p>
      </div>

      <div>
        <p className={`sbs-eyebrow mb-2 ${inverse ? "text-[var(--sbs-text-inverse-muted)]" : "text-[var(--sbs-text-muted)]"}`}>
          Ablauf
        </p>
        <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1.5">
          {product.pipeline.map((stage, index) => (
            <li key={stage.id} className="flex items-center gap-1.5">
              {index > 0 ? (
                <span aria-hidden="true" className={inverse ? "text-[var(--sbs-text-inverse-muted)]" : "text-[var(--sbs-border-strong)]"}>
                  ·
                </span>
              ) : null}
              <span
                className={`sbs-mono text-[0.6875rem] ${
                  stage.human
                    ? "font-[500] text-[var(--sbs-gold)]"
                    : inverse
                      ? "text-[var(--sbs-text-inverse-muted)]"
                      : "text-[var(--sbs-text-muted)]"
                }`}
              >
                {stage.label}
              </span>
            </li>
          ))}
        </ol>
      </div>
    </Link>
  );
}
