import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Host-based routing for the three public sites.
 *
 * One build, one deployment, three hostnames. Internally every page keeps a
 * stable path (`/industrie/produkte/normpilot`); publicly a division page lives
 * without that prefix (`industrie.sbsdeutschland.com/produkte/normpilot`).
 *
 * Each page is therefore reachable at exactly one public URL:
 *  - on a division host the clean path is rewritten to the internal one, and
 *    the internal form permanently redirects to the clean one;
 *  - on the corporate host the internal form permanently redirects to the
 *    division host, so the corporate origin never serves division content;
 *  - on any other hostname the internal prefixes return 404, so the internal
 *    URL space is never publicly reachable — for instance by addressing the
 *    server directly by IP. nginx rejects unmatched hosts at the edge as well;
 *    this is the second layer.
 *
 * Loopback hostnames are exempt so the whole ecosystem stays testable at a
 * single origin during development and in CI.
 */

const DIVISION_HOSTS: Record<string, { prefix: "/industrie" | "/legal" }> = {
  "industrie.sbsdeutschland.com": { prefix: "/industrie" },
  "industry.sbsdeutschland.com": { prefix: "/industrie" },
  "legal.sbsdeutschland.com": { prefix: "/legal" },
};

const CORPORATE_HOSTS = new Set(["sbsdeutschland.com", "www.sbsdeutschland.com"]);

/** Development and CI addressing, where path prefixes select the site. */
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", "::1", "0.0.0.0"]);

const DIVISION_ORIGINS: Record<"/industrie" | "/legal", string> = {
  "/industrie": "https://industrie.sbsdeutschland.com",
  "/legal": "https://legal.sbsdeutschland.com",
};

const PREFIXES = ["/industrie", "/legal"] as const;

function prefixOf(pathname: string): (typeof PREFIXES)[number] | null {
  for (const prefix of PREFIXES) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) return prefix;
  }
  return null;
}

export default function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
  const { pathname, search } = request.nextUrl;

  const division = DIVISION_HOSTS[host];
  if (division) {
    const { prefix } = division;

    // The internal prefix is an implementation detail on a division host.
    if (prefixOf(pathname) === prefix) {
      const url = request.nextUrl.clone();
      url.pathname = pathname.slice(prefix.length) || "/";
      return NextResponse.redirect(url, 308);
    }

    // A division host must not serve the other division's internal space.
    if (prefixOf(pathname)) {
      return new NextResponse(null, { status: 404 });
    }

    const url = request.nextUrl.clone();
    url.pathname = pathname === "/" ? prefix : `${prefix}${pathname}`;
    url.search = search;
    return NextResponse.rewrite(url);
  }

  if (CORPORATE_HOSTS.has(host)) {
    const prefix = prefixOf(pathname);
    if (prefix) {
      // Built through the URL parser rather than by concatenation, so a path
      // can never influence the origin of the redirect target.
      const target = new URL(pathname.slice(prefix.length) || "/", DIVISION_ORIGINS[prefix]);
      target.search = search;
      return NextResponse.redirect(target.toString(), 308);
    }
    return NextResponse.next();
  }

  if (LOOPBACK_HOSTS.has(host)) {
    return NextResponse.next();
  }

  // Unrecognised hostname: never expose the internal URL space.
  if (prefixOf(pathname)) {
    return new NextResponse(null, { status: 404 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\.(?:svg|png|jpg|jpeg|webp|avif|ico|txt|xml|webmanifest)$).*)",
  ],
};
