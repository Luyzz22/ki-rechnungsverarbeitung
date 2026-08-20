import type { ReactNode } from "react";

type Tone = "page" | "sunken" | "inverse" | "emphasis";
type Rhythm = "tight" | "normal" | "wide";

const tones: Record<Tone, string> = {
  page: "bg-[var(--sbs-bg-page)]",
  sunken: "bg-[var(--sbs-bg-sunken)]",
  emphasis: "bg-[var(--sbs-bg-emphasis)]",
  inverse: "sbs-inverse",
};

const rhythms: Record<Rhythm, string> = {
  tight: "sbs-section sbs-section--tight",
  normal: "sbs-section",
  wide: "sbs-section sbs-section--wide",
};

export function Section({
  children,
  tone = "page",
  rhythm = "normal",
  id,
  className = "",
  as: Tag = "section",
  labelledBy,
}: {
  children: ReactNode;
  tone?: Tone;
  rhythm?: Rhythm;
  id?: string;
  className?: string;
  as?: "section" | "div";
  labelledBy?: string;
}) {
  return (
    <Tag
      id={id}
      aria-labelledby={labelledBy}
      data-surface={tone === "inverse" ? "inverse" : undefined}
      className={`${tones[tone]} ${rhythms[rhythm]} ${className}`}
    >
      <div className="sbs-container">{children}</div>
    </Tag>
  );
}

export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`sbs-eyebrow ${className}`}>{children}</p>;
}

export function SectionHeader({
  eyebrow,
  title,
  lead,
  id,
  align = "start",
  className = "",
  as = "h2",
}: {
  eyebrow?: string;
  title: ReactNode;
  lead?: ReactNode;
  id?: string;
  align?: "start" | "center";
  className?: string;
  /** Set to "h1" when this header is the page title. */
  as?: "h1" | "h2";
}) {
  const alignment = align === "center" ? "text-center items-center mx-auto" : "";
  const Heading = as;
  return (
    <header className={`flex max-w-[46rem] flex-col gap-4 ${alignment} ${className}`}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Heading id={id} className={as === "h1" ? "sbs-display--sm" : "sbs-h2"}>
        {title}
      </Heading>
      {lead ? <p className="sbs-lead">{lead}</p> : null}
    </header>
  );
}
