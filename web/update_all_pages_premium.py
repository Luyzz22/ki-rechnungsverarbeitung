#!/usr/bin/env python3
"""
Premium Design-Update für alle Seiten
Features: Burger Menu, Active States, Scroll Animation, Dark Mode
"""

import os
import re
from datetime import datetime
from pathlib import Path

# ============================================
# HEADER HTML (mit Burger Menu)
# ============================================
HEADER_HTML = '''  <!-- HEADER -->
  <header class="sbs-header" id="main-header">
    <div class="sbs-header-inner">
      <a href="/sbshomepage/" class="sbs-logo-wrap">
        <img src="/static/sbs-logo-new.png" alt="SBS Deutschland Logo" class="sbs-logo-img" />
        <div class="sbs-logo-text">
          <strong>SBS Deutschland GmbH &amp; Co. KG</strong>
          <span>Smart Business Service · Weinheim</span>
        </div>
      </a>
      
      <!-- Burger Menu Button -->
      <button class="burger-menu" id="burger-menu" aria-label="Menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
      
      <!-- Navigation -->
      <nav class="sbs-nav" id="main-nav">
        <a href="/sbshomepage/" data-page="home">Startseite</a>
        <a href="/landing" data-page="landing">KI-Rechnungsverarbeitung</a>
        <a href="/sbshomepage/unternehmen.html" data-page="unternehmen">Über uns</a>
        <a href="/sbshomepage/kontakt.html" data-page="kontakt">Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta">Login / Demo</a>
        
        <!-- Dark Mode Toggle -->
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode Toggle">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''

# ============================================
# FOOTER HTML
# ============================================
FOOTER_HTML = '''  <!-- FOOTER (global) -->
  <footer id="sbs-footer-global">
    <div class="footer-inner">
      <div>
        © SBS Deutschland GmbH &amp; Co. KG · In der Dell 19, 69469 Weinheim
      </div>
      <div class="footer-links">
        <a href="/sbshomepage/impressum.html">Impressum</a>
        <a href="/sbshomepage/datenschutz.html">Datenschutz</a>
        <a href="/sbshomepage/agb.html">AGB</a>
      </div>
    </div>
  </footer>'''

# ============================================
# PREMIUM CSS (mit allen Features)
# ============================================
PREMIUM_CSS = '''
    /* ================================================
       PREMIUM HEADER/FOOTER CSS
       Features: Burger Menu, Scroll Animation, Dark Mode
       ================================================ */

    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-dark-soft: #0b2435;
      --sbs-accent: #ffb400;
      --sbs-accent-soft: rgba(255,180,0,0.14);
      --sbs-border-soft: rgba(15,23,42,0.08);
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
      --transition-fast: all 0.25s ease;
    }

    /* Dark Mode Variables */
    [data-theme="dark"] {
      --sbs-bg: #0f172a;
      --sbs-white: #1e293b;
      --sbs-dark: #60a5fa;
      --sbs-dark-soft: #e2e8f0;
      --sbs-text: #e2e8f0;
      --sbs-muted: #94a3b8;
      --sbs-border-soft: rgba(148,163,253,0.1);
    }

    body {
      background: var(--sbs-bg);
      color: var(--sbs-text);
      transition: background 0.3s ease, color 0.3s ease;
    }

    /* HEADER - Base */
    .sbs-header {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: var(--sbs-white);
      box-shadow: 0 1px 12px rgba(15,23,42,0.06);
      transition: all 0.3s ease;
    }

    /* Scroll Animation - kleinerer Header */
    .sbs-header.scrolled {
      padding: 4px 0;
      box-shadow: 0 4px 20px rgba(15,23,42,0.12);
    }

    .sbs-header.scrolled .sbs-logo-img {
      height: 38px;
    }

    .sbs-header-inner {
      max-width: 1200px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 32px;
      transition: padding 0.3s ease;
    }

    .sbs-header.scrolled .sbs-header-inner {
      padding: 8px 24px;
    }

    .sbs-logo-wrap {
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }

    .sbs-logo-img {
      height: 46px;
      width: auto;
      display: block;
      transition: height 0.3s ease;
    }

    .sbs-logo-text {
      display: flex;
      flex-direction: column;
      font-size: 13px;
      line-height: 1.25;
      color: var(--sbs-dark-soft);
    }

    .sbs-logo-text strong {
      font-size: 14px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }

    /* Navigation */
    .sbs-nav {
      display: flex;
      align-items: center;
      gap: 26px;
      font-size: 15px;
      color: var(--sbs-dark-soft);
    }

    .sbs-nav a {
      position: relative;
      padding-bottom: 4px;
      opacity: 0.85;
      transition: var(--transition-fast);
      text-decoration: none;
      color: var(--sbs-text);
    }

    .sbs-nav a:hover {
      opacity: 1;
    }

    /* Active State - automatisch gesetzt */
    .sbs-nav a.active::after,
    .sbs-nav a:hover::after {
      content: "";
      position: absolute;
      left: 0;
      bottom: 0;
      width: 100%;
      height: 2px;
      border-radius: 999px;
      background: var(--sbs-accent);
    }

    .sbs-nav-cta {
      padding: 9px 16px !important;
      border-radius: 999px;
      background: var(--sbs-accent) !important;
      color: #111827 !important;
      font-weight: 600;
      box-shadow: 0 8px 18px rgba(255,180,0,0.32);
    }

    .sbs-nav-cta:hover {
      transform: translateY(-1px);
      box-shadow: 0 12px 26px rgba(255,180,0,0.4);
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

    /* Dark Mode Toggle */
    .dark-mode-toggle {
      background: var(--sbs-white);
      border: 2px solid var(--sbs-border-soft);
      border-radius: 999px;
      width: 48px;
      height: 28px;
      cursor: pointer;
      position: relative;
      transition: all 0.3s ease;
      padding: 0;
      overflow: hidden;
    }

    .dark-mode-toggle:hover {
      border-color: var(--sbs-accent);
    }

    .sun-icon,
    .moon-icon {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      font-size: 14px;
      transition: all 0.3s ease;
    }

    .sun-icon {
      left: 4px;
    }

    .moon-icon {
      right: 4px;
      opacity: 0;
    }

    [data-theme="dark"] .sun-icon {
      opacity: 0;
      left: -20px;
    }

    [data-theme="dark"] .moon-icon {
      opacity: 1;
      right: 4px;
    }

    /* FOOTER */
    #sbs-footer-global {
      border-top: 1px solid var(--sbs-border-soft);
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
      opacity: 0.9;
      transition: var(--transition-fast);
    }

    #sbs-footer-global a:hover {
      opacity: 1;
      color: var(--sbs-accent);
    }

    /* ================================================
       RESPONSIVE - MOBILE
       ================================================ */
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
        height: 42px;
      }

      .sbs-header-inner {
        padding: 12px 20px;
      }

      .sbs-logo-img {
        height: 38px;
      }

      .sbs-logo-text {
        font-size: 11px;
      }

      .sbs-logo-text strong {
        font-size: 12px;
      }
    }

    /* Mobile Overlay */
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
# JAVASCRIPT (alle Features)
# ============================================
JAVASCRIPT = '''
  <script>
  // ================================================
  // PREMIUM FEATURES JAVASCRIPT
  // ================================================
  
  (function() {
    'use strict';
    
    // ========================================
    // 1. BURGER MENU
    // ========================================
    const burgerMenu = document.getElementById('burger-menu');
    const mainNav = document.getElementById('main-nav');
    
    if (burgerMenu && mainNav) {
      // Create mobile overlay
      const overlay = document.createElement('div');
      overlay.className = 'mobile-overlay';
      document.body.appendChild(overlay);
      
      burgerMenu.addEventListener('click', function() {
        burgerMenu.classList.toggle('active');
        mainNav.classList.toggle('active');
        overlay.classList.toggle('active');
        document.body.style.overflow = mainNav.classList.contains('active') ? 'hidden' : '';
      });
      
      // Close menu when clicking overlay
      overlay.addEventListener('click', function() {
        burgerMenu.classList.remove('active');
        mainNav.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      });
      
      // Close menu when clicking link
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
    // 2. ACTIVE STATES (automatisch)
    // ========================================
    function setActiveNavLink() {
      const currentPath = window.location.pathname;
      const navLinks = document.querySelectorAll('.sbs-nav a[data-page]');
      
      navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        
        // Check if current path matches
        if (currentPath === href || 
            currentPath.endsWith(href) ||
            (href === '/sbshomepage/' && currentPath === '/') ||
            (href === '/landing' && currentPath.includes('/landing'))) {
          link.classList.add('active');
        }
      });
    }
    
    setActiveNavLink();
    
    // ========================================
    // 3. SCROLL ANIMATION
    // ========================================
    const header = document.getElementById('main-header');
    let lastScroll = 0;
    
    if (header) {
      window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 80) {
          header.classList.add('scrolled');
        } else {
          header.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
      });
    }
    
    // ========================================
    // 4. DARK MODE TOGGLE
    // ========================================
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    // Load saved theme
    const savedTheme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    if (darkModeToggle) {
      darkModeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('sbs-theme', newTheme);
        
        // Animation
        darkModeToggle.style.transform = 'rotate(360deg)';
        setTimeout(() => {
          darkModeToggle.style.transform = '';
        }, 300);
      });
    }
    
    // ========================================
    // 5. SMOOTH SCROLL FOR ANCHOR LINKS
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href !== '#!') {
          e.preventDefault();
          const target = document.querySelector(href);
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      });
    });
    
  })();
  </script>'''

# ============================================
# UPDATE FUNCTIONS
# ============================================

def update_html_file(filepath):
    """HTML-Datei mit Premium Features updaten"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Header ersetzen
        header_pattern = r'<header[^>]*>.*?</header>'
        if re.search(header_pattern, content, re.DOTALL):
            content = re.sub(header_pattern, HEADER_HTML, content, flags=re.DOTALL)
        else:
            content = content.replace('<body>', '<body>\n' + HEADER_HTML + '\n', 1)
        
        # 2. Footer ersetzen
        footer_pattern = r'<footer[^>]*>.*?</footer>'
        if re.search(footer_pattern, content, re.DOTALL):
            content = re.sub(footer_pattern, FOOTER_HTML, content, flags=re.DOTALL)
        else:
            content = content.replace('</body>', '\n' + FOOTER_HTML + '\n</body>', 1)
        
        # 3. CSS hinzufügen/updaten
        if '.sbs-header {' not in content and '<style>' in content:
            content = content.replace('</style>', PREMIUM_CSS + '\n  </style>', 1)
        elif '<head>' in content and '<style>' not in content:
            content = content.replace('</head>', '  <style>' + PREMIUM_CSS + '\n  </style>\n</head>', 1)
        
        # 4. JavaScript hinzufügen (vor </body>)
        if 'burger-menu' not in content or 'dark-mode-toggle' not in content:
            content = content.replace('</body>', JAVASCRIPT + '\n</body>', 1)
        
        # 5. Speichern wenn Änderungen
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"❌ Fehler bei {filepath}: {e}")
        return False

def main():
    """Alle HTML-Dateien mit Premium Features updaten"""
    
    base_dir = Path('/var/www/invoice-app/web')
    
    files_to_update = [
        # Landing Page
        'static/landing/index.html',
        'static/landing/impressum.html',
        'static/landing/datenschutz.html',
        'static/landing/agb.html',
        
        # SBS Homepage
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
        
        # Templates
        'templates/index.html',
        'templates/results.html',
    ]
    
    updated = 0
    skipped = 0
    
    print("🚀 PREMIUM UPDATE GESTARTET!")
    print("=" * 60)
    print("Features:")
    print("  ✅ Burger Menu (Mobile)")
    print("  ✅ Automatische Active States")
    print("  ✅ Scroll Animation (Header)")
    print("  ✅ Dark Mode Toggle")
    print("=" * 60)
    print()
    
    for file_path in files_to_update:
        full_path = base_dir / file_path
        
        if not full_path.exists():
            print(f"⚠️  Übersprungen: {file_path}")
            skipped += 1
            continue
        
        if update_html_file(str(full_path)):
            print(f"✅ Updated: {file_path}")
            updated += 1
        else:
            print(f"⏭️  Keine Änderung: {file_path}")
            skipped += 1
    
    print()
    print("=" * 60)
    print(f"✅ FERTIG! {updated} Dateien updated, {skipped} übersprungen.")
    print("=" * 60)
    print()
    print("🧪 JETZT TESTEN:")
    print("  📱 Mobile: Browser-DevTools → Responsive Mode")
    print("  🌙 Dark Mode: Klick auf Moon/Sun Icon")
    print("  📍 Active States: Navigation automatisch markiert")
    print("  📜 Scroll: Header wird beim Scrollen kleiner")
    print()

if __name__ == '__main__':
    main()
