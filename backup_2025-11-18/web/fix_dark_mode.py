#!/usr/bin/env python3
import re
from pathlib import Path
from datetime import datetime

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

DARK_MODE_JS = '''
  <script>
  (function() {
    var theme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    var toggle = document.getElementById('dark-mode-toggle');
    if (toggle) {
      toggle.addEventListener('click', function(e) {
        e.preventDefault();
        var current = document.documentElement.getAttribute('data-theme');
        var next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('sbs-theme', next);
      });
    }
  })();
  </script>'''

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '[data-theme="dark"]' in content:
            return False
        
        original = content
        
        # Add CSS after :root
        match = re.search(r'(:root\s*\{[^}]+\})', content, re.DOTALL)
        if match:
            content = content[:match.end()] + DARK_MODE_CSS + content[match.end():]
        
        # Add JS before </body>
        if "localStorage.getItem('sbs-theme')" not in content and '</body>' in content:
            content = content.replace('</body>', DARK_MODE_JS + '\n</body>')
        
        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error {path}: {e}")
        return False

base = Path('/var/www/invoice-app/web')
files = list(base.glob('templates/**/*.html')) + list(base.glob('static/**/*.html'))

print("Dark Mode Fix")
print("=" * 50)
updated = 0
for f in set(files):
    if fix_file(f):
        print(f"OK: {f.relative_to(base)}")
        updated += 1
    else:
        print(f"Skip: {f.relative_to(base)}")
print(f"\nUpdated: {updated} files")
