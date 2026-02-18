#!/usr/bin/env python3
"""
Aktualisiert den Footer auf ALLEN Seiten mit modernem, cleanerem Design
Ändert Copyright auf 2025
"""

import re
from pathlib import Path
from datetime import datetime

# Moderner, cleaner Footer (2025)
NEW_FOOTER = '''  <!-- FOOTER -->
  <footer class="footer">
    <div class="footer-container">
      <div class="footer-content">
        <div class="footer-section footer-main">
          <div class="footer-logo">
            <img src="/static/sbs-logo-new.png" alt="SBS Deutschland Logo" class="footer-logo-img" />
            <div class="footer-brand">
              <strong>SBS Deutschland</strong>
              <span>Smart Business Service</span>
            </div>
          </div>
          <p class="footer-tagline">Ihr Partner für intelligente Geschäftsprozesse und KI-Lösungen aus der Rhein-Neckar-Region.</p>
          <div class="footer-location">
            <i>📍</i>
            <span>In der Dell 19, 69469 Weinheim</span>
          </div>
        </div>
        
        <div class="footer-section">
          <h4>Produkte</h4>
          <ul>
            <li><a href="/landing">KI-Rechnungsverarbeitung</a></li>
            <li><a href="/preise">Preise & Pakete</a></li>
            <li><a href="https://app.sbsdeutschland.com/">Demo & Upload</a></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>Unternehmen</h4>
          <ul>
            <li><a href="/sbshomepage/unternehmen.html">Über uns</a></li>
            <li><a href="/sbshomepage/kontakt.html">Kontakt</a></li>
            <li><a href="/sbshomepage/it-consulting.html">IT Consulting</a></li>
            <li><a href="/sbshomepage/sap-consulting.html">SAP Consulting</a></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>Rechtliches</h4>
          <ul>
            <li><a href="/sbshomepage/impressum.html">Impressum</a></li>
            <li><a href="/sbshomepage/datenschutz.html">Datenschutz</a></li>
            <li><a href="/sbshomepage/agb.html">AGB</a></li>
          </ul>
        </div>
      </div>
      
      <div class="footer-bottom">
        <p>&copy; 2026 SBS Deutschland GmbH & Co. KG. Alle Rechte vorbehalten.</p>
        <p class="footer-made">Made with ❤️ in Weinheim</p>
      </div>
    </div>
  </footer>

  <style>
    .footer {
      background: linear-gradient(135deg, #001f2e 0%, #003856 100%);
      color: rgba(255, 255, 255, 0.85);
      padding: 60px 24px 24px;
      margin-top: auto;
    }

    .footer-container {
      max-width: 1200px;
      margin: 0 auto;
    }

    .footer-content {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr;
      gap: 48px;
      margin-bottom: 48px;
    }

    .footer-section h4 {
      color: #FFB900;
      font-weight: 700;
      margin-bottom: 16px;
      font-size: 1rem;
      letter-spacing: 0.5px;
    }

    .footer-section ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .footer-section ul li {
      margin-bottom: 10px;
    }

    .footer-section ul li a {
      color: rgba(255, 255, 255, 0.7);
      text-decoration: none;
      transition: color 0.3s ease;
      font-size: 0.9rem;
    }

    .footer-section ul li a:hover {
      color: #FFB900;
    }

    .footer-logo {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .footer-logo-img {
      height: 36px;
      width: auto;
    }

    .footer-brand {
      display: flex;
      flex-direction: column;
      font-size: 12px;
      line-height: 1.3;
    }

    .footer-brand strong {
      font-size: 14px;
      font-weight: 700;
      color: white;
      letter-spacing: 0.5px;
    }

    .footer-brand span {
      color: rgba(255, 255, 255, 0.6);
    }

    .footer-tagline {
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
      margin-bottom: 16px;
      font-size: 0.9rem;
    }

    .footer-location {
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.85rem;
    }

    .footer-location i {
      font-style: normal;
    }

    .footer-bottom {
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      padding-top: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.6);
    }

    .footer-made {
      margin: 0;
    }

    @media (max-width: 768px) {
      .footer-content {
        grid-template-columns: 1fr;
        gap: 32px;
      }

      .footer-bottom {
        flex-direction: column;
        text-align: center;
      }
    }
  </style>'''

def find_footer_section(content):
    """Findet den Footer-Bereich in HTML"""
    patterns = [
        (r'<footer[^>]*>.*?</footer>', re.DOTALL),
        (r'<div[^>]*id=["\']sbs-footer-global["\'][^>]*>.*?</div>\s*</body>', re.DOTALL),
        (r'<!-- FOOTER -->.*?</footer>', re.DOTALL),
    ]
    
    for pattern, flags in patterns:
        match = re.search(pattern, content, flags)
        if match:
            return match.group(0), match.start(), match.end()
    
    return None, None, None

def update_footer(content):
    """Ersetzt den Footer durch den neuen"""
    old_footer, start, end = find_footer_section(content)
    
    if old_footer:
        new_content = content[:start] + NEW_FOOTER + '\n\n</body>\n</html>'
        new_content = re.sub(r'</body>\s*</body>', '</body>', new_content)
        new_content = re.sub(r'</html>\s*</html>', '</html>', new_content)
        return new_content
    else:
        if '</body>' in content:
            return content.replace('</body>', NEW_FOOTER + '\n\n</body>')
        else:
            return content + NEW_FOOTER

def update_copyright_year(content):
    """Ändert 2024 zu 2025 im Copyright"""
    patterns = [
        r'©\s*2024',
        r'&copy;\s*2024',
        r'Copyright\s*©?\s*2024',
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, lambda m: m.group(0).replace('2024', '2025'), content, flags=re.IGNORECASE)
    
    return content

def process_file(filepath):
    """Verarbeitet eine einzelne Datei"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        content = update_copyright_year(content)
        content = update_footer(content)
        
        if content != original_content:
            backup_path = filepath.parent / f"{filepath.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, backup_path
        return False, None
    except Exception as e:
        return False, str(e)

def main():
    base = Path('/var/www/invoice-app/web')
    
    html_files = []
    html_files.extend(base.glob('templates/**/*.html'))
    html_files.extend(base.glob('static/**/*.html'))
    html_files.extend(base.glob('sbshomepage/**/*.html'))
    html_files.extend(base.glob('*.html'))
    
    print("=" * 70)
    print("🔄 FOOTER-UPDATE FÜR ALLE SEITEN")
    print("=" * 70)
    print()
    print(f"📁 Gefundene HTML-Dateien: {len(html_files)}")
    print()
    
    updated_count = 0
    error_count = 0
    
    for filepath in sorted(html_files):
        rel_path = filepath.relative_to(base)
        success, backup = process_file(filepath)
        
        if success:
            if isinstance(backup, Path):
                print(f"✅ {rel_path}")
                updated_count += 1
            else:
                print(f"⏭️  {rel_path} (keine Änderung)")
        else:
            print(f"❌ {rel_path}: {backup}")
            error_count += 1
    
    print()
    print("=" * 70)
    print("✅ FOOTER-UPDATE ABGESCHLOSSEN")
    print("=" * 70)
    print()
    print(f"📊 Statistik:")
    print(f"   • {len(html_files)} Dateien gescannt")
    print(f"   • {updated_count} Dateien aktualisiert")
    print(f"   • {error_count} Fehler")
    print()
    print("🎨 Neuer Footer:")
    print("   • Modernes Grid-Layout (4 Spalten)")
    print("   • Logo + Brand im ersten Bereich")
    print("   • Gradient-Background (Dunkelblau)")
    print("   • Akzent-Farbe: #FFB900 (SBS Gelb)")
    print("   • Copyright: © 2026")
    print("   • Responsive für Mobile optimiert")
    print()
    print("💾 Backups:")
    print("   Alle Original-Dateien wurden als .backup_TIMESTAMP gesichert")
    print()
    print("🧪 Testen:")
    print("   https://sbsdeutschland.com/preise")
    print("   https://sbsdeutschland.com/landing")
    print("   https://sbsdeutschland.com/")
    print()

if __name__ == '__main__':
    main()
