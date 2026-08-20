/**
 * Crawls the running site and reports dead internal links plus the reachability
 * of every external product URL referenced by the content registry.
 *
 *   npm run build && npm start &
 *   npm run check:links -- http://127.0.0.1:3100
 */
const base = (process.argv[2] || process.env.SBS_BASE_URL || "http://127.0.0.1:3100").replace(/\/$/, "");
const EXTERNAL_TIMEOUT_MS = 12000;

/**
 * The three public sites are one build behind three hostnames. Cross-site links
 * are rendered as absolute production URLs, so before deployment they resolve
 * to hosts that do not exist yet. Map them back onto the local build and check
 * them there; only genuinely third-party URLs are fetched over the network.
 */
const SITE_ORIGINS = {
  "https://sbsdeutschland.com": "",
  "https://www.sbsdeutschland.com": "",
  "https://industrie.sbsdeutschland.com": "/industrie",
  "https://legal.sbsdeutschland.com": "/legal",
};

function toLocalPath(url) {
  for (const [origin, prefix] of Object.entries(SITE_ORIGINS)) {
    if (url === origin) return prefix || "/";
    if (url.startsWith(origin + "/")) {
      const rest = url.slice(origin.length);
      return (prefix + rest) || "/";
    }
  }
  return null;
}

/**
 * The build serves three hostnames, so the crawl runs three times with the
 * matching Host header. A link that only works on its own host is correct;
 * a link that works on none of them is dead.
 */
const HOSTS = [
  { host: "sbsdeutschland.com", prefix: "", start: "/" },
  { host: "industrie.sbsdeutschland.com", prefix: "/industrie", start: "/" },
  { host: "legal.sbsdeutschland.com", prefix: "/legal", start: "/" },
];

const internalFailures = [];
const externalTargets = new Map();
let crawledPages = 0;

function normalise(href) {
  if (!href) return null;
  if (href.startsWith("#")) return null;
  if (/^(mailto:|tel:|javascript:)/i.test(href)) return null;
  if (/^https?:\/\//i.test(href)) return href;
  return href.split("#")[0] || "/";
}

async function crawl(site) {
  const seen = new Set();
  const queue = [site.start];
  while (queue.length) {
    const path = queue.shift();
    if (seen.has(path)) continue;
    seen.add(path);
    crawledPages += 1;

    let response;
    try {
      // Node's fetch drops a manually set Host header, so the crawl addresses
      // each site through its internal prefix instead of its public hostname.
      response = await fetch(base + site.prefix + (path === "/" ? "" : path) || base + "/", {
        redirect: "manual",
      });
    } catch (error) {
      internalFailures.push({ host: site.host, path, status: "FETCH_ERROR", detail: String(error) });
      continue;
    }
    if (response.status >= 400) {
      internalFailures.push({ host: site.host, path, status: response.status });
      continue;
    }
    if (response.status >= 300) continue;

    const html = await response.text();
    for (const match of html.matchAll(/href="([^"]+)"/g)) {
      const href = normalise(match[1]);
      if (!href) continue;
      if (/^https?:\/\//i.test(href)) {
        // Cross-site links are checked while crawling their own host.
        if (toLocalPath(href.split("#")[0]) !== null) continue;
        if (!externalTargets.has(href)) externalTargets.set(href, `${site.host}${path}`);
        continue;
      }
      if (href.startsWith("/_next") || href.endsWith(".svg") || href.endsWith(".xml") || href.endsWith(".txt")) continue;
      // A relative href on a division host is already in that site's public
      // space, so it maps onto the internal prefix.
      if (!seen.has(href)) queue.push(href);
    }
  }
}

async function checkExternal() {
  const results = [];
  for (const [url, from] of externalTargets) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), EXTERNAL_TIMEOUT_MS);
    try {
      let response = await fetch(url, { method: "HEAD", redirect: "follow", signal: controller.signal });
      if (response.status === 405 || response.status === 403) {
        response = await fetch(url, { method: "GET", redirect: "follow", signal: controller.signal });
      }
      results.push({ url, from, status: response.status });
    } catch (error) {
      results.push({ url, from, status: "UNREACHABLE", detail: String(error).slice(0, 120) });
    } finally {
      clearTimeout(timer);
    }
  }
  return results;
}

for (const site of HOSTS) await crawl(site);
const external = await checkExternal();

console.log(`internal pages crawled: ${crawledPages} (across ${HOSTS.length} hostnames)`);
console.log(`internal failures:      ${internalFailures.length}`);
for (const failure of internalFailures) console.log(`  ✗ ${failure.host}${failure.path} → ${failure.status}`);

console.log(`external links checked: ${external.length}`);
const externalBad = external.filter((entry) => entry.status === "UNREACHABLE" || Number(entry.status) >= 400);
for (const entry of external) {
  const ok = entry.status !== "UNREACHABLE" && Number(entry.status) < 400;
  console.log(`  ${ok ? "✓" : "✗"} ${entry.status} ${entry.url}${ok ? "" : `  (verlinkt von ${entry.from})`}`);
}

if (internalFailures.length) {
  console.error("\nDead internal links found.");
  process.exit(1);
}
if (externalBad.length) {
  console.error("\nExternal targets unreachable from this network — verify manually before release.");
  process.exit(2);
}
console.log("\nLink check passed.");
