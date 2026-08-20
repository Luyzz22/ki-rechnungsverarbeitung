/**
 * The SBS Signal Rail as a section divider: a thin line carrying labelled
 * nodes. Purpose: orient — it marks the seam between two stages of the page
 * narrative without adding a decorative band.
 */
export function RailDivider({ labels, tone = "light" }: { labels: string[]; tone?: "light" | "inverse" }) {
  const line = tone === "inverse" ? "var(--sbs-signal-line-inverse)" : "var(--sbs-signal-line)";
  const text = tone === "inverse" ? "var(--sbs-text-inverse-muted)" : "var(--sbs-text-muted)";
  const node = tone === "inverse" ? "var(--sbs-accent-on-inverse)" : "var(--sbs-accent)";

  return (
    <div className="sbs-scroll-x -mx-[var(--sbs-gutter)] px-[var(--sbs-gutter)]">
      <ol
        className="flex min-w-max items-center gap-0"
        style={{ color: text }}
        aria-label="Ablauf"
      >
        {labels.map((label, index) => (
          <li key={label} className="flex items-center gap-0">
            {index > 0 ? (
              <span aria-hidden="true" className="block h-px w-10 sm:w-16" style={{ background: line }} />
            ) : null}
            <span className="flex items-center gap-2 whitespace-nowrap px-1">
              <span
                aria-hidden="true"
                className="block h-[7px] w-[7px] rounded-full"
                style={{ background: node }}
              />
              <span className="sbs-mono text-[0.75rem]">{label}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
