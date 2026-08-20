import Link from "next/link";
import { linkFor } from "@/content/site";

/**
 * SBS Industrie hero (§22): document types converge on one processing layer and
 * fan out into the three places the result is used. Motion purpose: explain —
 * the connectors flow toward the layer, then out of it.
 */
const inputs = [
  { label: "QM-Handbuch.pdf", kind: "PDF" },
  { label: "Auditplan.xlsx", kind: "XLSX" },
  { label: "Prüfbericht", kind: "PDF" },
  { label: "Wartungshandbuch", kind: "PDF" },
  { label: "Servicebeleg", kind: "SCAN" },
];

const outputs = [
  { label: "Evidence", product: "NormPilot", href: "/industrie/produkte/normpilot" },
  { label: "Technische Antwort", product: "HydraulikDoc", href: "/industrie/produkte/hydraulikdoc" },
  { label: "Backoffice", product: "BelegFlow", href: "/plattform/belegflow" },
];

export function IndustryHeroGraphic({ currentPath }: { currentPath: string }) {
  return (
    <div className="flex flex-col gap-4">
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {inputs.map((input, index) => (
          <li
            key={input.label}
            className="flex flex-col gap-1.5 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-inverse)] bg-[color-mix(in_srgb,var(--sbs-bg-inverse-elevated)_60%,transparent)] px-3 py-2.5"
            style={{ animation: `sbs-fade-up var(--sbs-motion-slow) var(--sbs-ease-standard) ${index * 60}ms both` }}
          >
            <span className="sbs-mono text-[0.625rem] uppercase tracking-[0.1em] text-[var(--sbs-accent-on-inverse)]">
              {input.kind}
            </span>
            <span className="text-[0.75rem] leading-[1.35] text-[var(--sbs-text-inverse-secondary)]">
              {input.label}
            </span>
          </li>
        ))}
      </ul>

      <FanIn />

      <div className="rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-inverse-strong)] bg-[var(--sbs-bg-inverse-elevated)] px-4 py-3.5">
        <p className="sbs-mono text-[0.6875rem] uppercase tracking-[0.12em] text-[var(--sbs-accent-on-inverse)]">
          Verarbeitungsschicht
        </p>
        <ol className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5">
          {["Validierung", "Layout-Extraktion", "Strukturierung", "Modell", "Human Review"].map((step, index) => (
            <li key={step} className="flex items-center gap-2">
              {index > 0 ? (
                <span aria-hidden="true" className="text-[var(--sbs-text-inverse-muted)]">
                  ›
                </span>
              ) : null}
              <span
                className={`sbs-mono text-[0.75rem] ${
                  index === 4 ? "text-[var(--sbs-gold)]" : "text-[var(--sbs-text-inverse-secondary)]"
                }`}
              >
                {step}
              </span>
            </li>
          ))}
        </ol>
      </div>

      <FanOut />

      <ul className="grid grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-3">
        {outputs.map((output) => (
          <li key={output.product}>
            <Link
              href={linkFor(currentPath, output.href)}
              className="group flex min-h-11 flex-col justify-center gap-0.5 rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-inverse)] bg-[color-mix(in_srgb,var(--sbs-bg-inverse-elevated)_60%,transparent)] px-3 py-2.5 transition-colors duration-[var(--sbs-motion-fast)] hover:border-[var(--sbs-accent-on-inverse)]"
            >
              <span className="sbs-mono text-[0.625rem] uppercase tracking-[0.1em] text-[var(--sbs-text-inverse-muted)]">
                {output.label}
              </span>
              <span className="flex items-center gap-1.5 text-[0.875rem] font-[560] text-[var(--sbs-text-inverse)]">
                {output.product}
                <span
                  aria-hidden="true"
                  className="text-[var(--sbs-accent-on-inverse)] transition-transform duration-[var(--sbs-motion-fast)] group-hover:translate-x-0.5 motion-reduce:transition-none"
                >
                  →
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FanIn() {
  return (
    <svg viewBox="0 0 400 26" className="h-9 w-full" aria-hidden="true" preserveAspectRatio="none">
      {[40, 120, 200, 280, 360].map((x) => (
        <path
          key={x}
          d={`M${x} 0 C ${x} 14, 200 10, 200 26`}
          fill="none"
          stroke="var(--sbs-signal-line-inverse)"
          strokeWidth="1.4"
          strokeDasharray="3 5"
          vectorEffect="non-scaling-stroke"
          className="[animation:sbs-dash-flow_3.2s_linear_infinite] motion-reduce:[animation:none]"
        />
      ))}
    </svg>
  );
}

function FanOut() {
  return (
    <svg viewBox="0 0 400 26" className="h-9 w-full" aria-hidden="true" preserveAspectRatio="none">
      {[70, 200, 330].map((x) => (
        <path
          key={x}
          d={`M200 0 C 200 14, ${x} 12, ${x} 26`}
          fill="none"
          stroke="var(--sbs-signal-line-inverse)"
          strokeWidth="1.4"
          strokeDasharray="3 5"
          vectorEffect="non-scaling-stroke"
          className="[animation:sbs-dash-flow_3.2s_linear_infinite] motion-reduce:[animation:none]"
        />
      ))}
    </svg>
  );
}
