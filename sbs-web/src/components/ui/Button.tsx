import Link from "next/link";
import type { ReactNode } from "react";

type Variant = "primary" | "secondary" | "quiet" | "inverse";
type Size = "md" | "lg";

type Props = {
  href: string;
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  external?: boolean;
  /** Purpose: focus — the arrow shifts to signal "this goes somewhere". */
  arrow?: boolean;
  className?: string;
  "aria-label"?: string;
};

const base =
  "group inline-flex items-center justify-center gap-2 rounded-[var(--sbs-radius-md)] font-[560] " +
  "transition-[background-color,color,border-color,box-shadow,transform] duration-[var(--sbs-motion-fast)] " +
  "ease-[var(--sbs-ease-standard)] whitespace-nowrap";

const sizes: Record<Size, string> = {
  md: "min-h-11 px-[1.125rem] text-[0.9375rem]",
  lg: "min-h-12 px-6 text-[1rem]",
};

const variants: Record<Variant, string> = {
  primary:
    "bg-[var(--sbs-accent)] text-[var(--sbs-accent-contrast)] shadow-[var(--sbs-shadow-sm)] " +
    "hover:bg-[var(--sbs-accent-strong)] hover:shadow-[var(--sbs-shadow-md)]",
  secondary:
    "border border-[var(--sbs-border-strong)] bg-[var(--sbs-bg-elevated)] text-[var(--sbs-text-primary)] " +
    "hover:border-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)]",
  quiet:
    "px-0 text-[var(--sbs-accent)] hover:text-[var(--sbs-accent-strong)] min-h-0 py-1",
  inverse:
    "border border-[var(--sbs-border-inverse-strong)] bg-transparent text-[var(--sbs-text-inverse)] " +
    "hover:border-[var(--sbs-accent-on-inverse)] hover:text-[var(--sbs-accent-on-inverse)]",
};

export function Button({
  href,
  children,
  variant = "primary",
  size = "md",
  external,
  arrow = true,
  className = "",
  ...rest
}: Props) {
  const classes = `${base} ${sizes[size]} ${variants[variant]} ${className}`;
  const content = (
    <>
      <span>{children}</span>
      {arrow ? <Arrow /> : null}
    </>
  );

  if (external) {
    return (
      <a href={href} className={classes} target="_blank" rel="noopener noreferrer" {...rest}>
        {content}
        <span className="sr-only"> (öffnet in neuem Tab)</span>
      </a>
    );
  }

  return (
    <Link href={href} className={classes} {...rest}>
      {content}
    </Link>
  );
}

function Arrow() {
  return (
    <svg
      aria-hidden="true"
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      className="translate-x-0 transition-transform duration-[var(--sbs-motion-fast)] ease-[var(--sbs-ease-standard)] group-hover:translate-x-[3px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
    >
      <path
        d="M2.5 7h9M8 3.5 11.5 7 8 10.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
