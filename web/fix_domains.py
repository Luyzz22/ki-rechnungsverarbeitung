#!/usr/bin/env python3
"""
Fix: Separate Headers für app.sbsdeutschland.com und sbsdeutschland.com
"""

import re
from pathlib import Path

# ============================================
# HEADER FÜR APP-DOMAIN (absolute URLs)
# ============================================
HEADER_APP = '''  <!-- HEADER (APP Domain) -->
  <header class="sbs-header" id="main-header">
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
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode Toggle">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''

# ============================================
# HEADER FÜR MAIN-DOMAIN (relative URLs)
# ============================================
HEADER_MAIN = '''  <!-- HEADER (MAIN Domain) -->
  <header class="sbs-header" id="main-header">
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
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode Toggle">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''

# ============================================
# FOOTER (gleich für beide)
# ============================================
FOOTER_HTML = '''  <!-- FOOTER (global) -->
  <footer id="sbs-footer-global">
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

def update_file(filepath, header_html):
    """Update eine einzelne Datei"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Header ersetzen
        header_pattern = r'<header[^>]*>.*?</header>'
        if re.search(header_pattern, content, re.DOTALL):
            content = re.sub(header_pattern, header_html, content, flags=re.DOTALL)
        
        # Footer ersetzen
        footer_pattern = r'<footer[^>]*>.*?</footer>'
        if re.search(footer_pattern, content, re.DOTALL):
            content = re.sub(footer_pattern, FOOTER_HTML, content, flags=re.DOTALL)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

def main():
    base = Path('/var/www/invoice-app/web')
    
    # APP-Domain Dateien (templates/)
    app_files = [
        'templates/index.html',
        'templates/results.html',
    ]
    
    # MAIN-Domain Dateien (sbshomepage/, static/landing/)
    main_files = [
        'static/landing/index.html',
        'static/landing/impressum.html',
        'static/landing/datenschutz.html',
        'static/landing/agb.html',
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
    ]
    
    print("🔧 DOMAIN-FIX GESTARTET!")
    print("=" * 60)
    
    # Update APP-Domain Dateien
    print("\n📱 APP-Domain (app.sbsdeutschland.com):")
    for file in app_files:
        path = base / file
        if path.exists():
            if update_file(path, HEADER_APP):
                print(f"  ✅ {file}")
            else:
                print(f"  ⏭️  {file}")
    
    # Update MAIN-Domain Dateien
    print("\n🌐 MAIN-Domain (sbsdeutschland.com):")
    for file in main_files:
        path = base / file
        if path.exists():
            if update_file(path, HEADER_MAIN):
                print(f"  ✅ {file}")
            else:
                print(f"  ⏭️  {file}")
    
    print("\n" + "=" * 60)
    print("✅ FERTIG!")
    print("=" * 60)
    print("\n🧪 JETZT TESTEN:")
    print("  1. https://app.sbsdeutschland.com/")
    print("     → Klick auf 'Startseite' → Sollte zu sbsdeutschland.com")
    print("  2. https://sbsdeutschland.com/")
    print("     → Klick auf 'Upload' → Sollte zu app.sbsdeutschland.com")
    print()

if __name__ == '__main__':
    main()
