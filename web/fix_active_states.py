#!/usr/bin/env python3
"""
Fix: Active States und Landing Page Dark Mode
"""

import re
from pathlib import Path

# JavaScript mit besserer Active-State-Logik
FIXED_JS = '''
  <script>
  (function() {
    'use strict';
    
    console.log('🎨 Design Script loaded');
    
    // ========================================
    // DARK MODE - LADEN & SETZEN
    // ========================================
    const savedTheme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Body theme auch setzen
    if (document.body) {
      document.body.setAttribute('data-theme', savedTheme);
    }
    
    console.log('📱 Theme:', savedTheme);
    
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
    // ACTIVE STATES - NUR EINE SEITE AKTIV
    // ========================================
    function setActiveNavLink() {
      const currentPath = window.location.pathname;
      const navLinks = document.querySelectorAll('.sbs-nav a[data-page]');
      
      // ALLE active entfernen
      navLinks.forEach(link => link.classList.remove('active'));
      
      // NUR die aktuelle Seite markieren
      if (currentPath.includes('/landing')) {
        const landingLink = document.querySelector('a[data-page="landing"]');
        if (landingLink) landingLink.classList.add('active');
      } else if (currentPath.includes('/unternehmen')) {
        const aboutLink = document.querySelector('a[data-page="unternehmen"]');
        if (aboutLink) aboutLink.classList.add('active');
      } else if (currentPath.includes('/kontakt')) {
        const contactLink = document.querySelector('a[data-page="kontakt"]');
        if (contactLink) contactLink.classList.add('active');
      } else if (currentPath.includes('/sbshomepage') || currentPath === '/') {
        const homeLink = document.querySelector('a[data-page="home"]');
        if (homeLink) homeLink.classList.add('active');
      }
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
    // DARK MODE TOGGLE
    // ========================================
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    if (darkModeToggle) {
      console.log('🌙 Dark mode button ready');
      
      darkModeToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        console.log('🔄 Switching to', newTheme);
        
        document.documentElement.setAttribute('data-theme', newTheme);
        if (document.body) {
          document.body.setAttribute('data-theme', newTheme);
        }
        localStorage.setItem('sbs-theme', newTheme);
        
        // Animation
        darkModeToggle.style.transform = 'rotate(180deg)';
        setTimeout(() => {
          darkModeToggle.style.transform = '';
        }, 300);
      });
    }
    
  })();
  </script>'''

def update_js(filepath):
    """Ersetze JavaScript in Datei"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Entferne altes Script
        content = re.sub(
            r'<script>\s*\(function\(\)\s*\{.*?}\)\(\);\s*</script>',
            FIXED_JS,
            content,
            flags=re.DOTALL
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ {filepath}: {e}")
        return False

def main():
    base = Path('/var/www/invoice-app/web')
    
    all_files = [
        'templates/index.html',
        'templates/results.html',
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
    print("🔧 FIX: ACTIVE STATES & LANDING PAGE DARK MODE")
    print("=" * 70)
    print()
    print("Fixes:")
    print("  ✅ Nur EINE Seite hat gelbe Unterstreichung")
    print("  ✅ Landing Page: vollständiger Dark Mode")
    print("=" * 70)
    print()
    
    updated = 0
    for file in all_files:
        path = base / file
        if path.exists():
            if update_js(path):
                print(f"  ✅ {file}")
                updated += 1
    
    print()
    print("=" * 70)
    print(f"✅ {updated} DATEIEN AKTUALISIERT!")
    print("=" * 70)
    print()
    print("🧪 JETZT TESTEN:")
    print("  1. Browser neu laden (Cmd+Shift+R)")
    print("  2. Verschiedene Seiten öffnen")
    print("  3. NUR die aktuelle Seite sollte gelb sein")
    print("  4. Landing Page: Dark Mode funktioniert")
    print()

if __name__ == '__main__':
    main()
