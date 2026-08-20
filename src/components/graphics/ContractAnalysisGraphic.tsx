import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * KanzleiAI: the three-panel workbench (§29) — document, structured extraction,
 * review decision. The right panel carries the part that distinguishes the
 * product: a finding is not "done" until a person has decided about it.
 */
const extraction = [
  { field: "Parteien", value: "Muster GmbH · Beispiel AG" },
  { field: "Laufzeit", value: "24 Monate ab Unterzeichnung" },
  { field: "Kündigung", value: "3 Monate zum Laufzeitende" },
  { field: "Haftung", value: "Begrenzt auf Jahresvergütung" },
  { field: "Gerichtsstand", value: "Mannheim" },
];

const findings = [
  { title: "Automatische Verlängerung ohne Hinweis", level: "risk" as const, label: "hoch", decision: "angepasst" },
  { title: "Haftungsbegrenzung unter Marktüblichkeit", level: "gap" as const, label: "mittel", decision: "angenommen" },
  { title: "Gerichtsstand abweichend vom Standard", level: "neutral" as const, label: "niedrig", decision: "offen" },
];

export function ContractAnalysisGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  return (
    <GraphicFrame
      label="KanzleiAI · Analyse-Workbench"
      tone={tone}
      caption="Extraktion und Risikobewertung sind zwei getrennte, schemavalidierte Stufen. Jedes Finding trägt seine eigene Prüfentscheidung."
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-3 lg:grid-cols-[minmax(0,0.6fr)_minmax(0,0.9fr)_minmax(0,1fr)]">
        {/* Document */}
        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-3">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Dokument</p>
          <div className="flex flex-col gap-1.5" aria-hidden="true">
            {[92, 76, 88, 60, 84, 70, 90, 52].map((w, index) => (
              <span
                key={index}
                className="block h-[5px] rounded-full"
                style={{
                  width: `${w}%`,
                  background: index === 3 ? "var(--sbs-accent)" : "var(--sbs-border-strong)",
                  opacity: index === 3 ? 1 : 0.55,
                }}
              />
            ))}
          </div>
          <p className="sbs-mono mt-3 text-[0.625rem] text-[var(--sbs-text-muted)]">
            Rahmenvertrag · 14 Seiten
          </p>
        </div>

        {/* Extraction */}
        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-elevated)] p-3">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Stufe 1 · Extraktion</p>
          <dl className="flex flex-col gap-2">
            {extraction.map((entry, index) => (
              <div
                key={entry.field}
                style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${index * 70}ms both` }}
              >
                <dt className="sbs-mono text-[0.625rem] uppercase tracking-[0.09em] text-[var(--sbs-text-muted)]">
                  {entry.field}
                </dt>
                <dd className="text-[0.8125rem] leading-[1.4] text-[var(--sbs-text-primary)]">{entry.value}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Review */}
        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-elevated)] p-3">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Stufe 2 · Findings &amp; Review</p>
          <ul className="flex flex-col gap-2.5">
            {findings.map((finding, index) => (
              <li
                key={finding.title}
                className="rounded-[var(--sbs-radius-sm)] border border-[var(--sbs-border-subtle)] p-2.5"
                style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${220 + index * 80}ms both` }}
              >
                <p className="text-[0.8125rem] leading-[1.4] font-[550] text-[var(--sbs-text-primary)]">
                  {finding.title}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <StatusPill kind={finding.level}>Risiko: {finding.label}</StatusPill>
                  <StatusPill kind={finding.decision === "offen" ? "neutral" : "ok"}>
                    {finding.decision}
                  </StatusPill>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <DemoNote>Synthetischer Beispielvertrag. Keine Mandantendaten.</DemoNote>
    </GraphicFrame>
  );
}

/**
 * The hybrid processing path (§30). This is only shown because the redaction
 * pipeline exists in the KanzleiAI repository: sanitise, OCR, detect, redact,
 * minimise, with the re-identification mapping encrypted and kept local.
 */
const hybridStages = [
  { id: "original", label: "Originaldokument", scope: "lokal", detail: "Verlässt den Server nicht" },
  { id: "sanitize", label: "Sanitisierung", scope: "lokal", detail: "Eingebettete Skripte, Dateien und Metadaten entfernen" },
  { id: "ocr", label: "OCR & Layout", scope: "lokal", detail: "Token mit Koordinaten, Coverage-Bewertung" },
  { id: "detect", label: "Erkennung", scope: "lokal", detail: "PII, Adressen, Aktenzeichen, Deny-Listen, QR-Codes" },
  { id: "redact", label: "Redaction", scope: "lokal", detail: "Pixel- und Textschwärzung, Platzhalter statt Klartext" },
  { id: "mapping", label: "Mapping", scope: "lokal", detail: "Klartext ↔ Pseudonym, verschlüsselt und mandantengetrennt" },
  { id: "minimize", label: "Minimierter Payload", scope: "grenze", detail: "Default-Deny: nur freigegebene Felder" },
  { id: "cloud", label: "Cloud-Modell", scope: "cloud", detail: "Sieht ausschließlich den minimierten Payload" },
  { id: "reassoc", label: "Rückführung", scope: "lokal", detail: "Zuordnung erfolgt wieder lokal" },
  { id: "review", label: "Human Review", scope: "lokal", detail: "Entscheidung durch berechtigte Person" },
];

export function HybridProcessingGraphic() {
  return (
    <GraphicFrame
      label="KanzleiAI · Datenweg"
      caption="Fail-closed: bleibt ein Befund unsicher, blockiert das Policy Gate den Versand, statt ihn zu erlauben. Der Datenweg ist Teil des Produkts, nicht eine Zusicherung im Text."
    >
      <ol className="flex flex-col gap-0">
        {hybridStages.map((stage, index) => {
          const boundary = stage.scope === "grenze";
          const cloud = stage.scope === "cloud";
          return (
            <li key={stage.id} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3">
              <div className="flex flex-col items-center">
                <span
                  aria-hidden="true"
                  className="mt-[0.45rem] h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    background: cloud
                      ? "var(--sbs-gold)"
                      : boundary
                        ? "var(--sbs-warn)"
                        : "var(--sbs-accent)",
                  }}
                />
                {index < hybridStages.length - 1 ? (
                  <span
                    aria-hidden="true"
                    className="w-px flex-1"
                    style={{
                      background: "var(--sbs-signal-line)",
                      minHeight: "1.35rem",
                    }}
                  />
                ) : null}
              </div>
              <div className="pb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[0.875rem] font-[580] text-[var(--sbs-text-primary)]">{stage.label}</p>
                  <StatusPill kind={cloud ? "gap" : boundary ? "gap" : "neutral"}>
                    {cloud ? "Cloud" : boundary ? "Grenze" : "lokal"}
                  </StatusPill>
                </div>
                <p className="mt-0.5 text-[0.8125rem] leading-[1.5] text-[var(--sbs-text-secondary)]">
                  {stage.detail}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </GraphicFrame>
  );
}
