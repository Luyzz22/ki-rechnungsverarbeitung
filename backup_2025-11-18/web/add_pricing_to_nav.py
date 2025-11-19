#!/usr/bin/env python3
import re
from pathlib import Path

def update_nav_links(content, domain_type='main'):
    """Fügt Preise zur Navigation hinzu"""
    
    if 'href="/preise"' in content or 'href="https://sbsdeutschland.com/preise"' in content:
        return content
    
    if domain_type == 'app':
        old_nav = r'(<a href="https://sbsdeutschland\.com/landing"[^>]*>KI-Rechnungsverarbeitung</a>)\s*(<a href="https://sbsdeutschland\.com/sbshomepage/unternehmen\.html")'
        new_nav = r'\1\n        <a href="https://sbsdeutschland.com/preise">Preise</a>\n        \2'
    else:
        old_nav = r'(<a href="/landing"[^>]*>KI-Rechnungsverarbeitung</a>)\s*(<a href="/sbshomepage/unternehmen\.html")'
        new_nav = r'\1\n        <a href="/preise">Preise</a>\n        \2'
    
    return re.sub(old_nav, new_nav, content)

def update_file(filepath, domain_type='main'):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = update_nav_links(content, domain_type)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
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
    ]
    
    print("🔗 PREISE ZUR NAVIGATION HINZUFÜGEN")
    print("=" * 60)
    
    updated = 0
    
    print("\n📱 APP-Domain:")
    for file in app_files:
        path = base / file
        if path.exists():
            if update_file(path, 'app'):
                print(f"  ✅ {file}")
                updated += 1
            else:
                print(f"  ⏭️  {file} (bereits aktuell)")
    
    print("\n🌐 MAIN-Domain:")
    for file in main_files:
        path = base / file
        if path.exists():
            if update_file(path, 'main'):
                print(f"  ✅ {file}")
                updated += 1
            else:
                print(f"  ⏭️  {file} (bereits aktuell)")
    
    print(f"\n✅ FERTIG! {updated} Dateien aktualisiert")
    print("\n🧪 Testen: https://sbsdeutschland.com/preise")

if __name__ == '__main__':
    main()
