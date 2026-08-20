import { GraphicFrame, StatusPill, DemoNote } from "./primitives";

/**
 * FlowCheck AI+: the invoice run. The graphic shows what actually blocks an export —
 * a duplicate and an implausible total — rather than a clean happy path.
 */
const invoices = [
  { number: "RE-2026-0418", supplier: "Nordwerk GmbH", net: "2.480,00 €", state: "ready" as const, note: "SKR03 · 3400" },
  { number: "RE-2026-0419", supplier: "Hansa Technik", net: "740,50 €", state: "duplicate" as const, note: "identisch zu RE-2026-0402" },
  { number: "RE-2026-0420", supplier: "Meyer & Söhne", net: "12.900,00 €", state: "check" as const, note: "Brutto/Netto-Differenz" },
  { number: "RE-2026-0421", supplier: "Süd Logistik", net: "310,00 €", state: "ready" as const, note: "SKR03 · 4730" },
];

export function InvoiceAutomationGraphic({ tone = "light" }: { tone?: "light" | "inverse" }) {
  const exportable = invoices.filter((invoice) => invoice.state === "ready").length;
  return (
    <GraphicFrame
      label="FlowCheck AI+ · Prüflauf"
      tone={tone}
      caption="Auffällige Belege gehen in die Klärung, nicht in den Export. Erst die rollenbasierte Freigabe erzeugt einen Exportdatensatz."
    >
      <div className="sbs-scroll-x">
        <table className="w-full min-w-[32rem] border-collapse text-left">
          <caption className="sr-only">Beispielhafter Rechnungslauf mit Prüfstatus</caption>
          <thead>
            <tr className="border-b border-[var(--sbs-border)]">
              {["Beleg", "Lieferant", "Netto", "Prüfung"].map((head) => (
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
            {invoices.map((invoice, index) => (
              <tr
                key={invoice.number}
                className="border-b border-[var(--sbs-border-subtle)] last:border-0"
                style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${index * 75}ms both` }}
              >
                <th scope="row" className="sbs-mono py-2.5 pr-4 text-[0.75rem] font-[500] text-[var(--sbs-text-primary)]">
                  {invoice.number}
                </th>
                <td className="py-2.5 pr-4 text-[0.8125rem] text-[var(--sbs-text-secondary)]">{invoice.supplier}</td>
                <td className="sbs-mono py-2.5 pr-4 text-[0.75rem] text-[var(--sbs-text-primary)]">{invoice.net}</td>
                <td className="py-2.5">
                  <div className="flex flex-col items-start gap-1">
                    {invoice.state === "ready" ? (
                      <StatusPill kind="ok">freigabebereit</StatusPill>
                    ) : invoice.state === "duplicate" ? (
                      <StatusPill kind="risk">Dublette</StatusPill>
                    ) : (
                      <StatusPill kind="gap">Klärung</StatusPill>
                    )}
                    <span className="sbs-mono text-[0.625rem] text-[var(--sbs-text-muted)]">{invoice.note}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border)] bg-[var(--sbs-bg-sunken)] px-3.5 py-3">
        <p className="text-[0.8125rem] text-[var(--sbs-text-secondary)]">
          <span className="font-[620] text-[var(--sbs-text-primary)]">{exportable} von {invoices.length}</span>{" "}
          Belegen erreichen die Freigabe. Zwei bleiben in der Klärung.
        </p>
        <StatusPill kind="neutral">DATEV-Export nach Freigabe</StatusPill>
      </div>
      <DemoNote>Synthetische Belegdaten. Keine realen Lieferanten oder Beträge.</DemoNote>
    </GraphicFrame>
  );
}
