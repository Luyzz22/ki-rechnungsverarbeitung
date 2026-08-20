import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Host-based routing for the three public sites (§14).
 *
 * One build, one deployment, three hostnames. Internally every page keeps a
 * stable path (`/industrie/produkte/normpilot`); publicly a division page lives
 * without that prefix (`industrie.sbsdeutschland.com/produkte/normpilot`).
 *
 * Each page is therefore reachable at exactly one public URL:
 *  - on a division host the clean path is rewritten to the internal one, and
 *    the internal form permanently redirects to the clean one;
 *  - on the corporate host the internal form permanently redirects to the
 *    division host, so the corporate origin never serves division content.
 *
 * Unknown hosts (localhost, preview deployments, health checks) fall through
 * untouched, which keeps the whole ecosystem testable at a single origin.
 */

const DIVISION_HOSTS: Record<string, { prefix: "/industrie" | "/legal" }> = {
  "industrie.sbsdeutschland.com": { prefix: "/industrie" },
  "industry.sbsdeutschland.com": { prefix: "/industrie" },
  "legal.sbsdeutschland.com": { prefix: "/legal" },
};

const CORPORATE_HOSTS = new Set(["sbsdeutschland.com", "www.sbsdeutschland.com"]);

const DIVISION_ORIGINS: Record<"/industrie" | "/legal", string> = {
  "/industrie": "https://industrie.sbsdeutschland.com",
  "/legal": "https://legal.sbsdeutschland.com",
};

export default function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
  const { pathname, search } = request.nextUrl;

  const division = DIVISION_HOSTS[host];
  if (division) {
    const { prefix } = division;

    // The internal prefix is an implementation detail on a division host.
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      const url = request.nextUrl.clone();
      url.pathname = pathname.slice(prefix.length) || "/";
      return NextResponse.redirect(url, 308);
    }

    const url = request.nextUrl.clone();
    url.pathname = pathname === "/" ? prefix : `${prefix}${pathname}`;
    url.search = search;
    return NextResponse.rewrite(url);
  }

  if (CORPORATE_HOSTS.has(host)) {
    for (const prefix of ["/industrie", "/legal"] as const) {
      if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
        const target = `${DIVISION_ORIGINS[prefix]}${pathname.slice(prefix.length) || "/"}${search}`;
        return NextResponse.redirect(target, 308);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\.(?:svg|png|jpg|jpeg|webp|avif|ico|txt|xml|webmanifest)$).*)",
  ],
};
