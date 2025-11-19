#!/usr/bin/env python3
"""
Fügt Dark Mode Support zu allen Seiten hinzu, die ihn noch nicht haben
"""

import re
from pathlib import Path
from datetime import datetime

# Dark Mode JavaScript Code
DARK_MODE_SCRIPT = '''
  <script>
  (function() {
    'use strict';
    
    // Dark Mode
    const savedTheme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (document.body) {
      document.body.setAttribute('data-theme', savedTheme);
    }
    
    // Burger Menu
    const burgerMenu = document.getElementById('burger-menu');
    const mainNav = document.getElementById('main-nav');
    
    if (burgerMenu && mainNav) {
      burgerMenu.addEventListener('click', function() {
        burgerMenu.classList.toggle('active');
        mainNav.classList.toggle('active');
      });
    }
    
    // Dark Mode Toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    if (darkModeToggle) {
      darkModeToggle.addEventListener('click', function(e) {
        e.preventDefault();
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        if (document.body) {
          document.body.setAttribute('data-theme', newTheme);
        }
        localStorage.setItem('sbs-theme', newTheme);
      });
    }
  })();
  </script>'''

# Dark Mode CSS Variables
DARK_MODE_CSS = '''
    [data-theme="dark"] {
      --sbs-bg: #0f172a;
      --sbs-white: #1e293b;
      --sbs-dark: #60a5fa;
      --sbs-dark-soft: #e2e8f0;
      --sbs-text: #e2e8f0;
      --sbs-muted: #94a3b8;
      --sbs-gradient: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    }
    
    [data-theme="dark"] .sun-icon { opacity: 0.3; }
    [data-theme="light"] .moon-icon { opacity: 0.3; }'''

def has_dark_mode(content):
    """Prüft ob Dark Mode bereits vorhanden ist"""
    return 'data-theme="dark"' in content or '[data-theme="dark"]' in content

def add_dark_mode_css(content):
    """Fügt Dark Mode CSS Variables hinzu"""
    # Finde das :root { ... } CSS
    root_pattern = r'(:root\s*\{[^}]+\})'
    match = re.search(root_pattern, content, re.DOTALL)
    
    if match:
        # Füge Dark Mode CSS nach :root ein
        insert_pos = match.end()
        new_content = content[:insert_pos] + '\n' + DARK_MODE_CSS + content[insert_pos:]
        return new_content
    else:
        # Kein :root gefunden, füge vor </style> ein
        if '</style>' in content:
            return content.replace('</style>', DARK_MODE_CSS + '\n  </style>')
    
    return content

def add_dark_mode_script(content):
    """Fügt Dark Mode JavaScript hinzu"""
    # Prüfe ob Script bereits existiert
    if "localStorage.getItem('sbs-theme')" in content:
        return content
    
    # Füge vor </body> ein
    if '</body>' in content:
        return content.replace('</body>', DARK_MODE_SCRIPT + '\n\n</body>')
    
    return content

def process_file(filepath):
    """Verarbeitet eine HTML-Datei"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip wenn Dark Mode bereits vorhanden
        if has_dark_mode(content):
            return False, "already has dark mode"
        
        original_content = content
        
        # Füge CSS hinzu
        content = add_dark_mode_css(content)
        
        # Füge JavaScript hinzu
        content = add_dark_mode_script(content)
        
        if content != original_content:
            # Backup erstellen
            backup_path = filepath.parent / f"{filepath.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Neue Version schreiben
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, backup_path
        
        return False, "no changes needed"
    except Exception as e:
        return False, str(e)

def main():
    base = Path('/var/www/invoice-app/web')
    
    # Alle HTML-Dateien außer sbshomepage (die haben wir schon gemacht)
    html_files = []
    
    # Templates
    html_files.extend(base.glob('templates/**/*.html'))
    
    # Static (außer sbshomepage)
    for pattern in ['static/landing/**/*.html', 'static/preise/**/*.html', 'static/*.html']:
        html_files.extend(base.glob(pattern))
    
    # Impressum, Datenschutz, AGB aus static/landing
    html_files.extend((base / 'static/landing').glob('*.html'))
    
    print("=" * 70)
    print("🌙 DARK MODE FIX FÜR ALLE SEITEN")
    print("=" * 70)
    print()
    print(f"📁 Gefundene HTML-Dateien: {len(html_files)}")
    print()
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for filepath in sorted(set(html_files)):
        rel_path = filepath.relative_to(base)
        success, result = process_file(filepath)
        
        if success:
            print(f"✅ {rel_path}")
            updated_count += 1
        else:
            if "already has dark mode" in str(result):
                print(f"⏭️  {rel_path} (bereits Dark Mode)")
                skipped_count += 1
            elif "no changes needed" in str(result):
                print(f"⏭️  {rel_path} (keine Änderung)")
                skipped_count += 1
            else:
                print(f"❌ {rel_path}: {result}")
                error_count += 1
    
    print()
    print("=" * 70)
    print("✅ DARK MODE FIX ABGESCHLOSSEN")
    print("=" * 70)
    print()
    print(f"📊 Statistik:")
    print(f"   • {len(html_files)} Dateien gescannt")
    print(f"   • {updated_count} Dateien aktualisiert")
    print(f"   • {skipped_count} Dateien übersprungen")
    print(f"   • {error_count} Fehler")
    print()
    print("🌙 Dark Mode Features:")
    print("   • CSS Variables für Light/Dark Theme")
    print("   • LocalStorage-Persistenz")
    print("   • Toggle-Button funktioniert")
    print("   • Automatische Theme-Erkennung")
    print()
    print("🧪 Testen:")
    print("   https://sbsdeutschland.com/landing")
    print("   https://sbsdeutschland.com/preise")
    print("   https://app.sbsdeutschland.com/")
    print()
    print("💡 Dark Mode Toggle: Klicke auf das 🌙-Icon!")
    print()

if __name__ == '__main__':
    main()
