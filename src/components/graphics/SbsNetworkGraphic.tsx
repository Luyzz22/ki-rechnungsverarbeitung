"use client";

import Link from "next/link";
import { useState } from "react";
import { linkFor } from "@/content/site";

/**
 * SBS Product Network — the corporate hero graphic (§17).
 *
 * Built from real HTML links with SVG rails in the gaps, so every node is
 * keyboard reachable and screen-reader readable. Hover and focus reveal the
 * same capability line, so the information is never hover-only (§39).
 *
 * Motion purpose: explain — the dashed rails show that both divisions run
 * through one shared processing path. Everything stops under reduced motion.
 */

type Node = {
  id: string;
  name: string;
  capability: string;
  href: string;
};

const industry: Node[] = [
  { id: "normpilot", name: "NormPilot", capability: "Evidence Matrix und Gap Findings aus Bestandsdokumenten.", href: "/industrie/produkte/normpilot" },
  { id: "hydraulikdoc", name: "HydraulikDoc", capability: "Quellengebundene Antworten aus technischer Dokumentation.", href: "/industrie/produkte/hydraulikdoc" },
  { id: "belegflow", name: "BelegFlow", capability: "Belegprüfung, Freigabe und Export im kaufmännischen Backoffice.", href: "/plattform/belegflow" },
];

const legal: Node[] = [
  { id: "kanzleiai", name: "KanzleiAI", capability: "Strukturierte Vertragsextraktion mit Risiko-Findings und Human Review.", href: "/legal/produkte/kanzleiai" },
  { id: "compliancehub", name: "ComplianceHub", capability: "KI-System-Inventar, Risikoklassifikation und Nachweise.", href: "/legal/produkte/compliancehub" },
];

const coreLayers = ["Dokumente", "Extraktion", "Modelle", "Human Review", "Audit Trail"];

export function SbsNetworkGraphic({ currentPath }: { currentPath: string }) {
  const [active, setActive] = useState<string | null>(null);
  const capability = active
    ? [...industry, ...legal].find((node) => node.id === active)?.capability
    : null;

  return (
    <div>
      <p className="sr-only">
        Übersicht des SBS-Produktnetzes: die Produkte der Bereiche Industrie und Legal nutzen einen
        gemeinsamen Verarbeitungsweg aus Dokumenten, Extraktion, Modellen, menschlicher Prüfung und
        Audit Trail.
      </p>

      {/* Division labels get their own row so both sit on one baseline even
          though the two columns hold a different number of products. */}
      <div className="mb-3 hidden items-baseline justify-between md:flex">
        <DivisionLabel heading="Industrie" href={linkFor(currentPath, "/industrie")} />
        <DivisionLabel heading="Legal" href={linkFor(currentPath, "/legal")} align="end" />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] items-center gap-x-0 gap-y-6 md:grid-cols-[minmax(0,1fr)_2.75rem_auto_2.75rem_minmax(0,1fr)]">
        <NodeColumn heading="Industrie" href="/industrie" nodes={industry} active={active} setActive={setActive} align="start" currentPath={currentPath} />

        <Rail count={3} direction="right" />

        <div className="mx-auto w-full max-w-[15.5rem] rounded-[var(--sbs-radius-lg)] border border-[var(--sbs-border-inverse-strong)] bg-[var(--sbs-bg-inverse-elevated)] p-5 shadow-[var(--sbs-shadow-inverse)]">
          <p className="sbs-mono whitespace-nowrap text-[0.625rem] uppercase tracking-[0.11em] text-[var(--sbs-accent-on-inverse)]">
            SBS Enterprise Core
          </p>
          <ul className="mt-3.5 flex flex-col gap-2.5">
            {coreLayers.map((layer, index) => (
              <li key={layer} className="flex items-center gap-2.5">
                <span
                  aria-hidden="true"
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: index === 3 ? "var(--sbs-gold)" : "var(--sbs-accent-on-inverse)" }}
                />
                <span
                  className={`text-[0.8125rem] ${
                    index === 3 ? "text-[var(--sbs-text-inverse)]" : "text-[var(--sbs-text-inverse-secondary)]"
                  }`}
                >
                  {layer}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <Rail count={2} direction="left" />

        <NodeColumn heading="Legal" href="/legal" nodes={legal} active={active} setActive={setActive} align="end" currentPath={currentPath} />
      </div>

      <p
        aria-live="polite"
        className="mt-6 min-h-[3.25rem] rounded-[var(--sbs-radius-md)] border border-[var(--sbs-border-inverse)] px-4 py-3 text-[0.8125rem] leading-[1.5] text-[var(--sbs-text-inverse-secondary)]"
      >
        {capability ?? "Ein Verarbeitungsweg, zwei Geschäftsbereiche — wählen Sie ein Produkt für die Details."}
      </p>
    </div>
  );
}

function NodeColumn({
  heading,
  href,
  nodes,
  active,
  setActive,
  align,
  currentPath,
}: {
  heading: string;
  href: string;
  nodes: Node[];
  active: string | null;
  setActive: (id: string | null) => void;
  align: "start" | "end";
  currentPath: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      {/* On mobile the label sits with its column; on desktop the shared
          label row above takes over. */}
      <Link
        href={linkFor(currentPath, href)}
        className="sbs-mono inline-flex min-h-9 items-center gap-1.5 self-start text-[0.6875rem] uppercase tracking-[0.13em] text-[var(--sbs-accent-on-inverse)] transition-opacity hover:opacity-75 md:hidden"
      >
        {heading}
        <span aria-hidden="true">→</span>
      </Link>
      <ul className="flex flex-col gap-2.5">
        {nodes.map((node) => (
          <li key={node.id}>
            <Link
              href={linkFor(currentPath, node.href)}
              onMouseEnter={() => setActive(node.id)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(node.id)}
              onBlur={() => setActive(null)}
              className={`flex min-h-12 items-center gap-2.5 rounded-[var(--sbs-radius-md)] border px-3.5 py-3 transition-[border-color,background-color] duration-[var(--sbs-motion-fast)] ${
                align === "end" ? "md:flex-row-reverse md:text-right" : ""
              } ${
                active === node.id
                  ? "border-[var(--sbs-accent-on-inverse)] bg-[var(--sbs-bg-inverse-elevated)]"
                  : "border-[var(--sbs-border-inverse)] bg-[color-mix(in_srgb,var(--sbs-bg-inverse-elevated)_55%,transparent)]"
              }`}
            >
              <span
                aria-hidden="true"
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: active === node.id ? "var(--sbs-gold)" : "var(--sbs-accent-on-inverse)" }}
              />
              <span className="text-[0.9375rem] font-[560] text-[var(--sbs-text-inverse)]">{node.name}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Rail segment between a product column and the core: `count` strands
 * converging on the core's vertical centre.
 */
function DivisionLabel({
  heading,
  href,
  align = "start",
}: {
  heading: string;
  href: string;
  align?: "start" | "end";
}) {
  return (
    <Link
      href={href}
      className={`sbs-mono inline-flex min-h-9 items-center gap-1.5 text-[0.6875rem] uppercase tracking-[0.13em] text-[var(--sbs-accent-on-inverse)] transition-opacity hover:opacity-75 ${
        align === "end" ? "flex-row-reverse" : ""
      }`}
    >
      {heading}
      <span aria-hidden="true">{align === "end" ? "←" : "→"}</span>
    </Link>
  );
}

function Rail({ count, direction }: { count: number; direction: "right" | "left" }) {
  const height = 172;
  const spread = count === 3 ? [30, 86, 142] : [58, 114];
  return (
    <svg
      viewBox={`0 0 44 ${height}`}
      className="hidden h-[172px] w-11 md:block"
      aria-hidden="true"
      preserveAspectRatio="none"
    >
      {spread.map((y) => (
        <path
          key={y}
          d={
            direction === "right"
              ? `M0 ${y} C 22 ${y}, 22 86, 44 86`
              : `M44 ${y} C 22 ${y}, 22 86, 0 86`
          }
          fill="none"
          stroke="var(--sbs-signal-line-inverse)"
          strokeWidth="1.3"
          strokeDasharray="3 6"
          vectorEffect="non-scaling-stroke"
          className="[animation:sbs-dash-flow_4.5s_linear_infinite] motion-reduce:[animation:none]"
        />
      ))}
    </svg>
  );
}
