/**
 * Enterprise architecture flow (§18.6): input → processing → AI → human control
 * → output → audit. Rendered as an ordered list with a rail, so the sequence is
 * available to a screen reader in the same order it is drawn.
 *
 * Motion purpose: explain. The dashed connectors move in the reading direction;
 * under reduced motion they are static lines and nothing is lost.
 */

const stages = [
  {
    id: "input",
    label: "Input",
    detail: "PDF, XLSX, E-Mail, Vertrag, Prüfbericht, Rechnung",
    note: "validiert",
  },
  {
    id: "processing",
    label: "Verarbeitung",
    detail: "Sanitisierung, Layout- und Tabellenextraktion, Strukturierung",
    note: "deterministisch",
  },
  {
    id: "ai",
    label: "Modell",
    detail: "Schemavalidierte Ausgabe, versionierte Prompts, protokollierte Anbieterwahl",
    note: "begrenzt",
  },
  {
    id: "human",
    label: "Menschliche Prüfung",
    detail: "Annehmen, anpassen, ablehnen oder eskalieren — vor jeder Freigabe",
    note: "verbindlich",
    human: true,
  },
  {
    id: "output",
    label: "Ausgabe",
    detail: "Evidence Pack, DATEV-Export, Bericht, Maßnahme, Antwort mit Fundstelle",
    note: "rollenbegrenzt",
  },
  {
    id: "audit",
    label: "Audit Trail",
    detail: "Quelle, Modell, Prompt-Version, Zeitpunkt, Prüfer und Entscheidung",
    note: "persistent",
  },
];

export function ArchitectureFlow({ tone = "inverse" }: { tone?: "light" | "inverse" }) {
  const inverse = tone === "inverse";
  const line = inverse ? "var(--sbs-signal-line-inverse)" : "var(--sbs-signal-line)";
  const dot = inverse ? "var(--sbs-accent-on-inverse)" : "var(--sbs-accent)";

  return (
    <ol className="grid grid-cols-[minmax(0,1fr)] gap-x-4 gap-y-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {stages.map((stage, index) => (
        <li key={stage.id} className="relative flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: stage.human ? "var(--sbs-gold)" : dot }}
            />
            <span
              aria-hidden="true"
              className="h-px flex-1"
              style={{ background: line }}
            />
            <span className="sbs-mono text-[0.625rem] uppercase tracking-[0.1em]" style={{ color: inverse ? "var(--sbs-text-inverse-muted)" : "var(--sbs-text-muted)" }}>
              {String(index + 1).padStart(2, "0")}
            </span>
          </div>
          <h3 className={`text-[0.9375rem] font-[620] ${inverse ? "text-[var(--sbs-text-inverse)]" : "text-[var(--sbs-text-primary)]"}`}>
            {stage.label}
          </h3>
          <p className={`text-[0.8125rem] leading-[1.5] ${inverse ? "text-[var(--sbs-text-inverse-secondary)]" : "text-[var(--sbs-text-secondary)]"}`}>
            {stage.detail}
          </p>
          <p
            className="sbs-mono text-[0.6875rem]"
            style={{ color: stage.human ? "var(--sbs-gold)" : inverse ? "var(--sbs-text-inverse-muted)" : "var(--sbs-text-muted)" }}
          >
            {stage.note}
          </p>
        </li>
      ))}
    </ol>
  );
}
