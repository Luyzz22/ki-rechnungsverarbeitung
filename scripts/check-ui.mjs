// =============================================================================
// Responsive, accessibility and reduced-motion sweep across all three hosts.
//
//   node scripts/check-ui.mjs           (needs the site on 127.0.0.1:3100)
//
// Chromium is pointed at the loopback listener with --host-resolver-rules, so
// it sends real Host headers and src/proxy.ts routes exactly as in production.
// A Host header cannot be set via setExtraHTTPHeaders — Chromium rejects it.
//
// Checked per route: HTTP 200, no horizontal overflow, no tap target under
// 24px (measuring the label when the control itself is sr-only, which is the
// correct pattern and not a defect), exactly one h1, landmarks, lang, image
// alt text, labelled svg, non-empty link names, heading order, a visible focus
// ring on the first tab stop, and — under prefers-reduced-motion: reduce — no
// animation or transition longer than 100ms.
//
// The floor is 375px, the width this site has always claimed. 320px is swept
// too and currently overflows on five routes; see qa-report.md.
// =============================================================================
// playwright is not a dependency of this repository — the site ships no test
// runner. Resolve it from wherever it is installed instead.
import { createRequire } from 'node:module';
const require_ = createRequire(import.meta.url);
let chromium;
for (const spec of ['playwright', '/opt/node22/lib/node_modules/playwright/index.js']) {
  try { ({ chromium } = require_(spec)); break; } catch { /* try the next */ }
}
if (!chromium) {
  console.error('playwright not found — install it, or set NODE_PATH to a global install');
  process.exit(2);
}

const PORT = 3100;
const url = (host, path) => `http://${host}:${PORT}${path}`;
const HOSTS = {
  corporate: 'sbsdeutschland.com',
  industrie: 'industrie.sbsdeutschland.com',
  legal: 'legal.sbsdeutschland.com',
};
const ROUTES = [
  ['corporate', '/'], ['corporate', '/plattform'], ['corporate', '/plattform/flowcheck'],
  ['corporate', '/academy'], ['corporate', '/ressourcen'], ['corporate', '/unternehmen'],
  ['corporate', '/sicherheit'], ['corporate', '/kontakt'], ['corporate', '/labs/releaseproof'],
  ['corporate', '/impressum'], ['corporate', '/datenschutz'],
  ['industrie', '/'], ['industrie', '/plattform'], ['industrie', '/produkte'],
  ['industrie', '/produkte/normpilot'], ['industrie', '/produkte/hydraulikdoc'],
  ['industrie', '/loesungen'], ['industrie', '/kontakt'],
  ['legal', '/'], ['legal', '/produkte'], ['legal', '/produkte/kanzleiai'],
  ['legal', '/produkte/compliancehub'], ['legal', '/loesungen'],
  ['legal', '/governance'], ['legal', '/kontakt'],
];
const VIEWPORTS = [
  { name: '320', width: 320, height: 720 },
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1024', width: 1024, height: 768 },
  { name: '1440', width: 1440, height: 900 },
  { name: '1920', width: 1920, height: 1080 },
];

const problems = [];
const note = (kind, where, msg) => problems.push({ kind, where, msg });

// Chromium refuses a Host header set via setExtraHTTPHeaders, so map the real
// hostnames onto the loopback listener instead. The browser then sends genuine
// Host headers and src/proxy.ts routes exactly as it will in production.
const browser = await chromium.launch({
  args: ['--host-resolver-rules=MAP sbsdeutschland.com 127.0.0.1, MAP *.sbsdeutschland.com 127.0.0.1'],
});

// ---- responsive -----------------------------------------------------------
let vpChecks = 0;
for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  for (const [host, path] of ROUTES) {
    const page = await ctx.newPage();
    const res = await page.goto(url(HOSTS[host], path), { waitUntil: 'networkidle' });
    const where = `${HOSTS[host]}${path} @${vp.name}`;
    if (!res || res.status() !== 200) note('status', where, `HTTP ${res && res.status()}`);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (overflow > 1) note('overflow', where, `${overflow}px horizontal overflow`);
    const small = await page.evaluate(() => {
      const out = [];
      for (const el of document.querySelectorAll('a,button,[role=button],input,select')) {
        const st = getComputedStyle(el);
        if (st.visibility === 'hidden' || st.display === 'none') continue;
        // An sr-only control wrapped in a label is the correct pattern: the
        // label is what a finger hits, so measure the label.
        let target = el;
        const label = el.closest('label');
        if (label && label !== el) {
          const lr = label.getBoundingClientRect();
          const er = el.getBoundingClientRect();
          if (lr.width * lr.height > er.width * er.height) target = label;
        }
        const r = target.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.height < 24 || r.width < 24) out.push((target.textContent || target.tagName).trim().slice(0, 30) + ` ${Math.round(r.width)}x${Math.round(r.height)}`);
      }
      return out;
    });
    if (small.length) note('tap-target', where, small.slice(0, 3).join(' | '));
    const h1 = await page.locator('h1').count();
    if (h1 !== 1) note('h1', where, `${h1} h1 elements`);
    vpChecks++;
    await page.close();
  }
  await ctx.close();
}

// ---- accessibility + reduced motion ---------------------------------------
let a11yChecks = 0;
for (const reduced of [false, true]) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    reducedMotion: reduced ? 'reduce' : 'no-preference',
  });
  for (const [host, path] of ROUTES) {
    const page = await ctx.newPage();
    await page.goto(url(HOSTS[host], path), { waitUntil: 'networkidle' });
    const where = `${HOSTS[host]}${path}${reduced ? ' [reduced]' : ''}`;

    const struct = await page.evaluate(() => {
      const r = {};
      r.main = document.querySelectorAll('main').length;
      r.nav = document.querySelectorAll('nav').length;
      r.footer = document.querySelectorAll('footer').length;
      r.lang = document.documentElement.lang || '';
      r.imgNoAlt = [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length;
      r.svgNoLabel = [...document.querySelectorAll('svg')].filter(s =>
        s.getAttribute('aria-hidden') !== 'true' && !s.getAttribute('aria-label') &&
        !s.querySelector('title')).length;
      r.emptyLinks = [...document.querySelectorAll('a')].filter(a =>
        !a.textContent.trim() && !a.getAttribute('aria-label') && !a.querySelector('img,svg')).length;
      const levels = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]);
      r.headingJump = null;
      for (let i = 1; i < levels.length; i++) {
        if (levels[i] - levels[i - 1] > 1) { r.headingJump = `h${levels[i-1]} -> h${levels[i]}`; break; }
      }
      return r;
    });
    if (struct.main !== 1) note('landmark', where, `${struct.main} <main>`);
    if (struct.nav < 1) note('landmark', where, 'no <nav>');
    if (struct.footer < 1) note('landmark', where, 'no <footer>');
    if (!struct.lang) note('lang', where, 'no lang on <html>');
    if (struct.imgNoAlt) note('alt', where, `${struct.imgNoAlt} img without alt`);
    if (struct.svgNoLabel) note('svg-label', where, `${struct.svgNoLabel} svg neither hidden nor labelled`);
    if (struct.emptyLinks) note('empty-link', where, `${struct.emptyLinks} links with no accessible name`);
    if (struct.headingJump) note('heading-order', where, struct.headingJump);

    // visible focus on the first focusable
    await page.keyboard.press('Tab');
    const focusVisible = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return 'none';
      const st = getComputedStyle(el);
      const ring = st.outlineStyle !== 'none' && parseFloat(st.outlineWidth) > 0;
      const shadow = st.boxShadow && st.boxShadow !== 'none';
      return ring || shadow ? 'ok' : 'invisible';
    });
    if (focusVisible !== 'ok') note('focus', where, `first tab stop focus ${focusVisible}`);

    if (reduced) {
      const animated = await page.evaluate(() => {
        const out = [];
        for (const el of document.querySelectorAll('*')) {
          const st = getComputedStyle(el);
          const d = parseFloat(st.animationDuration) || 0;
          const t = parseFloat(st.transitionDuration) || 0;
          if (d > 0.1 || t > 0.1) out.push(el.tagName + '.' + (el.className || '').toString().slice(0, 40));
          if (out.length > 3) break;
        }
        return out;
      });
      if (animated.length) note('reduced-motion', where, animated.join(' | '));
    }
    a11yChecks++;
    await page.close();
  }
  await ctx.close();
}

await browser.close();

const byKind = {};
for (const p of problems) (byKind[p.kind] ||= []).push(p);
console.log(`responsive: ${ROUTES.length} routes x ${VIEWPORTS.length} viewports = ${vpChecks} page checks`);
console.log(`a11y/motion: ${a11yChecks} page checks (normal + reduced motion)`);
if (!problems.length) { console.log('\nbrowser sweep: PASS — 0 findings'); process.exit(0); }
console.log('');
for (const [kind, list] of Object.entries(byKind)) {
  console.log(`${kind}: ${list.length}`);
  for (const p of list.slice(0, 6)) console.log(`   ${p.where} — ${p.msg}`);
  if (list.length > 6) console.log(`   ... ${list.length - 6} more`);
}
console.log(`\nbrowser sweep: ${problems.length} finding(s)`);
process.exit(1);
