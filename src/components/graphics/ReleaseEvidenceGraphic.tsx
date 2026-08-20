import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * ReleaseProof: the seven deterministic rules against a release scope.
 * Deterministic means the same input gives the same table — that is drawn as a
 * plain rule grid rather than a score gauge.
 */
const rules = [
  "Akzeptanzkriterien vorhanden",
  "Akzeptierter Workflow-Status",
  "Keine offenen Subtasks",
  "Keine blockierenden Links",
  "Korrekte Release-Version",
  "Kein Blocker-Label",
  "Freigabemarker vorhanden",
];

const issues = [
  { key: "PROJ-412", results: [true, true, true, true, true, true, true] },
  { key: "PROJ-418", results: [true, true, false, true, true, true, false] },
  { key: "PROJ-421", results: [false, true, true, true, false, true, false] },
];

export function ReleaseEvidenceGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  return (
    <GraphicFrame
      label="ReleaseProof · Evidence-Matrix"
      tone={tone}
      caption="Sieben feste Regeln, ausgewertet ohne generative KI. Der Bericht zeigt, warum ein Release rot ist — die Freigabeentscheidung bleibt im Kundenprozess."
    >
      <div className="sbs-scroll-x">
        <table className="w-full min-w-[34rem] border-collapse text-left">
          <caption className="sr-only">Beispielhafte Evidence-Matrix mit sieben Regeln je Issue</caption>
          <thead>
            <tr className="border-b border-[var(--sbs-border)]">
              <th scope="col" className="sbs-mono pb-2 pr-3 text-[0.6875rem] font-[500] uppercase tracking-[0.1em] text-[var(--sbs-text-muted)]">
                Issue
              </th>
              {rules.map((rule, index) => (
                <th key={rule} scope="col" className="pb-2 pr-2 text-center">
                  <abbr
                    title={rule}
                    className="sbs-mono text-[0.6875rem] font-[500] text-[var(--sbs-text-muted)] no-underline"
                  >
                    R{index + 1}
                  </abbr>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, rowIndex) => (
              <tr
                key={issue.key}
                className="border-b border-[var(--sbs-border-subtle)] last:border-0"
                style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${rowIndex * 85}ms both` }}
              >
                <th scope="row" className="sbs-mono py-2.5 pr-3 text-[0.75rem] font-[500] text-[var(--sbs-text-primary)]">
                  {issue.key}
                </th>
                {issue.results.map((pass, index) => (
                  <td key={index} className="py-2.5 pr-2 text-center">
                    <span className="sr-only">
                      {rules[index]}: {pass ? "erfüllt" : "nicht erfüllt"}
                    </span>
                    <RuleMark pass={pass} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusPill kind="risk">2 von 3 Issues mit offenen Regelverstößen</StatusPill>
        <StatusPill kind="neutral">Scope: JQL_SCOPE</StatusPill>
        <StatusPill kind="neutral">nur Leserechte</StatusPill>
      </div>
      <DemoNote>Synthetische Issue-Schlüssel. Keine realen Projektdaten.</DemoNote>
    </GraphicFrame>
  );
}

/** Pass/fail mark drawn as an icon rather than a dingbat glyph. */
function RuleMark({ pass }: { pass: boolean }) {
  return (
    <svg
      aria-hidden="true"
      width="13"
      height="13"
      viewBox="0 0 13 13"
      fill="none"
      className="mx-auto"
      style={{ color: pass ? "var(--sbs-ok)" : "var(--sbs-risk)" }}
    >
      {pass ? (
        <path d="M2.5 6.8 5 9.3l5.5-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <path d="M3 3l7 7M10 3l-7 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      )}
    </svg>
  );
}
