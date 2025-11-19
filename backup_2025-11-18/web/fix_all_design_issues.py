#!/usr/bin/env python3
"""
FINALER FIX: Einheitliches Design auf ALLEN Seiten
- Gleiche Header-Größe
- Funktionierender Dark Mode
- Einheitliche Buttons
"""

import re
from pathlib import Path

# ============================================
# EINHEITLICHES CSS (funktioniert überall)
# ============================================
UNIFIED_CSS = '''
    /* ================================================
       UNIFIED DESIGN - ALLE SEITEN GLEICH
       ================================================ */

    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-dark-soft: #0b2435;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
      --transition-fast: all 0.25s ease;
    }

    [data-theme="dark"] {
      --sbs-bg: #0f172a;
      --sbs-white: #1e293b;
      --sbs-dark: #60a5fa;
      --sbs-dark-soft: #e2e8f0;
      --sbs-text: #e2e8f0;
      --sbs-muted: #94a3b8;
    }

    body {
      background: var(--sbs-bg);
      color: var(--sbs-text);
      transition: background 0.3s ease, color 0.3s ease;
    }

    /* HEADER - EXAKT GLEICH AUF ALLEN SEITEN */
    .sbs-header {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: var(--sbs-white);
      box-shadow: 0 1px 12px rgba(15,23,42,0.06);
      transition: all 0.3s ease;
    }

    .sbs-header-inner {
      max-width: 1200px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 32px;
    }

    .sbs-logo-wrap {
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }

    .sbs-logo-img {
      height: 40px;
      width: auto;
      display: block;
      transition: height 0.3s ease;
    }

    .sbs-logo-text {
      display: flex;
      flex-direction: column;
      font-size: 12px;
      line-height: 1.25;
      color: var(--sbs-dark-soft);
    }

    .sbs-logo-text strong {
      font-size: 13px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      font-weight: 700;
    }

    /* Navigation */
    .sbs-nav {
      display: flex;
      align-items: center;
      gap: 24px;
      font-size: 14px;
    }

    .sbs-nav a {
      position: relative;
      padding-bottom: 4px;
      opacity: 0.85;
      transition: var(--transition-fast);
      text-decoration: none;
      color: var(--sbs-text);
      font-weight: 500;
    }

    .sbs-nav a:hover {
      opacity: 1;
    }

    .sbs-nav a.active::after {
      content: "";
      position: absolute;
      left: 0;
      bottom: 0;
      width: 100%;
      height: 2px;
      border-radius: 999px;
      background: var(--sbs-accent);
    }

    /* Upload/Demo Button - IMMER GLEICH */
    .sbs-nav-cta {
      padding: 9px 18px !important;
      border-radius: 999px !important;
      background: var(--sbs-accent) !important;
      color: #111827 !important;
      font-weight: 600 !important;
      box-shadow: 0 4px 12px rgba(255,180,0,0.3) !important;
      opacity: 1 !important;
    }

    .sbs-nav-cta::after {
      display: none !important;
    }

    .sbs-nav-cta:hover {
      transform: translateY(-1px) !important;
      box-shadow: 0 6px 16px rgba(255,180,0,0.4) !important;
    }

    /* Burger Menu */
    .burger-menu {
      display: none;
      flex-direction: column;
      gap: 5px;
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      z-index: 1001;
    }

    .burger-menu span {
      width: 25px;
      height: 3px;
      background: var(--sbs-dark-soft);
      border-radius: 3px;
      transition: all 0.3s ease;
    }

    .burger-menu.active span:nth-child(1) {
      transform: rotate(45deg) translate(8px, 8px);
    }

    .burger-menu.active span:nth-child(2) {
      opacity: 0;
    }

    .burger-menu.active span:nth-child(3) {
      transform: rotate(-45deg) translate(7px, -7px);
    }

    /* Dark Mode Toggle - EINHEITLICH MIT BEIDEN ICONS */
    .dark-mode-toggle {
      background: var(--sbs-white);
      border: 2px solid rgba(15,23,42,0.12);
      border-radius: 999px;
      width: 50px;
      height: 28px;
      cursor: pointer;
      position: relative;
      transition: all 0.3s ease;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 6px;
      overflow: visible;
    }

    .dark-mode-toggle:hover {
      border-color: var(--sbs-accent);
      transform: scale(1.05);
    }

    .sun-icon,
    .moon-icon {
      font-size: 14px;
      transition: all 0.3s ease;
      opacity: 1;
    }

    /* Dark Mode: Mond hell, Sonne dunkel */
    [data-theme="dark"] .sun-icon {
      opacity: 0.3;
    }

    [data-theme="dark"] .moon-icon {
      opacity: 1;
    }

    /* Light Mode: Sonne hell, Mond dunkel */
    [data-theme="light"] .sun-icon {
      opacity: 1;
    }

    [data-theme="light"] .moon-icon {
      opacity: 0.3;
    }

    /* FOOTER */
    #sbs-footer-global {
      border-top: 1px solid rgba(148,163,253,0.1);
      background: var(--sbs-white);
      padding: 16px 24px 18px;
      font-size: 12px;
      color: var(--sbs-muted);
    }

    #sbs-footer-global .footer-inner {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    #sbs-footer-global .footer-links {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
    }

    #sbs-footer-global a {
      color: var(--sbs-text);
      text-decoration: none;
      opacity: 0.8;
      transition: var(--transition-fast);
    }

    #sbs-footer-global a:hover {
      opacity: 1;
      color: var(--sbs-accent);
    }

    /* RESPONSIVE */
    @media (max-width: 768px) {
      .burger-menu {
        display: flex;
      }

      .sbs-nav {
        position: fixed;
        top: 0;
        right: -100%;
        width: 280px;
        height: 100vh;
        background: var(--sbs-white);
        flex-direction: column;
        align-items: flex-start;
        padding: 80px 24px 24px;
        gap: 20px;
        box-shadow: -4px 0 20px rgba(0,0,0,0.1);
        transition: right 0.3s ease;
        overflow-y: auto;
      }

      .sbs-nav.active {
        right: 0;
      }

      .sbs-nav a {
        width: 100%;
        padding: 12px 0;
        font-size: 16px;
      }

      .sbs-nav-cta {
        width: 100%;
        text-align: center;
        display: block !important;
      }

      .dark-mode-toggle {
        width: 100%;
      }
    }

    .mobile-overlay {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 999;
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    .mobile-overlay.active {
      display: block;
      opacity: 1;
    }
'''

# ============================================
# FUNKTIONIERENDES JAVASCRIPT
# ============================================
UNIFIED_JS = '''
  <script>
  (function() {
    'use strict';
    
    console.log('🎨 Unified Design Script loaded');
    
    // ========================================
    // DARK MODE - LADEN & SETZEN
    // ========================================
    const savedTheme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    console.log('📱 Theme loaded:', savedTheme);
    
    // ========================================
    // BURGER MENU
    // ========================================
    const burgerMenu = document.getElementById('burger-menu');
    const mainNav = document.getElementById('main-nav');
    
    if (burgerMenu && mainNav) {
      let overlay = document.querySelector('.mobile-overlay');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'mobile-overlay';
        document.body.appendChild(overlay);
      }
      
      burgerMenu.addEventListener('click', function() {
        burgerMenu.classList.toggle('active');
        mainNav.classList.toggle('active');
        overlay.classList.toggle('active');
        document.body.style.overflow = mainNav.classList.contains('active') ? 'hidden' : '';
      });
      
      overlay.addEventListener('click', function() {
        burgerMenu.classList.remove('active');
        mainNav.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      });
      
      mainNav.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function() {
          burgerMenu.classList.remove('active');
          mainNav.classList.remove('active');
          overlay.classList.remove('active');
          document.body.style.overflow = '';
        });
      });
    }
    
    // ========================================
    // ACTIVE STATES
    // ========================================
    function setActiveNavLink() {
      const currentPath = window.location.pathname;
      const navLinks = document.querySelectorAll('.sbs-nav a[data-page]');
      
      navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        
        if (currentPath === href || 
            currentPath.endsWith(href) ||
            (href.includes('/sbshomepage/') && currentPath.includes('/sbshomepage/')) ||
            (href.includes('/landing') && currentPath.includes('/landing'))) {
          link.classList.add('active');
        }
      });
    }
    
    setActiveNavLink();
    
    // ========================================
    // SCROLL ANIMATION
    // ========================================
    const header = document.getElementById('main-header');
    if (header) {
      window.addEventListener('scroll', function() {
        if (window.pageYOffset > 80) {
          header.classList.add('scrolled');
        } else {
          header.classList.remove('scrolled');
        }
      });
    }
    
    // ========================================
    // DARK MODE TOGGLE - FUNKTIONIERT!
    // ========================================
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    if (darkModeToggle) {
      console.log('🌙 Dark mode button found');
      
      darkModeToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        console.log('🔄 Switching theme from', currentTheme, 'to', newTheme);
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('sbs-theme', newTheme);
        
        // Animation
        darkModeToggle.style.transform = 'rotate(180deg)';
        setTimeout(() => {
          darkModeToggle.style.transform = '';
        }, 300);
      });
      
      console.log('✅ Dark mode ready');
    } else {
      console.warn('⚠️ Dark mode button NOT found');
    }
    
  })();
  </script>'''

def clean_old_styles_and_scripts(content):
    """Entfernt alte Header/Footer CSS und JS"""
    # Entferne alte Header CSS
    content = re.sub(r'\.sbs-header\s*\{[^}]*\}', '', content, flags=re.DOTALL)
    content = re.sub(r'\.sbs-header-inner\s*\{[^}]*\}', '', content, flags=re.DOTALL)
    content = re.sub(r'\.dark-mode-toggle\s*\{[^}]*\}', '', content, flags=re.DOTALL)
    
    # Entferne alte Scripts
    content = re.sub(r'<script>.*?burger-menu.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<script>.*?dark-mode.*?</script>', '', content, flags=re.DOTALL)
    
    return content

def update_file(filepath, header_html):
    """Update eine Datei mit unified design"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # 1. Alte Styles & Scripts entfernen
        content = clean_old_styles_and_scripts(content)
        
        # 2. Header ersetzen
        header_pattern = r'<header[^>]*>.*?</header>'
        if re.search(header_pattern, content, re.DOTALL):
            content = re.sub(header_pattern, header_html, content, flags=re.DOTALL)
        
        # 3. Footer ersetzen
        footer_pattern = r'<footer[^>]*>.*?</footer>'
        FOOTER_HTML = '''  <footer id="sbs-footer-global">
    <div class="footer-inner">
      <div>
        © SBS Deutschland GmbH &amp; Co. KG · In der Dell 19, 69469 Weinheim
      </div>
      <div class="footer-links">
        <a href="https://sbsdeutschland.com/sbshomepage/impressum.html">Impressum</a>
        <a href="https://sbsdeutschland.com/sbshomepage/datenschutz.html">Datenschutz</a>
        <a href="https://sbsdeutschland.com/sbshomepage/agb.html">AGB</a>
      </div>
    </div>
  </footer>'''
        
        if re.search(footer_pattern, content, re.DOTALL):
            content = re.sub(footer_pattern, FOOTER_HTML, content, flags=re.DOTALL)
        
        # 4. CSS hinzufügen (vor </style>)
        if '<style>' in content and UNIFIED_CSS not in content:
            content = content.replace('</style>', UNIFIED_CSS + '\n  </style>', 1)
        
        # 5. JavaScript hinzufügen (vor </body>)
        if '</body>' in content and UNIFIED_JS not in content:
            content = content.replace('</body>', UNIFIED_JS + '\n</body>', 1)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"❌ {filepath}: {e}")
        return False

def main():
    base = Path('/var/www/invoice-app/web')
    
    # Header für APP-Domain
    HEADER_APP = '''  <header class="sbs-header" id="main-header">
    <div class="sbs-header-inner">
      <a href="https://sbsdeutschland.com/sbshomepage/" class="sbs-logo-wrap">
        <img src="/static/sbs-logo-new.png" alt="SBS Deutschland Logo" class="sbs-logo-img" />
        <div class="sbs-logo-text">
          <strong>SBS Deutschland GmbH &amp; Co. KG</strong>
          <span>Smart Business Service · Weinheim</span>
        </div>
      </a>
      
      <button class="burger-menu" id="burger-menu" aria-label="Menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
      
      <nav class="sbs-nav" id="main-nav">
        <a href="https://sbsdeutschland.com/sbshomepage/" data-page="home">Startseite</a>
        <a href="https://sbsdeutschland.com/landing" data-page="landing">KI-Rechnungsverarbeitung</a>
        <a href="https://sbsdeutschland.com/sbshomepage/unternehmen.html" data-page="unternehmen">Über uns</a>
        <a href="https://sbsdeutschland.com/sbshomepage/kontakt.html" data-page="kontakt">Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta active">Upload / Demo</a>
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''
    
    # Header für MAIN-Domain
    HEADER_MAIN = '''  <header class="sbs-header" id="main-header">
    <div class="sbs-header-inner">
      <a href="/sbshomepage/" class="sbs-logo-wrap">
        <img src="/static/sbs-logo-new.png" alt="SBS Deutschland Logo" class="sbs-logo-img" />
        <div class="sbs-logo-text">
          <strong>SBS Deutschland GmbH &amp; Co. KG</strong>
          <span>Smart Business Service · Weinheim</span>
        </div>
      </a>
      
      <button class="burger-menu" id="burger-menu" aria-label="Menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
      
      <nav class="sbs-nav" id="main-nav">
        <a href="/sbshomepage/" data-page="home">Startseite</a>
        <a href="/landing" data-page="landing">KI-Rechnungsverarbeitung</a>
        <a href="/sbshomepage/unternehmen.html" data-page="unternehmen">Über uns</a>
        <a href="/sbshomepage/kontakt.html" data-page="kontakt">Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta">Upload / Demo</a>
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''
    
    app_files = [
        'templates/index.html',
        'templates/results.html',
    ]
    
    main_files = [
        'static/landing/index.html',
        'sbshomepage/index.html',
        'sbshomepage/unternehmen.html',
        'sbshomepage/kontakt.html',
        'sbshomepage/it-consulting.html',
        'sbshomepage/quality-risk-management.html',
        'sbshomepage/sap-consulting.html',
        'sbshomepage/met-pmo.html',
        'sbshomepage/impressum.html',
        'sbshomepage/datenschutz.html',
        'sbshomepage/agb.html',
        'static/landing/impressum.html',
        'static/landing/datenschutz.html',
        'static/landing/agb.html',
    ]
    
    print("=" * 70)
    print("🎨 FINALER DESIGN-FIX")
    print("=" * 70)
    print("Fixes:")
    print("  ✅ Gleiche Header-Größe überall (40px Logo)")
    print("  ✅ Dark Mode Button: Sonne + Mond überall")
    print("  ✅ Dark Mode funktioniert!")
    print("  ✅ Einheitliche Schriftgrößen")
    print("=" * 70)
    print()
    
    updated = 0
    
    print("📱 APP-Domain:")
    for file in app_files:
        path = base / file
        if path.exists():
            if update_file(path, HEADER_APP):
                print(f"  ✅ {file}")
                updated += 1
    
    print("\n🌐 MAIN-Domain:")
    for file in main_files:
        path = base / file
        if path.exists():
            if update_file(path, HEADER_MAIN):
                print(f"  ✅ {file}")
                updated += 1
    
    print()
    print("=" * 70)
    print(f"✅ {updated} DATEIEN AKTUALISIERT!")
    print("=" * 70)
    print()
    print("🧪 JETZT TESTEN:")
    print("  1. Browser KOMPLETT neu laden (Cmd+Shift+R)")
    print("  2. Verschiedene Seiten öffnen")
    print("  3. Dark Mode Button klicken (🌙☀️)")
    print("  4. Console öffnen (F12) → sollte '🎨 Unified Design Script loaded' zeigen")
    print()
    print("📊 TEST-URLS:")
    print("  • https://sbsdeutschland.com/landing")
    print("  • https://sbsdeutschland.com/sbshomepage/")
    print("  • https://sbsdeutschland.com/sbshomepage/unternehmen.html")
    print("  • https://app.sbsdeutschland.com/")
    print()

if __name__ == '__main__':
    main()
