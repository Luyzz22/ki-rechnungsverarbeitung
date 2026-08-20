import type { ReactNode } from "react";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";
import { navForSite, ctaForSite } from "@/lib/nav";
import { sites, type SiteKey } from "@/content/site";

/**
 * Shared page frame. Header height, wordmark position, grid, footer logic and
 * motion vocabulary stay identical across sites; only the accent and the
 * navigation content change (§46).
 */
export function SiteChrome({
  siteKey,
  path,
  children,
}: {
  siteKey: SiteKey;
  path: string;
  children: ReactNode;
}) {
  const site = sites[siteKey];
  const homeHref = site.basePath || "/";
  const parentLink =
    siteKey === "corporate" ? undefined : { label: "SBS Deutschland", href: "/" };

  return (
    <div data-division={site.theme} className="flex min-h-screen flex-col">
      <a className="sbs-skip-link" href="#inhalt">
        Zum Inhalt springen
      </a>
      <SiteHeader
        site={site}
        nav={navForSite(siteKey)}
        cta={ctaForSite(siteKey)}
        homeHref={homeHref}
        currentPath={path}
        parentLink={parentLink}
      />
      <main id="inhalt" className="flex-1">
        {children}
      </main>
      <SiteFooter site={site} currentPath={path} />
    </div>
  );
}
