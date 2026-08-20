import { StatusPill } from "./primitives";

/**
 * SBS Legal hero (§28): a document on the left, findings appearing against it on
 * the right, and the review + audit steps that turn a finding into a decision.
 * No scales of justice, no courtrooms, no paragraph stock art.
 */
const findings = [
  { clause: "§ 4 Laufzeit", finding: "Automatische Verlängerung ohne Hinweisfrist", level: "risk" as const, label: "hoch" },
  { clause: "§ 9 Haftung", finding: "Begrenzung unterhalb der üblichen Bandbreite", level: "gap" as const, label: "mittel" },
  { clause: "§ 14 Gerichtsstand", finding: "Abweichung vom Standardgerichtsstand", level: "neutral" as const, label: "niedrig" },
];

export function LegalHeroGraphic() {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:grid-cols-[minmax(0,0.62fr)_minmax(0,1fr)]">
      <div className="rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-inverse)] bg-[color-mix(in_srgb,var(--sbs-bg-inverse-elevated)_65%,transparent)] p-4">
        <p className="sbs-mono text-[0.625rem] uppercase tracking-[0.11em] text-[var(--sbs-accent-on-inverse)]">
          Rahmenvertrag.pdf
        </p>
        <div className="mt-3 flex flex-col gap-[7px]" aria-hidden="true">
          {[94, 78, 88, 62, 90, 70, 84, 58, 92, 74, 86, 66].map((width, index) => {
            const highlighted = [3, 7, 10].includes(index);
            return (
              <span
                key={index}
                className="block h-[5px] rounded-full"
                style={{
                  width: `${width}%`,
                  background: highlighted ? "var(--sbs-accent-on-inverse)" : "var(--sbs-border-inverse-strong)",
                  opacity: highlighted ? 0.95 : 0.5,
                }}
              />
            );
          })}
        </div>
        <p className="sbs-mono mt-3 text-[0.625rem] text-[var(--sbs-text-inverse-muted)]">
          14 Seiten · lokal verarbeitet
        </p>
      </div>

      <div className="flex flex-col gap-2.5">
        <ul className="flex flex-col gap-2">
          {findings.map((entry, index) => (
            <li
              key={entry.clause}
              className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-inverse)] bg-[color-mix(in_srgb,var(--sbs-bg-inverse-elevated)_75%,transparent)] px-3.5 py-2.5"
              style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${100 + index * 110}ms both` }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="sbs-mono text-[0.6875rem] text-[var(--sbs-accent-on-inverse)]">{entry.clause}</span>
                <StatusPill kind={entry.level}>Risiko: {entry.label}</StatusPill>
              </div>
              <p className="mt-1 text-[0.8125rem] leading-[1.4] text-[var(--sbs-text-inverse-secondary)]">
                {entry.finding}
              </p>
            </li>
          ))}
        </ul>

        <div
          className="flex flex-wrap items-center gap-x-2 gap-y-1.5 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-inverse-strong)] px-3.5 py-2.5"
          style={{ animation: "sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) 440ms both" }}
        >
          {["Human Review", "Entscheidung", "Audit Trail"].map((step, index) => (
            <span key={step} className="flex items-center gap-2">
              {index > 0 ? (
                <span aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">
                  ›
                </span>
              ) : null}
              <span
                className={`sbs-mono text-[0.75rem] ${
                  index === 0 ? "text-[var(--sbs-gold)]" : "text-[var(--sbs-text-inverse-secondary)]"
                }`}
              >
                {step}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
