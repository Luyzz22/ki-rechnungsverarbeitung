/**
 * Content guard (§52, §51).
 *
 * Fails the build if unverifiable claims, invented proof or the generic AI-site
 * vocabulary reappear in the rendered pages. Every pattern here corresponds to
 * a claim the existing SBS site made that no source in the repositories backs.
 */
const base = (process.argv[2] || process.env.SBS_BASE_URL || "http://127.0.0.1:3100").replace(/\/$/, "");

const FORBIDDEN = [
  // Quantitative claims with no published measurement basis.
  { pattern: /\b\d{1,3}([.,]\d+)?\s*%\s*(Genauigkeit|Erkennung|Zeitersparnis|Trefferquote|Verfügbarkeit)/i, why: "Quote ohne Messgrundlage" },
  { pattern: /\b99[.,]\d\s*%/, why: "Genauigkeits-/Verfügbarkeitsquote" },
  { pattern: /\b9[0-9]\s*%\s*(der|Zeit|weniger|schneller)/i, why: "Marktanteil-/Einsparquote" },
  { pattern: /<\s*\d+\s*(Sekunden|Sekunde|s)\b/i, why: "Latenzzusage" },
  // Certifications and attestations we cannot evidence.
  { pattern: /\b(ISO\s?27001|ISO\s?9001)-(zertifiziert|zertifizierung)\b/i, why: "Zertifizierungsbehauptung" },
  { pattern: /\bSOC\s?2\b/i, why: "SOC-2-Behauptung" },
  { pattern: /\bBSI\s?C5\b/i, why: "BSI-C5-Behauptung" },
  { pattern: /\bTÜV[- ]?(zertifiziert|geprüft)\b/i, why: "Prüfsiegel" },
  // Absolute assurances.
  { pattern: /\b(100\s*%\s*sicher|absolut sicher|military[- ]grade|bank[- ]level security)\b/i, why: "Absolute Sicherheitszusage" },
  { pattern: /\b(garantiert|Garantie) (bestanden|Compliance|Konformität)/i, why: "Ergebnisgarantie" },
  { pattern: /\bDSGVO[- ]konform\b/i, why: "Konformitätszusage ohne Vertrags-/Betriebsnachweis", allowNegated: true },
  { pattern: /\bGoBD[- ]konform\b/i, why: "Konformitätszusage ohne Nachweis", allowNegated: true },
  // Marketing filler the brief rules out.
  { pattern: /\b(revolutionier|bahnbrechend|game[- ]?chang|next[- ]generation|unvergleichlich|weltweit führend|Marktführer)/i, why: "Superlativ ohne Beleg" },
  // Public status downgrades the owner explicitly ruled out for marketing.
  { pattern: /\b(Coming Soon|Demnächst verfügbar|Pre-Production|Vorschau-Version)\b/i, why: "Öffentliches Status-Downgrade" },
];

// Emoji used as interface chrome (§5). Product text may still contain none.
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;

const routes = [
  "/", "/plattform", "/plattform/belegflow", "/academy", "/labs/releaseproof",
  "/unternehmen", "/sicherheit", "/ressourcen", "/kontakt",
  "/industrie", "/industrie/produkte", "/industrie/produkte/normpilot",
  "/industrie/produkte/hydraulikdoc", "/industrie/loesungen", "/industrie/plattform", "/industrie/kontakt",
  "/legal", "/legal/produkte", "/legal/produkte/kanzleiai", "/legal/produkte/compliancehub",
  "/legal/loesungen", "/legal/governance", "/legal/kontakt",
];

function visibleText(html) {
  const body = html.match(/<body[^>]*>([\s\S]*)<\/body>/i)?.[1] ?? html;
  return body
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z]+;/gi, " ")
    .replace(/\s+/g, " ");
}

const DISCLAIMERS = /\b(keine|kein|nicht|Aussage|behaupten|behauptet|zu prüfen|abhängig|Gate|erst wenn|ohne)\b/i;

function isDisclaimed(text, index, length) {
  const window = text.slice(Math.max(0, index - 160), index + length + 160);
  return DISCLAIMERS.test(window);
}

const findings = [];
for (const route of routes) {
  const response = await fetch(base + route);
  if (!response.ok) {
    findings.push({ route, issue: `HTTP ${response.status}` });
    continue;
  }
  const text = visibleText(await response.text());
  for (const rule of FORBIDDEN) {
    const match = text.match(rule.pattern);
    if (!match) continue;
    // A term named in order to reject it is not a claim. Only skip when the
    // surrounding sentence explicitly disclaims or qualifies it.
    if (rule.allowNegated && isDisclaimed(text, match.index ?? 0, match[0].length)) continue;
    findings.push({ route, issue: rule.why, found: match[0].trim() });
  }
  const emoji = text.match(EMOJI);
  if (emoji) findings.push({ route, issue: "Emoji im Seitentext", found: emoji[0] });
}

console.log(`routes checked: ${routes.length}`);
if (!findings.length) {
  console.log("Content check passed — keine unbelegten Claims gefunden.");
  process.exit(0);
}
for (const finding of findings) {
  console.log(`  ✗ ${finding.route}: ${finding.issue}${finding.found ? ` → "${finding.found}"` : ""}`);
}
process.exit(1);
