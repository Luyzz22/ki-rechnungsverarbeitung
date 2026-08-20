import Link from "next/link";
import type { SiteConfig } from "@/content/site";

/**
 * One wordmark across all three sites. The division is a suffix, never a new
 * logo — a visitor moving from corporate to industry should read it as the
 * same company (§46).
 */
export function Wordmark({ site, homeHref }: { site: SiteConfig; homeHref: string }) {
  return (
    <Link
      href={homeHref}
      className="group flex min-h-11 items-center gap-2.5 rounded-[var(--sbs-radius-sm)] py-1"
      aria-label={site.brandSuffix ? `SBS Deutschland ${site.brandSuffix}, Startseite` : "SBS Deutschland, Startseite"}
    >
      <SignalMark />
      <span className="flex items-baseline gap-[0.4rem] leading-none">
        <span className="text-[1.0625rem] font-[660] tracking-[-0.025em] text-[var(--sbs-text-primary)]">
          SBS<span className="text-[var(--sbs-text-muted)]"> Deutschland</span>
        </span>
        {site.brandSuffix ? (
          <>
            <span aria-hidden="true" className="text-[var(--sbs-border-strong)]">
              /
            </span>
            <span className="text-[1.0625rem] font-[620] tracking-[-0.025em] text-[var(--sbs-accent)]">
              {site.brandSuffix}
            </span>
          </>
        ) : null}
      </span>
    </Link>
  );
}

/** The rail motif compressed into a mark: three inputs joining one path. */
function SignalMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true" className="shrink-0">
      <rect width="26" height="26" rx="7" fill="var(--sbs-navy)" />
      <path
        d="M6 8.5h4.2c1.6 0 2.4 1.3 3.4 2.6.9 1.2 1.7 2.4 3.3 2.4H20"
        stroke="var(--sbs-accent-on-inverse)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M6 17.5h4.2c1.6 0 2.4-1.3 3.4-2.6.9-1.2 1.7-2.4 3.3-2.4H20"
        stroke="var(--sbs-gold)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="20" cy="13" r="2" fill="var(--sbs-gold)" />
    </svg>
  );
}
