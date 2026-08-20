import type { ReactNode } from "react";

/**
 * Shared frame for every product graphic (§43). It keeps the graphics visually
 * related without making them interchangeable: the frame is identical, the
 * contents are drawn from each product's own mechanism.
 */
export function GraphicFrame({
  label,
  caption,
  children,
  tone = "light",
}: {
  label: string;
  caption?: string;
  children: ReactNode;
  tone?: "light" | "inverse";
}) {
  const inverse = tone === "inverse";
  return (
    <figure
      className={`min-w-0 overflow-hidden rounded-[var(--sbs-radius-lg)] border ${
        inverse
          ? "border-[var(--sbs-border-inverse)] bg-[var(--sbs-bg-inverse-elevated)]"
          : "border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-elevated)] shadow-[var(--sbs-shadow-md)]"
      }`}
    >
      <div
        className={`flex items-center gap-2 border-b px-4 py-2.5 ${
          inverse
            ? "border-[var(--sbs-border-inverse)] bg-[var(--sbs-bg-inverse-sunken)]"
            : "border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-sunken)]"
        }`}
      >
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-[var(--sbs-accent)]" />
        <span
          className={`sbs-mono text-[0.6875rem] uppercase tracking-[0.11em] ${
            inverse ? "text-[var(--sbs-text-inverse-muted)]" : "text-[var(--sbs-text-muted)]"
          }`}
        >
          {label}
        </span>
      </div>
      <div className="p-4 sm:p-6">{children}</div>
      {caption ? (
        <figcaption
          className={`border-t px-4 py-3 text-[0.75rem] leading-[1.5] sm:px-6 ${
            inverse
              ? "border-[var(--sbs-border-inverse)] text-[var(--sbs-text-inverse-muted)]"
              : "border-[var(--sbs-border-subtle)] text-[var(--sbs-text-muted)]"
          }`}
        >
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}

/** Status pill. Colour is always paired with a word, never used alone (§63). */
export function StatusPill({ kind, children }: { kind: "ok" | "gap" | "risk" | "neutral"; children: ReactNode }) {
  const map = {
    ok: "text-[var(--sbs-ok)] bg-[var(--sbs-ok-soft)] border-[color-mix(in_srgb,var(--sbs-ok)_25%,transparent)]",
    gap: "text-[var(--sbs-warn)] bg-[var(--sbs-warn-soft)] border-[color-mix(in_srgb,var(--sbs-warn)_25%,transparent)]",
    risk: "text-[var(--sbs-risk)] bg-[var(--sbs-risk-soft)] border-[color-mix(in_srgb,var(--sbs-risk)_25%,transparent)]",
    neutral: "text-[var(--sbs-neutral)] bg-[var(--sbs-neutral-soft)] border-[var(--sbs-border)]",
  } as const;
  return (
    <span className={`sbs-mono inline-flex items-center whitespace-nowrap rounded-[var(--sbs-radius-sm)] border px-1.5 py-0.5 text-[0.6875rem] ${map[kind]}`}>
      {children}
    </span>
  );
}

/** Demo-data marker. Every synthetic screen on the site carries one (§38). */
export function DemoNote({ children }: { children: ReactNode }) {
  return (
    <p className="sbs-mono mt-3 text-[0.6875rem] leading-[1.5] text-[var(--sbs-text-muted)]">
      <span className="rounded-[var(--sbs-radius-sm)] border border-[var(--sbs-border)] px-1.5 py-0.5">
        DEMO
      </span>{" "}
      {children}
    </p>
  );
}
