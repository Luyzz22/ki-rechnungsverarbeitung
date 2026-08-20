import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * ComplianceHub: risk classification and policy evaluation (§31).
 *
 * The left column is the Art. 6 decision path, the right is what falls out of
 * it: a violation with the rule that produced it and the owner it is assigned
 * to. Not a generic compliance checklist.
 */
const decision = [
  { label: "Verbotene Praktik?", answer: "nein", terminal: false },
  { label: "Annex I / III einschlägig?", answer: "ja", terminal: false },
  { label: "Sicherheitsbauteil oder Hochrisiko-Anwendung?", answer: "ja", terminal: true },
];

const systems = [
  { name: "Bewerber-Vorauswahl", level: "high" as const, dpia: false },
  { name: "Chat-Assistent Support", level: "limited" as const, dpia: true },
  { name: "Prognose Ersatzteilbedarf", level: "minimal" as const, dpia: true },
];

const levelLabel = { high: "high risk", limited: "limited risk", minimal: "minimal risk" } as const;
const levelKind = { high: "risk", limited: "gap", minimal: "ok" } as const;

export function RiskGovernanceGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  return (
    <GraphicFrame
      label="ComplianceHub · Klassifikation und Policy"
      tone={tone}
      caption="Die Klassifikation folgt der Entscheidungslogik des EU AI Act. Verstöße entstehen aus benannten Regeln und tragen eine Zuständigkeit — sie sind Arbeit, nicht Statistik."
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-4">
          <p className="sbs-eyebrow mb-3 text-[var(--sbs-text-muted)]">Entscheidungspfad · Art. 6</p>
          <ol className="flex flex-col gap-2.5">
            {decision.map((step, index) => (
              <li
                key={step.label}
                className="flex items-start justify-between gap-3 rounded-[var(--sbs-radius-sm)] border border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] px-3 py-2"
                style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${index * 90}ms both` }}
              >
                <span className="text-[0.8125rem] leading-[1.4] text-[var(--sbs-text-primary)]">{step.label}</span>
                <StatusPill kind={step.answer === "ja" ? "gap" : "neutral"}>{step.answer}</StatusPill>
              </li>
            ))}
          </ol>
          <div className="mt-3 rounded-[var(--sbs-radius-sm)] border border-[color-mix(in_srgb,var(--sbs-risk)_28%,transparent)] bg-[var(--sbs-risk-soft)] px-3 py-2.5">
            <p className="sbs-mono text-[0.6875rem] uppercase tracking-[0.1em] text-[var(--sbs-risk)]">
              Ergebnis
            </p>
            <p className="mt-0.5 text-[0.9375rem] font-[620] text-[var(--sbs-text-primary)]">high risk</p>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-elevated)] p-4">
            <p className="sbs-eyebrow mb-3 text-[var(--sbs-text-muted)]">KI-System-Inventar</p>
            <ul className="flex flex-col gap-2">
              {systems.map((system) => (
                <li key={system.name} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[0.8125rem] text-[var(--sbs-text-primary)]">{system.name}</span>
                  <span className="flex items-center gap-1.5">
                    <StatusPill kind={levelKind[system.level]}>{levelLabel[system.level]}</StatusPill>
                    <StatusPill kind={system.dpia ? "ok" : "risk"}>
                      DPIA {system.dpia ? "vorhanden" : "fehlt"}
                    </StatusPill>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-[var(--sbs-radius-md)] border border-[color-mix(in_srgb,var(--sbs-risk)_28%,transparent)] bg-[var(--sbs-bg-elevated)] p-4">
            <p className="sbs-eyebrow mb-1.5 text-[var(--sbs-risk)]">Violation</p>
            <p className="text-[0.875rem] font-[580] leading-[1.4] text-[var(--sbs-text-primary)]">
              High risk requires DPIA
            </p>
            <p className="mt-1 text-[0.8125rem] leading-[1.5] text-[var(--sbs-text-secondary)]">
              System „Bewerber-Vorauswahl“ ist als high risk klassifiziert, es liegt jedoch keine
              abgeschlossene Folgenabschätzung vor.
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              <StatusPill kind="neutral">Zuständig: AI Governance</StatusPill>
              <StatusPill kind="neutral">Vier-Augen erforderlich</StatusPill>
            </div>
          </div>
        </div>
      </div>
      <DemoNote>Synthetisches Inventar. Keine realen Systeme oder Mandantendaten.</DemoNote>
    </GraphicFrame>
  );
}
