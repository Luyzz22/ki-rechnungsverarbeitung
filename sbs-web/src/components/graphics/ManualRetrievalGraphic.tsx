import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * HydraulikDoc: retrieval against a technical manual (§23).
 *
 * The point of the graphic is the rejection path: an answer that cannot be tied
 * to a page is discarded rather than shown. That is drawn explicitly, next to
 * the answer that does carry a source.
 */
export function ManualRetrievalGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  return (
    <GraphicFrame
      label="HydraulikDoc · Quellengebundene Antwort"
      tone={tone}
      caption="Ein Entwurf ohne gültige Quellenmarke wird verworfen und nicht gespeichert. Erst nach menschlicher Annahme ist ein Ergebnis exportierbar."
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)]">
        <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] p-3.5">
          <p className="sbs-eyebrow mb-2 text-[var(--sbs-text-muted)]">Indexiertes Handbuch</p>
          <div className="flex flex-col gap-1.5" aria-hidden="true">
            {[
              { w: "88%", hit: false },
              { w: "72%", hit: false },
              { w: "94%", hit: false },
              { w: "64%", hit: true },
              { w: "80%", hit: false },
              { w: "58%", hit: false },
            ].map((line, index) => (
              <div key={index} className="flex items-center gap-2">
                <span className="sbs-mono w-8 shrink-0 text-[0.625rem] text-[var(--sbs-text-muted)]">
                  {String(20 + index).padStart(2, "0")}
                </span>
                <span
                  className="h-[6px] rounded-full"
                  style={{
                    width: line.w,
                    background: line.hit ? "var(--sbs-accent)" : "var(--sbs-border)",
                  }}
                />
              </div>
            ))}
          </div>
          <p className="sbs-mono mt-3 text-[0.6875rem] text-[var(--sbs-text-muted)]">
            Layout-Extraktion · Tabellen erhalten
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <div className="rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-elevated)] p-3.5">
            <p className="sbs-eyebrow mb-1.5 text-[var(--sbs-text-muted)]">Frage</p>
            <p className="text-[0.875rem] leading-[1.5] text-[var(--sbs-text-primary)]">
              Welches Anzugsdrehmoment gilt für die Verschraubung an Baugruppe B?
            </p>
          </div>

          <div className="rounded-[var(--sbs-radius-md)] border border-[color-mix(in_srgb,var(--sbs-ok)_30%,transparent)] bg-[var(--sbs-ok-soft)] p-3.5">
            <div className="flex items-center justify-between gap-3">
              <p className="sbs-eyebrow text-[var(--sbs-ok)]">Angenommen</p>
              <StatusPill kind="ok">Quelle vorhanden</StatusPill>
            </div>
            <p className="mt-1.5 text-[1.0625rem] font-[620] text-[var(--sbs-text-primary)]">45 Nm</p>
            <p className="sbs-mono mt-1 text-[0.6875rem] text-[var(--sbs-text-secondary)]">
              [S1] Wartungshandbuch, Seite 23, Tabelle 4.2
            </p>
          </div>

          <div className="rounded-[var(--sbs-radius-md)] border border-dashed border-[var(--sbs-border-strong)] bg-[var(--sbs-bg-sunken)] p-3.5">
            <div className="flex items-center justify-between gap-3">
              <p className="sbs-eyebrow text-[var(--sbs-text-muted)]">Verworfen</p>
              <StatusPill kind="risk">keine Quellenmarke</StatusPill>
            </div>
            <p className="mt-1.5 text-[0.8125rem] leading-[1.5] text-[var(--sbs-text-muted)] line-through decoration-[var(--sbs-border-strong)]">
              „Üblicherweise liegt das Drehmoment bei etwa 40 bis 50 Nm.“
            </p>
            <p className="sbs-mono mt-1.5 text-[0.6875rem] text-[var(--sbs-text-muted)]">
              nicht persistiert · kein Export
            </p>
          </div>
        </div>
      </div>
      <DemoNote>Synthetisches Beispiel aus einem fiktiven Handbuch.</DemoNote>
    </GraphicFrame>
  );
}
