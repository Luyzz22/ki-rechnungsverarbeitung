import Link from "next/link";
import { products } from "@/content/products";
import { academyCourses } from "@/content/academy";
import { ORG_LEGAL_NAME, linkFor, type SiteConfig } from "@/content/site";

type FooterColumn = { title: string; links: { label: string; href: string; external?: boolean }[] };

/**
 * One enterprise footer for all three sites (§47). Links are grouped by
 * division so the ecosystem is navigable from every page, and every product
 * entry is derived from the registry rather than hand-listed.
 */
export function SiteFooter({ site, currentPath }: { site: SiteConfig; currentPath: string }) {
  const industry = products.filter((product) => product.division === "industry");
  const legal = products.filter((product) => product.division === "legal");

  const columns: FooterColumn[] = [
    {
      title: "Industrie",
      links: [
        { label: "SBS Industrie", href: "/industrie" },
        ...industry.map((product) => ({ label: product.name, href: product.href })),
        { label: "Lösungen", href: "/industrie/loesungen" },
        { label: "Plattform", href: "/industrie/plattform" },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "SBS Legal", href: "/legal" },
        ...legal.map((product) => ({ label: product.name, href: product.href })),
        { label: "Lösungen", href: "/legal/loesungen" },
        { label: "Governance", href: "/legal/governance" },
      ],
    },
    {
      title: "Plattform",
      links: [
        { label: "Technische Grundlage", href: "/plattform" },
        { label: "BelegFlow", href: "/plattform/belegflow" },
        { label: "Sicherheit & Datenwege", href: "/sicherheit" },
        { label: "ReleaseProof", href: "/labs/releaseproof" },
      ],
    },
    {
      title: "Academy",
      links: [
        { label: "SBS Academy", href: "/academy" },
        ...academyCourses.map((course) => ({ label: course.name, href: course.url, external: true })),
      ],
    },
    {
      title: "Unternehmen",
      links: [
        { label: "Über SBS Deutschland", href: "/unternehmen" },
        { label: "Beratung & Services", href: "/unternehmen#consulting" },
        { label: "Ressourcen", href: "/ressourcen" },
        { label: "Kontakt", href: "/kontakt" },
      ],
    },
    {
      title: "Rechtliches",
      links: [
        { label: "Impressum", href: "/impressum" },
        { label: "Datenschutz", href: "/datenschutz" },
      ],
    },
  ];

  return (
    <footer className="border-t border-[var(--sbs-border-subtle)] bg-[var(--sbs-bg-sunken)]">
      <div className="sbs-container py-12 lg:py-16">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-8 sm:grid-cols-2 lg:grid-cols-6">
          {columns.map((column) => (
            <nav key={column.title} aria-label={column.title}>
              <h2 className="sbs-eyebrow mb-3 text-[var(--sbs-text-muted)]">{column.title}</h2>
              <ul className="flex flex-col gap-0.5">
                {column.links.map((link) => (
                  <li key={`${column.title}-${link.label}`}>
                    {link.external ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex min-h-9 items-center text-[0.875rem] text-[var(--sbs-text-secondary)] transition-colors duration-[var(--sbs-motion-fast)] hover:text-[var(--sbs-accent-strong)]"
                      >
                        {link.label}
                        <span className="sr-only"> (öffnet in neuem Tab)</span>
                      </a>
                    ) : (
                      <Link
                        href={linkFor(currentPath, link.href)}
                        className="inline-flex min-h-9 items-center text-[0.875rem] text-[var(--sbs-text-secondary)] transition-colors duration-[var(--sbs-motion-fast)] hover:text-[var(--sbs-accent-strong)]"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-[var(--sbs-border)] pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[0.8125rem] text-[var(--sbs-text-muted)]">
            © {new Date().getFullYear()} {ORG_LEGAL_NAME}
          </p>
          <p className="sbs-mono text-[0.75rem] text-[var(--sbs-text-muted)]">
            {site.origin.replace("https://", "")}
          </p>
        </div>
      </div>
    </footer>
  );
}
