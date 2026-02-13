/**
 * SBS Deutschland – Header & Footer Injection
 * =============================================
 * Für statische Landing-/Legal-Seiten (Impressum, Datenschutz, AGB etc.)
 * Injiziert konsistenten Header + Footer in #header-slot / #footer-slot
 * 
 * Version: 1.0 · 12. Februar 2026
 * Pfad: /static/js/header-footer.js
 */

(function () {
  'use strict';

  /* ── aktuelle Seite erkennen ── */
  var path = window.location.pathname;
  function isActive(keyword) {
    return path.indexOf(keyword) !== -1;
  }

  /* ── CSS (Scoped, kollidiert nicht mit Seiten-CSS) ── */
  var css = document.createElement('style');
  css.textContent = [
    /* ---------- HEADER ---------- */
    '.shf-header{background:linear-gradient(135deg,#003856 0%,#00507a 100%);position:fixed;top:0;left:0;right:0;z-index:9999;box-shadow:0 2px 20px rgba(0,0,0,.15)}',
    '.shf-header-inner{max-width:1400px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:68px}',
    '.shf-logo{display:flex;align-items:center;gap:12px;text-decoration:none}',
    '.shf-logo-icon{width:40px;height:40px;background:linear-gradient(135deg,#FFB900 0%,#ff9500 100%);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;color:#003856;font-weight:800}',
    '.shf-logo-text{display:flex;flex-direction:column}',
    '.shf-logo-text strong{color:#fff;font-size:1.05rem;font-weight:700;line-height:1.2}',
    '.shf-logo-text span{color:rgba(255,255,255,.65);font-size:.72rem;letter-spacing:.02em}',
    '.shf-nav{display:flex;align-items:center;gap:4px}',
    '.shf-nav a{color:rgba(255,255,255,.88);text-decoration:none;padding:8px 14px;border-radius:8px;font-size:.88rem;font-weight:500;transition:all .2s}',
    '.shf-nav a:hover{background:rgba(255,255,255,.1);color:#fff}',
    '.shf-nav a.active{background:rgba(255,255,255,.15);color:#fff}',
    '.shf-nav .shf-cta{background:linear-gradient(135deg,#FFB900,#ff9500);color:#003856;font-weight:600;padding:8px 18px;border-radius:8px}',
    '.shf-nav .shf-cta:hover{filter:brightness(1.08);background:linear-gradient(135deg,#FFB900,#ff9500)}',
    /* burger */
    '.shf-burger{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px}',
    '.shf-burger span{display:block;width:22px;height:2px;background:#fff;border-radius:2px;transition:all .3s}',
    /* ---------- FOOTER ---------- */
    '.shf-footer{background:linear-gradient(135deg,#003856 0%,#001f33 100%);color:rgba(255,255,255,.7);padding:48px 24px 32px}',
    '.shf-footer-inner{max-width:1400px;margin:0 auto}',
    '.shf-footer-grid{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:40px;margin-bottom:40px}',
    '.shf-footer-brand{display:flex;align-items:center;gap:10px;margin-bottom:12px}',
    '.shf-footer-brand strong{color:#fff;font-size:1rem}',
    '.shf-footer-brand span{font-size:.75rem;color:rgba(255,255,255,.5)}',
    '.shf-footer-tagline{font-size:.85rem;line-height:1.6;margin-bottom:10px;color:rgba(255,255,255,.6)}',
    '.shf-footer-loc{font-size:.82rem;color:rgba(255,255,255,.5)}',
    '.shf-footer h4{color:#FFB900;font-size:.82rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px}',
    '.shf-footer ul{list-style:none;padding:0;margin:0}',
    '.shf-footer li{margin-bottom:8px}',
    '.shf-footer a{color:rgba(255,255,255,.7);text-decoration:none;font-size:.85rem;transition:color .2s}',
    '.shf-footer a:hover{color:#FFB900}',
    '.shf-footer-bottom{border-top:1px solid rgba(255,255,255,.1);padding-top:24px;display:flex;justify-content:space-between;align-items:center;font-size:.8rem;color:rgba(255,255,255,.4);flex-wrap:wrap;gap:12px}',
    /* ---------- RESPONSIVE ---------- */
    '@media(max-width:860px){',
      '.shf-nav{display:none;position:fixed;top:68px;left:0;right:0;background:#003856;padding:20px;flex-direction:column;gap:0;box-shadow:0 8px 30px rgba(0,0,0,.3)}',
      '.shf-nav.open{display:flex}',
      '.shf-nav a{padding:14px 20px;border-radius:0;border-bottom:1px solid rgba(255,255,255,.08);width:100%}',
      '.shf-nav .shf-cta{margin-top:8px;text-align:center;border-radius:8px}',
      '.shf-burger{display:flex}',
      '.shf-footer-grid{grid-template-columns:1fr 1fr;gap:28px}',
    '}',
    '@media(max-width:480px){.shf-footer-grid{grid-template-columns:1fr}}'
  ].join('\n');
  document.head.appendChild(css);

  /* ── HEADER HTML ── */
  var headerSlot = document.getElementById('header-slot');
  if (headerSlot) {
    headerSlot.innerHTML = [
      '<header class="shf-header">',
      '  <div class="shf-header-inner">',
      '    <a href="/sbshomepage/" class="shf-logo">',
      '      <div class="shf-logo-icon">S</div>',
      '      <div class="shf-logo-text">',
      '        <strong>SBS Deutschland</strong>',
      '        <span>KI-Lösungen · Weinheim</span>',
      '      </div>',
      '    </a>',
      '    <button class="shf-burger" id="shfBurger" aria-label="Menü öffnen">',
      '      <span></span><span></span><span></span>',
      '    </button>',
      '    <nav class="shf-nav" id="shfNav">',
      '      <a href="/sbshomepage/"' + (path === '/sbshomepage/' || path === '/sbshomepage' ? ' class="active"' : '') + '>Startseite</a>',
      '      <a href="/static/landing/"' + (isActive('/landing/index') || (isActive('/landing/') && !isActive('impressum') && !isActive('datenschutz') && !isActive('agb') && !isActive('preise')) ? ' class="active"' : '') + '>KI-Rechnungsverarbeitung</a>',
      '      <a href="/sbshomepage/unternehmen.html"' + (isActive('unternehmen') ? ' class="active"' : '') + '>Über uns</a>',
      '      <a href="/sbshomepage/kontakt.html"' + (isActive('kontakt') ? ' class="active"' : '') + '>Kontakt</a>',
      '      <a href="https://app.sbsdeutschland.com/" class="shf-cta">Upload / Demo</a>',
      '    </nav>',
      '  </div>',
      '</header>'
    ].join('\n');

    /* Burger Toggle */
    var burger = document.getElementById('shfBurger');
    var nav = document.getElementById('shfNav');
    if (burger && nav) {
      burger.addEventListener('click', function () {
        nav.classList.toggle('open');
      });
    }
  }

  /* ── FOOTER HTML ── */
  var footerSlot = document.getElementById('footer-slot');
  if (footerSlot) {
    footerSlot.innerHTML = [
      '<footer class="shf-footer">',
      '  <div class="shf-footer-inner">',
      '    <div class="shf-footer-grid">',
      '      <div>',
      '        <div class="shf-footer-brand">',
      '          <div class="shf-logo-icon" style="width:34px;height:34px;font-size:1.1rem">S</div>',
      '          <div>',
      '            <strong style="color:#fff;display:block">SBS Deutschland</strong>',
      '            <span style="font-size:.72rem;color:rgba(255,255,255,.5)">Smart Business Service</span>',
      '          </div>',
      '        </div>',
      '        <p class="shf-footer-tagline">Enterprise KI-Lösungen für den deutschen Mittelstand.<br>Entwickelt und betrieben in Deutschland.</p>',
      '        <div class="shf-footer-loc">📍 In der Dell 19, 69469 Weinheim</div>',
      '      </div>',
      '      <div>',
      '        <h4>Produkt</h4>',
      '        <ul>',
      '          <li><a href="/static/landing/">KI-Rechnungsverarbeitung</a></li>',
      '          <li><a href="https://contract.sbsdeutschland.com/">KI-Vertragsanalyse</a></li>',
      '          <li><a href="/static/preise/">Preise &amp; Pakete</a></li>',
      '          <li><a href="/copilot">Finance Copilot</a></li>',
      '        </ul>',
      '      </div>',
      '      <div>',
      '        <h4>Unternehmen</h4>',
      '        <ul>',
      '          <li><a href="/sbshomepage/unternehmen.html">Über uns</a></li>',
      '          <li><a href="/sbshomepage/kontakt.html">Kontakt</a></li>',
      '          <li><a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a></li>',
      '          <li><a href="tel:+4962012446">+49 6201 24469</a></li>',
      '        </ul>',
      '      </div>',
      '      <div>',
      '        <h4>Rechtliches</h4>',
      '        <ul>',
      '          <li><a href="/static/landing/impressum.html"' + (isActive('impressum') ? ' style="color:#FFB900"' : '') + '>Impressum</a></li>',
      '          <li><a href="/static/landing/datenschutz.html"' + (isActive('datenschutz') ? ' style="color:#FFB900"' : '') + '>Datenschutz</a></li>',
      '          <li><a href="/static/landing/agb.html"' + (isActive('agb') ? ' style="color:#FFB900"' : '') + '>AGB</a></li>',
      '        </ul>',
      '      </div>',
      '    </div>',
      '    <div class="shf-footer-bottom">',
      '      <div>© ' + new Date().getFullYear() + ' SBS Deutschland GmbH &amp; Co. KG · Alle Rechte vorbehalten.</div>',
      '      <div>Made with ❤️ in Weinheim</div>',
      '    </div>',
      '  </div>',
      '</footer>'
    ].join('\n');
  }

})();
