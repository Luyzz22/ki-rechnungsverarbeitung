#!/usr/bin/env python3
"""
Fix: app.sbsdeutschland.com hat Upload/Demo aktiv, nicht Startseite
"""

import re
from pathlib import Path

# Header für APP-Domain - Upload/Demo Button mit "active" Klasse
HEADER_APP_FIXED = '''  <header class="sbs-header" id="main-header">
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
        <a href="https://sbsdeutschland.com/sbshomepage/">Startseite</a>
        <a href="https://sbsdeutschland.com/landing">KI-Rechnungsverarbeitung</a>
        <a href="https://sbsdeutschland.com/sbshomepage/unternehmen.html">Über uns</a>
        <a href="https://sbsdeutschland.com/sbshomepage/kontakt.html">Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta active">Upload / Demo</a>
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>'''

def update_header(filepath, new_header):
    """Ersetze Header in Datei"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Header ersetzen
        header_pattern = r'<header[^>]*>.*?</header>'
        if re.search(header_pattern, content, re.DOTALL):
            content = re.sub(header_pattern, new_header, content, flags=re.DOTALL)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"❌ {filepath}: {e}")
        return False

def main():
    base = Path('/var/www/invoice-app/web')
    
    app_files = [
        'templates/index.html',
        'templates/results.html',
    ]
    
    print("🔧 FIX: app.sbsdeutschland.com Active State")
    print("=" * 60)
    
    for file in app_files:
        path = base / file
        if path.exists():
            if update_header(path, HEADER_APP_FIXED):
                print(f"  ✅ {file}")
    
    print()
    print("✅ FERTIG! Jetzt ist 'Upload / Demo' aktiv auf app.sbsdeutschland.com")
    print()

if __name__ == '__main__':
    main()
