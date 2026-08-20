import type { LegalBlock } from "@/content/legal/types";
import { Section } from "@/components/ui/Section";

/**
 * Renders a reviewed legal document in the site design.
 *
 * The wording comes verbatim from the maintained source document (see
 * scripts/extract-legal.mjs). Nothing here reformulates, shortens or
 * supplements it.
 */
export function LegalDocument({ blocks, notice }: { blocks: LegalBlock[]; notice?: string }) {
  const first = blocks[0];
  const title = first && first.type === "title" ? first.text : "";
  const body = first && first.type === "title" ? blocks.slice(1) : blocks;

  return (
    <>
      <section className="sbs-inverse" data-surface="inverse">
        <div className="sbs-container sbs-section">
          <h1 className="sbs-display--sm max-w-[38rem] text-[var(--sbs-text-inverse)]">{title}</h1>
        </div>
      </section>

      <Section tone="page">
        <div className="max-w-[var(--sbs-container-prose)]">
          {notice ? (
            <p className="mb-9 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-4 text-[0.8125rem] leading-[1.6] text-[var(--sbs-text-muted)]">
              {notice}
            </p>
          ) : null}

          <div className="flex flex-col">
            {body.map((block, index) => {
              // A leading "h3" before the first real section would jump h1 → h3.
              const seenH2 = body.slice(0, index).some((entry) => entry.type === "h2");
              if (block.type === "h2" || (block.type === "h3" && !seenH2)) {
                return (
                  <h2
                    key={`${index}-${block.text}`}
                    className="sbs-h3 mt-10 border-t border-[var(--sbs-border)] pt-7 first:mt-0 first:border-0 first:pt-0"
                  >
                    {block.text}
                  </h2>
                );
              }
              if (block.type === "h3") {
                return (
                  <h3 key={`${index}-${block.text}`} className="sbs-h4 mt-7 text-[var(--sbs-text-primary)]">
                    {block.text}
                  </h3>
                );
              }
              if (block.type === "list") {
                return (
                  <ul key={`list-${index}`} className="mt-3 flex flex-col gap-2">
                    {block.items.map((item, itemIndex) => (
                      <li key={`${index}-${itemIndex}`} className="flex items-start gap-2.5">
                        <span
                          aria-hidden="true"
                          className="mt-[0.6rem] h-[5px] w-[5px] shrink-0 rounded-full bg-[var(--sbs-accent)]"
                        />
                        <span className="text-[0.9375rem] leading-[1.7] text-[var(--sbs-text-secondary)]">{item}</span>
                      </li>
                    ))}
                  </ul>
                );
              }
              return (
                <p key={`${index}-p`} className="mt-3 text-[0.9375rem] leading-[1.75] text-[var(--sbs-text-secondary)]">
                  {block.text}
                </p>
              );
            })}
          </div>
        </div>
      </Section>
    </>
  );
}
