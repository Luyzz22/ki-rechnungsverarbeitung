import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * NormPilot: the Evidence Matrix (§23).
 *
 * Each row is a requirement with its evidence source, the page it was found on,
 * and its status. The last row is deliberately a gap with the corrective action
 * it produced — that is the part of the product that a generic "compliance
 * dashboard" illustration would leave out.
 */
const rows = [
  { requirement: "Dokumentenlenkung", evidence: "QM-Handbuch.pdf", locus: "S. 12", status: "ok" as const },
  { requirement: "Interne Auditplanung", evidence: "Auditplan_2026.xlsx", locus: "Blatt 1", status: "ok" as const },
  { requirement: "Lieferantenbewertung", evidence: "Bewertung_Q2.xlsx", locus: "Blatt 3", status: "ok" as const },
  { requirement: "Schulungsnachweis Prüfmittel", evidence: null, locus: null, status: "gap" as const },
];

export function EvidenceMatrixGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  return (
    <GraphicFrame
      label="NormPilot · Evidence Matrix"
      tone={tone}
      caption="Ohne Fundstelle entsteht kein bestätigter Nachweis. Fehlende Nachweise werden als Gap Finding mit Schweregrad geführt und in eine Maßnahme überführt."
    >
      <div className="sbs-scroll-x">
        <table className="w-full min-w-[30rem] border-collapse text-left">
          <caption className="sr-only">
            Beispielhafte Evidence Matrix mit Anforderung, Nachweis, Fundstelle und Status
          </caption>
          <thead>
            <tr className="border-b border-[var(--sbs-border)]">
              {["Anforderung", "Nachweis", "Fundstelle", "Status"].map((head) => (
                <th
                  key={head}
                  scope="col"
                  className="sbs-mono pb-2 pr-4 text-[0.6875rem] font-[500] uppercase tracking-[0.1em] text-[var(--sbs-text-muted)]"
                >
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr
                key={row.requirement}
                className="border-b border-[var(--sbs-border-subtle)] last:border-0"
                style={{
                  animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${index * 80}ms both`,
                }}
              >
                <th scope="row" className="py-2.5 pr-4 text-[0.8125rem] font-[560] text-[var(--sbs-text-primary)]">
                  {row.requirement}
                </th>
                <td className="py-2.5 pr-4">
                  {row.evidence ? (
                    <span className="sbs-mono text-[0.75rem] text-[var(--sbs-accent-strong)]">{row.evidence}</span>
                  ) : (
                    <span className="sbs-mono text-[0.75rem] text-[var(--sbs-text-muted)]">— kein Nachweis</span>
                  )}
                </td>
                <td className="py-2.5 pr-4">
                  <span className="sbs-mono text-[0.75rem] text-[var(--sbs-text-muted)]">{row.locus ?? "—"}</span>
                </td>
                <td className="py-2.5">
                  {row.status === "ok" ? (
                    <StatusPill kind="ok">belegt</StatusPill>
                  ) : (
                    <StatusPill kind="gap">GAP · hoch</StatusPill>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-3.5">
        <p className="sbs-eyebrow mb-1.5 text-[var(--sbs-text-muted)]">Erzeugte Maßnahme</p>
        <p className="text-[0.8125rem] leading-[1.5] text-[var(--sbs-text-secondary)]">
          Schulungsnachweise für Prüfmittelverantwortliche erfassen und dem Requirement zuordnen.
        </p>
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <StatusPill kind="neutral">Zuständig: QMB</StatusPill>
          <StatusPill kind="neutral">Status: offen</StatusPill>
          <StatusPill kind="neutral">Review erforderlich</StatusPill>
        </div>
      </div>
      <DemoNote>Synthetische Beispieldaten. Keine Norm-Volltexte, keine Kundendaten.</DemoNote>
    </GraphicFrame>
  );
}
