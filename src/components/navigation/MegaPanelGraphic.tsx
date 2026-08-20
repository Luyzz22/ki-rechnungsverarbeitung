/**
 * Small live graphics for the mega-menu featured column (§45). Each one is a
 * miniature of the product mechanism it links to, not a decorative shape.
 * Purpose: explain. All motion is CSS and is disabled under reduced motion.
 */
export function MegaPanelGraphic({ variant }: { variant: "network" | "evidence" | "contract" }) {
  if (variant === "evidence") return <EvidenceMini />;
  if (variant === "contract") return <ContractMini />;
  return <NetworkMini />;
}

const flowClass =
  "[stroke-dasharray:3_5] [animation:sbs-dash-flow_3.5s_linear_infinite] motion-reduce:[animation:none]";

function EvidenceMini() {
  return (
    <svg viewBox="0 0 200 92" className="w-full" role="img" aria-label="Anforderung, Nachweis, Status">
      {[0, 1, 2].map((row) => (
        <g key={row} transform={`translate(0 ${row * 30})`}>
          <rect x="2" y="6" width="62" height="18" rx="4" fill="var(--sbs-bg-emphasis)" />
          <rect x="10" y="13" width="42" height="4" rx="2" fill="var(--sbs-text-muted)" opacity="0.55" />
          <line x1="66" y1="15" x2="112" y2="15" stroke="var(--sbs-signal-line)" strokeWidth="1.4" className={flowClass} />
          <rect x="114" y="6" width="48" height="18" rx="4" fill="var(--sbs-accent-soft)" />
          <rect x="121" y="13" width="30" height="4" rx="2" fill="var(--sbs-accent)" opacity="0.7" />
          {row === 2 ? (
            <g>
              <rect x="170" y="8" width="26" height="14" rx="3" fill="var(--sbs-warn)" opacity="0.14" />
              <text x="183" y="18.5" textAnchor="middle" fontSize="7.5" fill="var(--sbs-warn)" fontFamily="var(--sbs-font-mono)">
                GAP
              </text>
            </g>
          ) : (
            <g>
              <rect x="170" y="8" width="26" height="14" rx="3" fill="var(--sbs-ok)" opacity="0.13" />
              <path d="M178 15.2l3 3 6-6" stroke="var(--sbs-ok)" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </g>
          )}
        </g>
      ))}
    </svg>
  );
}

function ContractMini() {
  return (
    <svg viewBox="0 0 200 92" className="w-full" role="img" aria-label="Vertrag, Extraktion, Prüfung">
      <rect x="2" y="8" width="48" height="76" rx="5" fill="var(--sbs-bg-emphasis)" />
      {[16, 26, 36, 46, 56, 66].map((y, i) => (
        <rect key={y} x="10" y={y} width={i % 3 === 0 ? 32 : 24} height="3.5" rx="1.75" fill="var(--sbs-text-muted)" opacity="0.4" />
      ))}
      <rect x="9" y="34" width="34" height="7" rx="2" fill="var(--sbs-accent)" opacity="0.2" />
      <line x1="52" y1="46" x2="76" y2="46" stroke="var(--sbs-signal-line)" strokeWidth="1.4" className={flowClass} />
      {[0, 1, 2, 3].map((i) => (
        <g key={i} transform={`translate(78 ${14 + i * 18})`}>
          <rect width="58" height="13" rx="3" fill="var(--sbs-accent-soft)" />
          <rect x="6" y="5" width={34 - i * 4} height="3.5" rx="1.75" fill="var(--sbs-accent)" opacity="0.65" />
        </g>
      ))}
      <line x1="138" y1="46" x2="158" y2="46" stroke="var(--sbs-signal-line)" strokeWidth="1.4" className={flowClass} />
      <rect x="160" y="30" width="36" height="32" rx="4" fill="var(--sbs-bg-page)" stroke="var(--sbs-border)" />
      <path d="M170 46.5l4 4 8-9" stroke="var(--sbs-ok)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <text x="178" y="60" textAnchor="middle" fontSize="6.5" fill="var(--sbs-text-muted)" fontFamily="var(--sbs-font-mono)">
        REVIEW
      </text>
    </svg>
  );
}

function NetworkMini() {
  return (
    <svg viewBox="0 0 200 92" className="w-full" role="img" aria-label="Industrie und Legal am gemeinsamen Kern">
      <path d="M14 22h44c14 0 16 24 32 24" stroke="var(--sbs-signal-line)" strokeWidth="1.5" fill="none" className={flowClass} />
      <path d="M14 70h44c14 0 16-24 32-24" stroke="var(--sbs-signal-line)" strokeWidth="1.5" fill="none" className={flowClass} />
      <path d="M96 46h44" stroke="var(--sbs-signal-line)" strokeWidth="1.5" fill="none" className={flowClass} />
      <circle cx="14" cy="22" r="4" fill="var(--sbs-accent)" />
      <circle cx="14" cy="70" r="4" fill="var(--sbs-accent)" />
      <rect x="90" y="36" width="52" height="20" rx="5" fill="var(--sbs-navy)" />
      <text x="116" y="49.5" textAnchor="middle" fontSize="7" fill="#fff" fontFamily="var(--sbs-font-mono)">
        SBS CORE
      </text>
      <rect x="150" y="30" width="46" height="14" rx="3" fill="var(--sbs-accent-soft)" />
      <rect x="150" y="48" width="46" height="14" rx="3" fill="var(--sbs-accent-soft)" />
      <text x="24" y="25.5" fontSize="7" fill="var(--sbs-text-muted)" fontFamily="var(--sbs-font-mono)">
        INDUSTRIE
      </text>
      <text x="24" y="73.5" fontSize="7" fill="var(--sbs-text-muted)" fontFamily="var(--sbs-font-mono)">
        LEGAL
      </text>
    </svg>
  );
}
