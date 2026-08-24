// =============================================================================
// Behavioural test for the hero slider.
//
//   node scripts/check-slider.mjs        (needs the site on 127.0.0.1:3100)
//
// Covers what a static sweep cannot: that autoplay advances, that it stops for
// good once a reader takes control, that the explicit pause/resume control
// carries the right accessible name in both states (WCAG 2.2.2), that keyboard
// and inert behaviour hold, and that reduced motion means nothing rotates and
// no pause control is offered for something that is not moving.
//
// Note when reading failures: the pointer must be moved off the region before
// any timing assertion, because hovering pauses rotation on purpose.
// =============================================================================
import { createRequire } from 'node:module';

// playwright is not a dependency of this repository — the site ships no test
// runner. Resolve it from wherever it is installed.
const require_ = createRequire(import.meta.url);
let chromium;
for (const spec of ['playwright', '/opt/node22/lib/node_modules/playwright/index.js']) {
  try { ({ chromium } = require_(spec)); break; } catch { /* try the next */ }
}
if (!chromium) {
  console.error('playwright not found — install it, or set NODE_PATH to a global install');
  process.exit(2);
}

const browser = await chromium.launch();
let fail = 0;
const ok = (c, m) => { console.log(`  ${c ? 'PASS' : 'FAIL'} ${m}`); if (!c) fail++; };

// ---- normal motion --------------------------------------------------------
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
await page.goto('http://127.0.0.1:3100/', { waitUntil: 'networkidle' });
const activeLabel = () => page.locator('.sbs-hero-slider__slide[data-active="true"]').getAttribute('aria-label');

const first = await activeLabel();
ok(/1 von 3/.test(first), `starts on slide 1 (${first})`);

const initialToggleName = await page.locator('.sbs-hero-slider__toggle').getAttribute('aria-label');
ok(initialToggleName === 'Rotation pausieren',
   `initial accessible name is "Rotation pausieren" (got "${initialToggleName}")`);

// auto-advance
await page.waitForTimeout(7600);
const second = await activeLabel();
ok(second !== first, `auto-advances (${second})`);

// manual control stops the timer
await page.locator('.sbs-hero-slider__dot').first().click();
const afterClick = await activeLabel();
ok(/1 von 3/.test(afterClick), 'dot click selects slide 1');
await page.waitForTimeout(8000);
ok(await activeLabel() === afterClick, 'auto-advance stops once the reader takes over');

// keyboard
await page.locator('.sbs-hero-slider__arrow').first().focus();
await page.keyboard.press('ArrowRight');
ok(/2 von 3/.test(await activeLabel()), 'ArrowRight advances');
await page.keyboard.press('ArrowLeft');
ok(/1 von 3/.test(await activeLabel()), 'ArrowLeft goes back');

// inactive slides are not reachable by keyboard
// Focusability is the property that matters, so test that directly: try to
// focus each inactive slide's link and see whether it actually took focus.
const reachable = await page.evaluate(() => {
  const inactive = document.querySelectorAll('.sbs-hero-slider__slide[data-active="false"] a');
  for (const a of inactive) { a.focus(); if (document.activeElement === a) return true; }
  return false;
});
ok(!reachable, 'inactive slide links cannot take focus');

// exactly one h1 on the page, unchanged by the slider
ok(await page.locator('h1').count() === 1, 'page keeps exactly one h1');
ok(await page.locator('.sbs-hero-slider h2').count() === 3, 'slides use h2');

// ---- explicit pause / resume control (WCAG 2.2.2) -------------------------
const toggle = page.locator('.sbs-hero-slider__toggle');
ok(await toggle.count() === 1, 'pause control is rendered');

// The pointer must leave the region between a click and any timing assertion:
// hovering pauses rotation, which is intended behaviour, not a bug to measure.
const moveOff = () => page.mouse.move(5, 5);

// Navigation earlier in this test stopped rotation, so the control is in its
// resume state. Press it and confirm rotation genuinely comes back.
ok(await toggle.getAttribute('aria-label') === 'Rotation fortsetzen',
   'after navigating, the control offers "Rotation fortsetzen"');
await toggle.click();
ok(await toggle.getAttribute('aria-label') === 'Rotation pausieren',
   'after resuming, the control offers "Rotation pausieren"');
await moveOff();
const beforeAuto = await activeLabel();
await page.waitForTimeout(7800);
ok(await activeLabel() !== beforeAuto, 'resume restarts autoplay');

// Now pause and prove it stays paused with the pointer away.
await toggle.click();
ok(await toggle.getAttribute('aria-label') === 'Rotation fortsetzen',
   'accessible name becomes "Rotation fortsetzen" when paused');
await moveOff();
const whilePaused = await activeLabel();
await page.waitForTimeout(9000);
ok(await activeLabel() === whilePaused, 'paused rotation never restarts by itself');

// Keyboard reachable.
const focusable = await page.evaluate(() => {
  const b = document.querySelector('.sbs-hero-slider__toggle');
  b.focus();
  return document.activeElement === b;
});
ok(focusable, 'pause control is keyboard focusable');

await ctx.close();

// ---- reduced motion -------------------------------------------------------
const rctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
const rpage = await rctx.newPage();
await rpage.goto('http://127.0.0.1:3100/', { waitUntil: 'networkidle' });
const rLabel = () => rpage.locator('.sbs-hero-slider__slide[data-active="true"]').getAttribute('aria-label');
const r1 = await rLabel();
await rpage.waitForTimeout(8000);
ok(await rLabel() === r1, 'reduced motion: never auto-advances');
await rpage.locator('.sbs-hero-slider__arrow').last().click();
ok(/2 von 3/.test(await rLabel()), 'reduced motion: controls still work');
ok(await rpage.locator('.sbs-scroll-progress').count() === 0, 'reduced motion: no scroll progress bar');
ok(await rpage.locator('.sbs-hero-slider__toggle').count() === 0,
   'reduced motion: no pause control, because nothing rotates');
await rctx.close();

// ---- mobile ---------------------------------------------------------------
// The controls are the part most likely to break when the row has to wrap.
const mctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
const mpage = await mctx.newPage();
await mpage.goto('http://127.0.0.1:3100/', { waitUntil: 'networkidle' });
ok(await mpage.evaluate(() =>
     document.documentElement.scrollWidth - document.documentElement.clientWidth) <= 1,
   'mobile: no horizontal overflow at 375px');
const mToggle = mpage.locator('.sbs-hero-slider__toggle');
ok(await mToggle.getAttribute('aria-label') === 'Rotation pausieren',
   'mobile: pause control keeps its accessible name when its label is visually hidden');
const box = await mToggle.boundingBox();
ok(box !== null && box.height >= 44,
   `mobile: pause control meets the 44px tap target (${box ? Math.round(box.height) : 0}px)`);
await mctx.close();

await browser.close();
console.log(fail ? `\nslider: ${fail} failure(s)` : '\nslider: PASS');
process.exit(fail ? 1 : 0);
