#!/usr/bin/env python3
"""
Professionelles Redesign aller SBS Homepage-Seiten
- Einheitliches Design mit Dark Mode
- Hero-Sections mit Gradient
- Icon-Cards für Features
- Moderner Footer (2025)
- Responsive Layout
"""

from pathlib import Path

# Base HTML Template mit Dark Mode Support
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | SBS Deutschland</title>
  <meta name="description" content="{description}">
  <link rel="icon" href="/static/favicon.ico">
  
  <style>
    :root {{
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-dark-soft: #0b2435;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
      --sbs-gradient: linear-gradient(135deg, #003856 0%, #005a8a 100%);
      --transition: all 0.3s ease;
    }}
    
    [data-theme="dark"] {{
      --sbs-bg: #0f172a;
      --sbs-white: #1e293b;
      --sbs-dark: #60a5fa;
      --sbs-dark-soft: #e2e8f0;
      --sbs-text: #e2e8f0;
      --sbs-muted: #94a3b8;
      --sbs-gradient: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    }}
    
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--sbs-bg);
      color: var(--sbs-text);
      line-height: 1.6;
      transition: background 0.3s ease, color 0.3s ease;
    }}

    /* HEADER */
    .sbs-header {{
      position: sticky;
      top: 0;
      z-index: 1000;
      background: var(--sbs-white);
      box-shadow: 0 1px 12px rgba(15,23,42,0.06);
      transition: var(--transition);
    }}

    .sbs-header-inner {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 32px;
    }}

    .sbs-logo-wrap {{
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }}

    .sbs-logo-img {{
      height: 40px;
      width: auto;
    }}

    .sbs-logo-text {{
      display: flex;
      flex-direction: column;
      font-size: 12px;
      line-height: 1.25;
      color: var(--sbs-dark-soft);
    }}

    .sbs-logo-text strong {{
      font-size: 13px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      font-weight: 700;
    }}

    .burger-menu {{
      display: none;
      flex-direction: column;
      gap: 5px;
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      z-index: 1001;
    }}

    .burger-menu span {{
      width: 25px;
      height: 3px;
      background: var(--sbs-dark-soft);
      border-radius: 3px;
      transition: var(--transition);
    }}

    .sbs-nav {{
      display: flex;
      align-items: center;
      gap: 24px;
      font-size: 14px;
    }}

    .sbs-nav a {{
      position: relative;
      padding-bottom: 4px;
      opacity: 0.85;
      transition: var(--transition);
      text-decoration: none;
      color: var(--sbs-text);
      font-weight: 500;
    }}

    .sbs-nav a:hover {{
      opacity: 1;
    }}

    .sbs-nav a.active::after {{
      content: "";
      position: absolute;
      left: 0;
      bottom: 0;
      width: 100%;
      height: 2px;
      border-radius: 999px;
      background: var(--sbs-accent);
    }}

    .sbs-nav-cta {{
      padding: 9px 18px !important;
      border-radius: 999px !important;
      background: var(--sbs-accent) !important;
      color: #111827 !important;
      font-weight: 600 !important;
      box-shadow: 0 4px 12px rgba(255,180,0,0.3) !important;
      opacity: 1 !important;
    }}

    .sbs-nav-cta::after {{
      display: none !important;
    }}

    .sbs-nav-cta:hover {{
      transform: translateY(-1px) !important;
      box-shadow: 0 6px 16px rgba(255,180,0,0.4) !important;
    }}

    .dark-mode-toggle {{
      background: var(--sbs-white);
      border: 2px solid rgba(15,23,42,0.12);
      border-radius: 999px;
      width: 50px;
      height: 28px;
      cursor: pointer;
      transition: var(--transition);
      padding: 0 6px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .dark-mode-toggle:hover {{
      border-color: var(--sbs-accent);
      transform: scale(1.05);
    }}

    .sun-icon, .moon-icon {{
      font-size: 14px;
      transition: var(--transition);
    }}

    [data-theme="dark"] .sun-icon {{ opacity: 0.3; }}
    [data-theme="light"] .moon-icon {{ opacity: 0.3; }}

    /* HERO */
    .hero {{
      background: var(--sbs-gradient);
      padding: 80px 24px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}

    .hero::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
      opacity: 0.4;
    }}

    .hero-content {{
      max-width: 900px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }}

    .hero-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
      padding: 8px 18px;
      border-radius: 999px;
      color: white;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.5px;
      margin-bottom: 24px;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }}

    .hero h1 {{
      font-size: 3rem;
      font-weight: 800;
      color: white;
      line-height: 1.2;
      margin-bottom: 20px;
      letter-spacing: -0.02em;
    }}

    .hero-subtitle {{
      font-size: 1.2rem;
      color: rgba(255, 255, 255, 0.9);
      line-height: 1.6;
      max-width: 700px;
      margin: 0 auto;
    }}

    /* MAIN CONTENT */
    .main-content {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 80px 24px;
    }}

    .section-title {{
      font-size: 2.2rem;
      font-weight: 800;
      color: var(--sbs-dark);
      margin-bottom: 16px;
      text-align: center;
      letter-spacing: -0.02em;
    }}

    .section-subtitle {{
      font-size: 1.1rem;
      color: var(--sbs-muted);
      text-align: center;
      margin-bottom: 60px;
      max-width: 700px;
      margin-left: auto;
      margin-right: auto;
    }}

    /* FEATURE CARDS */
    .feature-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 32px;
      margin-top: 48px;
    }}

    .feature-card {{
      background: var(--sbs-white);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.06);
      transition: var(--transition);
    }}

    .feature-card:hover {{
      transform: translateY(-8px);
      box-shadow: 0 12px 40px rgba(0,0,0,0.12);
    }}

    .feature-icon {{
      font-size: 3rem;
      margin-bottom: 16px;
      display: block;
    }}

    .feature-card h3 {{
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--sbs-dark);
      margin-bottom: 12px;
    }}

    .feature-card p {{
      color: var(--sbs-muted);
      line-height: 1.7;
    }}

    .feature-card ul {{
      margin-top: 16px;
      padding-left: 20px;
    }}

    .feature-card ul li {{
      color: var(--sbs-muted);
      margin-bottom: 8px;
      line-height: 1.6;
    }}

    /* CONTACT CARDS */
    .contact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 32px;
      margin-top: 48px;
    }}

    .contact-card {{
      background: var(--sbs-white);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.06);
      text-align: center;
    }}

    .contact-card .icon {{
      font-size: 3rem;
      margin-bottom: 16px;
      display: block;
    }}

    .contact-card h3 {{
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--sbs-dark);
      margin-bottom: 8px;
    }}

    .contact-card p {{
      color: var(--sbs-muted);
      margin-bottom: 8px;
    }}

    .contact-card a {{
      color: var(--sbs-accent);
      text-decoration: none;
      font-weight: 600;
    }}

    .contact-card a:hover {{
      text-decoration: underline;
    }}

    /* CTA SECTION */
    .cta-section {{
      background: var(--sbs-gradient);
      padding: 80px 24px;
      text-align: center;
      border-radius: 20px;
      margin: 80px 0;
    }}

    .cta-section h2 {{
      font-size: 2.5rem;
      font-weight: 800;
      color: white;
      margin-bottom: 16px;
    }}

    .cta-section p {{
      font-size: 1.2rem;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 32px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 16px 32px;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      text-decoration: none;
      transition: var(--transition);
      cursor: pointer;
      border: none;
    }}

    .btn-primary {{
      background: var(--sbs-accent);
      color: #111827;
      box-shadow: 0 4px 20px rgba(255,180,0,0.3);
    }}

    .btn-primary:hover {{
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(255,180,0,0.4);
    }}

    .btn-secondary {{
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
      color: white;
      border: 2px solid rgba(255, 255, 255, 0.3);
    }}

    .btn-secondary:hover {{
      background: rgba(255, 255, 255, 0.25);
      transform: translateY(-2px);
    }}

    /* FOOTER */
    .footer {{
      background: linear-gradient(135deg, #001f2e 0%, #003856 100%);
      color: rgba(255, 255, 255, 0.85);
      padding: 60px 24px 24px;
      margin-top: auto;
    }}

    .footer-container {{
      max-width: 1200px;
      margin: 0 auto;
    }}

    .footer-content {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr;
      gap: 48px;
      margin-bottom: 48px;
    }}

    .footer-section h4 {{
      color: #FFB900;
      font-weight: 700;
      margin-bottom: 16px;
      font-size: 1rem;
      letter-spacing: 0.5px;
    }}

    .footer-section ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}

    .footer-section ul li {{
      margin-bottom: 10px;
    }}

    .footer-section ul li a {{
      color: rgba(255, 255, 255, 0.7);
      text-decoration: none;
      transition: color 0.3s ease;
      font-size: 0.9rem;
    }}

    .footer-section ul li a:hover {{
      color: #FFB900;
    }}

    .footer-logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }}

    .footer-logo-img {{
      height: 36px;
      width: auto;
    }}

    .footer-brand {{
      display: flex;
      flex-direction: column;
      font-size: 12px;
      line-height: 1.3;
    }}

    .footer-brand strong {{
      font-size: 14px;
      font-weight: 700;
      color: white;
      letter-spacing: 0.5px;
    }}

    .footer-brand span {{
      color: rgba(255, 255, 255, 0.6);
    }}

    .footer-tagline {{
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
      margin-bottom: 16px;
      font-size: 0.9rem;
    }}

    .footer-location {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.85rem;
    }}

    .footer-location i {{
      font-style: normal;
    }}

    .footer-bottom {{
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      padding-top: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.6);
    }}

    .footer-made {{
      margin: 0;
    }}

    /* RESPONSIVE */
    @media (max-width: 768px) {{
      .burger-menu {{ display: flex; }}
      
      .sbs-nav {{
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
      }}
      
      .sbs-nav.active {{ right: 0; }}
      
      .hero h1 {{ font-size: 2rem; }}
      .section-title {{ font-size: 1.8rem; }}
      .cta-section h2 {{ font-size: 2rem; }}
      
      .feature-grid {{
        grid-template-columns: 1fr;
      }}

      .contact-grid {{
        grid-template-columns: 1fr;
      }}

      .footer-content {{
        grid-template-columns: 1fr;
        gap: 32px;
      }}

      .footer-bottom {{
        flex-direction: column;
        text-align: center;
      }}
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header class="sbs-header">
    <div class="sbs-header-inner">
      <a href="/sbshomepage/" class="sbs-logo-wrap">
        <img src="/static/sbs-logo-new.png" alt="SBS Deutschland Logo" class="sbs-logo-img" />
        <div class="sbs-logo-text">
          <strong>SBS Deutschland GmbH & Co. KG</strong>
          <span>Smart Business Service · Weinheim</span>
        </div>
      </a>
      
      <button class="burger-menu" id="burger-menu" aria-label="Menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
      
      <nav class="sbs-nav" id="main-nav">
        <a href="/sbshomepage/">Startseite</a>
        <a href="/landing">KI-Rechnungsverarbeitung</a>
        <a href="/preise">Preise</a>
        <a href="/sbshomepage/unternehmen.html" {active_unternehmen}>Über uns</a>
        <a href="/sbshomepage/kontakt.html" {active_kontakt}>Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta">Upload / Demo</a>
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>

{content}

  <!-- FOOTER -->
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

  <script>
  (function() {{
    'use strict';
    
    // Dark Mode
    const savedTheme = localStorage.getItem('sbs-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (document.body) {{
      document.body.setAttribute('data-theme', savedTheme);
    }}
    
    // Burger Menu
    const burgerMenu = document.getElementById('burger-menu');
    const mainNav = document.getElementById('main-nav');
    
    if (burgerMenu && mainNav) {{
      burgerMenu.addEventListener('click', function() {{
        burgerMenu.classList.toggle('active');
        mainNav.classList.toggle('active');
      }});
    }}
    
    // Dark Mode Toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    if (darkModeToggle) {{
      darkModeToggle.addEventListener('click', function(e) {{
        e.preventDefault();
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        if (document.body) {{
          document.body.setAttribute('data-theme', newTheme);
        }}
        localStorage.setItem('sbs-theme', newTheme);
      }});
    }}
  }})();
  </script>

</body>
</html>'''

# Seiten-Definitionen
PAGES = {
    'kontakt.html': {
        'title': 'Kontakt',
        'description': 'Nehmen Sie Kontakt mit SBS Deutschland auf. Wir beraten Sie gerne zu KI-Rechnungsverarbeitung und unseren Consulting-Dienstleistungen.',
        'badge': '💬 KONTAKT',
        'h1': 'Sprechen Sie uns an',
        'subtitle': 'Sie möchten mehr über unsere KI-Rechnungsverarbeitung oder unsere Dienstleistungen erfahren? Unser Team in Weinheim steht Ihnen gerne zur Verfügung.',
        'active': 'kontakt',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">💬 KONTAKT</div>
      <h1>Sprechen Sie uns an</h1>
      <p class="hero-subtitle">Sie möchten mehr über unsere KI-Rechnungsverarbeitung oder unsere Dienstleistungen erfahren? Unser Team in Weinheim steht Ihnen gerne zur Verfügung.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Wie können wir Ihnen helfen?</h2>
    <p class="section-subtitle">Wählen Sie den für Sie passenden Kontaktweg - wir freuen uns auf Ihre Nachricht.</p>

    <div class="contact-grid">
      <div class="contact-card">
        <span class="icon">📍</span>
        <h3>Adresse</h3>
        <p><strong>SBS Deutschland GmbH & Co. KG</strong></p>
        <p>In der Dell 19</p>
        <p>69469 Weinheim</p>
        <p>Deutschland</p>
      </div>

      <div class="contact-card">
        <span class="icon">📞</span>
        <h3>Telefon</h3>
        <p>Rufen Sie uns direkt an:</p>
        <p><a href="tel:+4962018061009">+49 6201 80 6109</a></p>
        <p style="font-size: 0.85rem; margin-top: 12px;">Mo-Fr: 9:00-17:00 Uhr</p>
      </div>

      <div class="contact-card">
        <span class="icon">✉️</span>
        <h3>E-Mail</h3>
        <p>Schreiben Sie uns eine Nachricht:</p>
        <p><a href="mailto:info@sbsdeutschland.com">info@sbsdeutschland.com</a></p>
        <p style="font-size: 0.85rem; margin-top: 12px;">Antwort innerhalb von 24h</p>
      </div>

      <div class="contact-card">
        <span class="icon">🌐</span>
        <h3>Web</h3>
        <p>Besuchen Sie unsere Website:</p>
        <p><a href="https://www.sbsdeutschland.com" target="_blank">www.SBSDeutschland.com</a></p>
        <p style="font-size: 0.85rem; margin-top: 12px;">Weitere Informationen</p>
      </div>
    </div>

    <div class="cta-section" style="margin-top: 80px;">
      <h2>Testen Sie unsere KI-Rechnungsverarbeitung</h2>
      <p>Für Produkt-Demos nutzen Sie gerne unser interaktives Formular und die Kontaktmöglichkeiten auf unserer KI-Seite.</p>
      <a href="/landing#demo" class="btn btn-primary">🚀 Zur Demo</a>
    </div>
  </div>
'''
    },
    
    'unternehmen.html': {
        'title': 'Über uns',
        'description': 'SBS Deutschland - Ihr Partner für Smart Business Services in der Rhein-Neckar-Region. KI-Technologie, IT Consulting und SAP-Expertise.',
        'badge': '🏢 ÜBER UNS',
        'h1': 'Smart Business Services aus Weinheim',
        'subtitle': 'Die SBS Deutschland GmbH & Co. KG steht für moderne KI-Technologie, praktische Beratung und tiefes Prozessverständnis - regional verankert, technologisch führend.',
        'active': 'unternehmen',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">🏢 ÜBER UNS</div>
      <h1>Smart Business Services aus Weinheim</h1>
      <p class="hero-subtitle">Die SBS Deutschland GmbH & Co. KG steht für moderne KI-Technologie, praktische Beratung und tiefes Prozessverständnis - regional verankert, technologisch führend.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Unsere Kompetenzen</h2>
    <p class="section-subtitle">Vier Säulen, ein Ziel: Ihre Geschäftsprozesse effizienter, sicherer und zukunftssicher zu gestalten.</p>

    <div class="feature-grid">
      <div class="feature-card">
        <span class="feature-icon">💻</span>
        <h3>IT Consulting & Softwareentwicklung</h3>
        <p>Moderne Architektur, intelligente Schnittstellen und nahtlose Automatisierung - inklusive KI-Integration in Ihre bestehenden Systeme.</p>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🎯</span>
        <h3>Quality & Risk Management</h3>
        <p>Qualitätsstandards, Risikomanagement und Auditfähigkeit für Ihre digitalen Finanz- und Dokumentenprozesse.</p>
      </div>

      <div class="feature-card">
        <span class="feature-icon">📊</span>
        <h3>SAP Consulting & Reporting</h3>
        <p>Integration moderner Lösungen in SAP-Landschaften - für durchgängige, transparente Finanzprozesse.</p>
      </div>

      <div class="feature-card">
        <span class="feature-icon">📐</span>
        <h3>Metrologie & PMO</h3>
        <p>Messmitteldokumentation, Prüfabläufe und professionelles Projektmanagement für technisch anspruchsvolle Branchen.</p>
      </div>
    </div>

    <div style="margin-top: 100px;">
      <h2 class="section-title">Regionale Verankerung, globale Standards</h2>
      <p class="section-subtitle">Mit unserem Standort in Weinheim verstehen wir die Anforderungen von Unternehmen in der Metropolregion Rhein-Neckar und im Odenwald.</p>

      <div class="feature-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));">
        <div class="feature-card">
          <span class="feature-icon">🤝</span>
          <h3>Persönlich</h3>
          <p>Direkter Ansprechpartner vor Ort, kurze Wege und schnelle Reaktionszeiten.</p>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🇩🇪</span>
          <h3>Deutschsprachig</h3>
          <p>Kompetenter Support in deutscher Sprache - klar, verständlich, lösungsorientiert.</p>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🔒</span>
          <h3>DSGVO-konform</h3>
          <p>Alle Daten bleiben in Deutschland, höchste Sicherheitsstandards inklusive.</p>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🚀</span>
          <h3>Innovativ</h3>
          <p>Modernste KI-Technologie, kontinuierlich weiterentwickelt und produktionsreif.</p>
        </div>
      </div>
    </div>

    <div class="cta-section">
      <h2>Unser Leitprodukt: KI-Rechnungsverarbeitung</h2>
      <p>Wir entwickeln kontinuierlich unsere KI-gestützte Rechnungsverarbeitung weiter, um Ihre Finanz- und Dokumentenprozesse effizienter, sicherer und transparenter zu gestalten.</p>
      <a href="/landing" class="btn btn-primary">🤖 Mehr zur KI-Rechnungsverarbeitung</a>
    </div>
  </div>
'''
    },
    
    'it-consulting.html': {
        'title': 'IT Consulting & Programming',
        'description': 'IT Consulting und Softwareentwicklung von SBS Deutschland. Architektur, Schnittstellen, Integration und Automatisierung mit KI-Support.',
        'badge': '💻 IT CONSULTING',
        'h1': 'IT Consulting & Programming',
        'subtitle': 'Wir unterstützen Sie bei Architektur, Schnittstellen, Integrationen und Automatisierung - inklusive Anbindung unserer KI-Rechnungsverarbeitung an Ihre bestehenden Systeme.',
        'active': '',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">💻 IT CONSULTING</div>
      <h1>IT Consulting & Programming</h1>
      <p class="hero-subtitle">Wir unterstützen Sie bei Architektur, Schnittstellen, Integrationen und Automatisierung - inklusive Anbindung unserer KI-Rechnungsverarbeitung an Ihre bestehenden Systeme.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Unsere IT-Leistungen</h2>
    <p class="section-subtitle">Von der Strategie bis zur Implementierung - wir begleiten Sie auf Ihrem Weg zur digitalen Transformation.</p>

    <div class="feature-grid">
      <div class="feature-card">
        <span class="feature-icon">🏗️</span>
        <h3>Software-Architektur</h3>
        <p>Moderne, skalierbare Architekturen für Ihre Anwendungen - von Microservices bis Cloud-Native.</p>
        <ul>
          <li>Architekturberatung & Design</li>
          <li>Cloud-Migration & Modernisierung</li>
          <li>Performance-Optimierung</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔗</span>
        <h3>API & Schnittstellen</h3>
        <p>Nahtlose Integration in Ihre bestehende IT-Landschaft durch intelligente Schnittstellenkonzepte.</p>
        <ul>
          <li>RESTful & GraphQL APIs</li>
          <li>ERP/CRM-Anbindungen</li>
          <li>Webhook-Integration</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">⚙️</span>
        <h3>Prozessautomatisierung</h3>
        <p>Automatisieren Sie repetitive Aufgaben und gewinnen Sie wertvolle Zeit für strategische Themen.</p>
        <ul>
          <li>Workflow-Automatisierung</li>
          <li>KI-gestützte Prozesse</li>
          <li>Monitoring & Alerting</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🤖</span>
        <h3>KI-Integration</h3>
        <p>Binden Sie unsere KI-Rechnungsverarbeitung nahtlos in Ihre Systeme ein.</p>
        <ul>
          <li>API-basierte Integration</li>
          <li>Custom Workflows</li>
          <li>Datenexport in Ihr ERP</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🛠️</span>
        <h3>Custom Development</h3>
        <p>Individuelle Softwareentwicklung für Ihre spezifischen Anforderungen.</p>
        <ul>
          <li>Python, Java, JavaScript</li>
          <li>Web-Apps & Dashboards</li>
          <li>Datenbank-Design</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔒</span>
        <h3>Security & Compliance</h3>
        <p>Sicherheit von Anfang an - DSGVO-konform und nach Best Practices.</p>
        <ul>
          <li>Security Audits</li>
          <li>DSGVO-Compliance</li>
          <li>Verschlüsselung & Backups</li>
        </ul>
      </div>
    </div>

    <div class="cta-section">
      <h2>Bereit für Ihr IT-Projekt?</h2>
      <p>Lassen Sie uns gemeinsam Ihre Anforderungen besprechen und die beste Lösung für Ihr Unternehmen finden.</p>
      <div style="display: flex; gap: 16px; justify-content: center; flex-wrap: wrap;">
        <a href="/sbshomepage/kontakt.html" class="btn btn-primary">💬 Kontakt aufnehmen</a>
        <a href="/landing" class="btn btn-secondary">🤖 Zur KI-Rechnungsverarbeitung</a>
      </div>
    </div>
  </div>
'''
    },
    
    'sap-consulting.html': {
        'title': 'SAP Consulting & Reporting',
        'description': 'SAP Consulting und Reporting von SBS Deutschland. Integration moderner Lösungen in SAP-Landschaften mit KI-Support.',
        'badge': '📊 SAP CONSULTING',
        'h1': 'SAP Consulting & Reporting',
        'subtitle': 'Wir unterstützen Unternehmen bei der Integration moderner Lösungsansätze in bestehende SAP-Landschaften - besonders im Zusammenspiel mit unserer KI-Rechnungsverarbeitung.',
        'active': '',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">📊 SAP CONSULTING</div>
      <h1>SAP Consulting & Reporting</h1>
      <p class="hero-subtitle">Wir unterstützen Unternehmen bei der Integration moderner Lösungsansätze in bestehende SAP-Landschaften - besonders im Zusammenspiel mit unserer KI-Rechnungsverarbeitung.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Unsere SAP-Schwerpunkte</h2>
    <p class="section-subtitle">Durchgängige, transparente Finanzprozesse durch die Verbindung von SAP-Expertise und KI-Technologie.</p>

    <div class="feature-grid">
      <div class="feature-card">
        <span class="feature-icon">🔗</span>
        <h3>KI-Integration in SAP</h3>
        <p>Nahtlose Anbindung unserer KI-Rechnungsverarbeitung an Ihre SAP-Systeme.</p>
        <ul>
          <li>SAP FI (Finanzwesen) Integration</li>
          <li>SAP MM (Materialwirtschaft) Anbindung</li>
          <li>Automatischer Datenexport nach SAP</li>
          <li>Echtzeit-Synchronisation</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">📈</span>
        <h3>Reporting & Analytics</h3>
        <p>Konzeption und Umsetzung aussagekräftiger Reports rund um Eingangsrechnungen.</p>
        <ul>
          <li>Custom SAP-Reports</li>
          <li>Dashboards & Visualisierungen</li>
          <li>KPI-Tracking & Monitoring</li>
          <li>Automatisierte Auswertungen</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">⚡</span>
        <h3>Workflow-Optimierung</h3>
        <p>Optimierung von Workflows und Freigabeprozessen in Verbindung mit digitalen Belegen.</p>
        <ul>
          <li>Digitale Freigabe-Workflows</li>
          <li>Automatische Kontierung</li>
          <li>Dublettenprüfung</li>
          <li>Eskalationsprozesse</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">✅</span>
        <h3>Compliance & Audit</h3>
        <p>Beratung zu Datenqualität, Compliance und Nachvollziehbarkeit für Audits.</p>
        <ul>
          <li>GoBD-konforme Archivierung</li>
          <li>Audit-Trail & Versionierung</li>
          <li>DSGVO-Compliance</li>
          <li>Revisionssichere Prozesse</li>
        </ul>
      </div>
    </div>

    <div style="margin-top: 100px;">
      <h2 class="section-title">Ihr Mehrwert</h2>
      <div class="feature-grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));">
        <div class="feature-card">
          <span class="feature-icon">💡</span>
          <h3>Prozess-Know-how</h3>
          <p>Tiefes Verständnis für Finanzprozesse und SAP-Strukturen aus langjähriger Praxis.</p>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🚀</span>
          <h3>Schnelle Umsetzung</h3>
          <p>Pragmatische Lösungen, die im Alltag Ihrer Fachabteilungen wirklich funktionieren.</p>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🎯</span>
          <h3>Echte Entlastung</h3>
          <p>Automatisierung repetitiver Aufgaben spart Zeit und reduziert Fehlerquellen.</p>
        </div>
      </div>
    </div>

    <div class="cta-section">
      <h2>SAP + KI = Effiziente Finanzprozesse</h2>
      <p>Durch die Kombination von KI, Prozess-Know-how und SAP-Expertise entstehen Lösungen, die technisch funktionieren und im Alltag entlasten.</p>
      <div style="display: flex; gap: 16px; justify-content: center; flex-wrap: wrap;">
        <a href="/landing" class="btn btn-primary">🤖 Zur KI-Rechnungsverarbeitung</a>
        <a href="/sbshomepage/kontakt.html" class="btn btn-secondary">💬 Beratung anfragen</a>
      </div>
    </div>
  </div>
'''
    },
    
    'quality-risk-management.html': {
        'title': 'Quality & Risk Management',
        'description': 'Quality & Risk Management von SBS Deutschland. Qualitätsstandards, Risikomanagement und Auditfähigkeit für digitale Prozesse.',
        'badge': '🎯 QUALITY & RISK',
        'h1': 'Quality & Risk Management',
        'subtitle': 'Wir unterstützen bei Qualitätsstandards, Risikomanagement, Dokumentation und Auditfähigkeit - insbesondere in digitalen Finanz- und Dokumentenprozessen.',
        'active': '',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">🎯 QUALITY & RISK</div>
      <h1>Quality & Risk Management</h1>
      <p class="hero-subtitle">Wir unterstützen bei Qualitätsstandards, Risikomanagement, Dokumentation und Auditfähigkeit - insbesondere in digitalen Finanz- und Dokumentenprozessen.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Unsere Leistungen</h2>
    <p class="section-subtitle">Qualität und Compliance als Fundament erfolgreicher digitaler Transformation.</p>

    <div class="feature-grid">
      <div class="feature-card">
        <span class="feature-icon">📋</span>
        <h3>Qualitätsmanagement</h3>
        <p>Aufbau und Optimierung von Qualitätsmanagementsystemen für digitale Prozesse.</p>
        <ul>
          <li>ISO 9001 Implementierung</li>
          <li>Prozessdokumentation</li>
          <li>Kontinuierliche Verbesserung (KVP)</li>
          <li>Qualitätskennzahlen & Monitoring</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">⚠️</span>
        <h3>Risikomanagement</h3>
        <p>Identifikation, Bewertung und Steuerung von Risiken in Geschäftsprozessen.</p>
        <ul>
          <li>Risikoanalysen & Assessments</li>
          <li>Risiko-Controlling</li>
          <li>Business Continuity Planning</li>
          <li>Compliance-Management</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">✅</span>
        <h3>Audit-Vorbereitung</h3>
        <p>Sicherstellung der Auditfähigkeit Ihrer digitalen Prozesse und Dokumentationen.</p>
        <ul>
          <li>Interne Audits</li>
          <li>GoBD-Compliance</li>
          <li>Revisionssichere Archivierung</li>
          <li>Audit-Trail & Nachvollziehbarkeit</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">📄</span>
        <h3>Dokumentenmanagement</h3>
        <p>Strukturierte Verwaltung und Archivierung digitaler Dokumente.</p>
        <ul>
          <li>Dokumenten-Workflows</li>
          <li>Versionierung & Freigaben</li>
          <li>Rechtssichere Archivierung</li>
          <li>Automatische Klassifizierung</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔒</span>
        <h3>Datenschutz & Security</h3>
        <p>DSGVO-konforme Gestaltung Ihrer Prozesse und IT-Systeme.</p>
        <ul>
          <li>DSGVO-Compliance</li>
          <li>Datenschutz-Folgenabschätzung</li>
          <li>Security Assessments</li>
          <li>Schulungen & Awareness</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔍</span>
        <h3>KI-Qualitätssicherung</h3>
        <p>Besondere Expertise in der Qualitätssicherung KI-gestützter Prozesse.</p>
        <ul>
          <li>KI-Modell-Validierung</li>
          <li>Accuracy & Performance Testing</li>
          <li>Bias-Detection & Fairness</li>
          <li>Explainability & Transparenz</li>
        </ul>
      </div>
    </div>

    <div class="cta-section">
      <h2>Qualität trifft auf KI-Innovation</h2>
      <p>Unsere Expertise in Quality & Risk Management kombiniert mit modernster KI-Technologie - für sichere, compliant und effiziente Prozesse.</p>
      <div style="display: flex; gap: 16px; justify-content: center; flex-wrap: wrap;">
        <a href="/landing" class="btn btn-primary">🤖 Zur KI-Rechnungsverarbeitung</a>
        <a href="/sbshomepage/kontakt.html" class="btn btn-secondary">💬 Beratung anfragen</a>
      </div>
    </div>
  </div>
'''
    },
    
    'met-pmo.html': {
        'title': 'Metrologie & PMO',
        'description': 'Metrologie und PMO-Services von SBS Deutschland. Messmittelverwaltung und professionelles Projektmanagement für technische Branchen.',
        'badge': '📐 METROLOGIE & PMO',
        'h1': 'Metrologie & PMO',
        'subtitle': 'Neben KI- und IT-Lösungen verfügt die SBS Deutschland GmbH & Co. KG über Erfahrung im Bereich Metrologie und Projektmanagement-Office - insbesondere für technisch anspruchsvolle Branchen.',
        'active': '',
        'content': '''
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">📐 METROLOGIE & PMO</div>
      <h1>Metrologie & PMO</h1>
      <p class="hero-subtitle">Neben KI- und IT-Lösungen verfügt die SBS Deutschland GmbH & Co. KG über Erfahrung im Bereich Metrologie und Projektmanagement-Office - insbesondere für technisch anspruchsvolle Branchen.</p>
    </div>
  </section>

  <div class="main-content">
    <h2 class="section-title">Metrologie</h2>
    <p class="section-subtitle">Transparente Messmittel- und Prüfmittelverwaltung für höchste Qualitätsansprüche.</p>

    <div class="feature-grid">
      <div class="feature-card">
        <span class="feature-icon">📊</span>
        <h3>Messmittelverwaltung</h3>
        <p>Aufbau und Pflege transparenter Messmittel- und Prüfmitteldokumentation.</p>
        <ul>
          <li>Messmittelstammdaten</li>
          <li>Kalibrierungsmanagement</li>
          <li>Prüffristen & Erinnerungen</li>
          <li>MSA (Measurement System Analysis)</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔬</span>
        <h3>Prüfprozesse</h3>
        <p>Definition und Dokumentation von Prüfabläufen und deren Nachweisführung.</p>
        <ul>
          <li>Prüfpläne & Prüfanweisungen</li>
          <li>First Article Inspection (FAI)</li>
          <li>In-Process-Kontrollen</li>
          <li>Endprüfungen & Freigaben</li>
        </ul>
      </div>

      <div class="feature-card">
        <span class="feature-icon">🔗</span>
        <h3>System-Integration</h3>
        <p>Integration relevanter Informationen in bestehende QM-/IT-Systeme.</p>
        <ul>
          <li>CAQ-System-Anbindung</li>
          <li>ERP-Integration</li>
          <li>Automatisierte Datenerfassung</li>
          <li>Digitale Prüfprotokolle</li>
        </ul>
      </div>
    </div>

    <div style="margin-top: 100px;">
      <h2 class="section-title">Projektmanagement-Office (PMO)</h2>
      <p class="section-subtitle">Professionelles Projekt- und Portfoliomanagement für komplexe technische Projekte.</p>

      <div class="feature-grid">
        <div class="feature-card">
          <span class="feature-icon">📅</span>
          <h3>Projektplanung & Steuerung</h3>
          <p>Strukturierte Planung, Steuerung und Monitoring von Projekten.</p>
          <ul>
            <li>Projektpläne & Meilensteine</li>
            <li>Ressourcenplanung</li>
            <li>Risiko- & Changemanagement</li>
            <li>Earned Value Management</li>
          </ul>
        </div>

        <div class="feature-card">
          <span class="feature-icon">👥</span>
          <h3>Stakeholder-Management</h3>
          <p>Aufbau effizienter Kommunikationsstrukturen und Stakeholder-Koordination.</p>
          <ul>
            <li>Stakeholder-Analysen</li>
            <li>Kommunikationspläne</li>
            <li>Meeting-Management</li>
            <li>Eskalationsprozesse</li>
          </ul>
        </div>

        <div class="feature-card">
          <span class="feature-icon">📈</span>
          <h3>Reporting & Governance</h3>
          <p>Standardisierte Reports und Entscheidungsgrundlagen für das Management.</p>
          <ul>
            <li>Management-Dashboards</li>
            <li>Status-Reports & KPIs</li>
            <li>Portfolio-Übersichten</li>
            <li>Project Health Checks</li>
          </ul>
        </div>

        <div class="feature-card">
          <span class="feature-icon">🛠️</span>
          <h3>Methodik & Tools</h3>
          <p>Etablierung von PM-Standards und Einführung passender Tools.</p>
          <ul>
            <li>Agile & klassisches PM</li>
            <li>Tool-Auswahl & Implementierung</li>
            <li>PM-Prozesse & Templates</li>
            <li>PM-Schulungen</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="cta-section">
      <h2>Durchgängige Prozessketten</h2>
      <p>Auf Wunsch verknüpfen wir PMO- und Metrologie-Expertise mit unseren KI- und Rechnungsverarbeitungslösungen - für wirklich durchgängige Prozessketten.</p>
      <div style="display: flex; gap: 16px; justify-content: center; flex-wrap: wrap;">
        <a href="/landing" class="btn btn-primary">🤖 Zur KI-Rechnungsverarbeitung</a>
        <a href="/sbshomepage/kontakt.html" class="btn btn-secondary">💬 Beratung anfragen</a>
      </div>
    </div>
  </div>
'''
    },
}

def generate_page(page_name, page_data):
    """Generiert eine HTML-Seite aus dem Template"""
    active_kontakt = 'class="active"' if page_data['active'] == 'kontakt' else ''
    active_unternehmen = 'class="active"' if page_data['active'] == 'unternehmen' else ''
    
    html = BASE_TEMPLATE.format(
        title=page_data['title'],
        description=page_data['description'],
        content=page_data['content'],
        active_kontakt=active_kontakt,
        active_unternehmen=active_unternehmen
    )
    
    return html

def main():
    base = Path('/var/www/invoice-app/web/sbshomepage')
    
    print("=" * 70)
    print("🎨 PROFESSIONELLES REDESIGN: SBS HOMEPAGE-SEITEN")
    print("=" * 70)
    print()
    print("📄 Zu aktualisierende Seiten:")
    for page_name in PAGES.keys():
        print(f"  • {page_name}")
    print()
    
    updated_count = 0
    
    for page_name, page_data in PAGES.items():
        filepath = base / page_name
        
        # Backup erstellen
        if filepath.exists():
            backup_path = filepath.parent / f"{filepath.stem}.backup_{Path(__file__).stat().st_mtime}"
            import shutil
            shutil.copy2(filepath, backup_path)
        
        # Neue Seite generieren
        html = generate_page(page_name, page_data)
        
        # Schreiben
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ {page_name} aktualisiert")
        updated_count += 1
    
    print()
    print("=" * 70)
    print("✅ REDESIGN ABGESCHLOSSEN")
    print("=" * 70)
    print()
    print(f"📊 Statistik:")
    print(f"   • {updated_count} Seiten neu erstellt")
    print()
    print("🎨 Neue Features:")
    print("   • Einheitlicher Header mit Dark Mode Toggle")
    print("   • Hero-Sections mit Gradient-Background")
    print("   • Icon-Cards für Features")
    print("   • Professionelles, modernes Layout")
    print("   • Moderner Footer (2025)")
    print("   • Fully Responsive")
    print("   • Dark Mode funktioniert überall")
    print()
    print("🧪 Testen:")
    print("   https://sbsdeutschland.com/sbshomepage/kontakt.html")
    print("   https://sbsdeutschland.com/sbshomepage/unternehmen.html")
    print("   https://sbsdeutschland.com/sbshomepage/it-consulting.html")
    print("   https://sbsdeutschland.com/sbshomepage/sap-consulting.html")
    print("   https://sbsdeutschland.com/sbshomepage/quality-risk-management.html")
    print("   https://sbsdeutschland.com/sbshomepage/met-pmo.html")
    print()
    print("💡 Dark Mode testen: Klicke auf das 🌙-Icon in der Navigation!")
    print()

if __name__ == '__main__':
    main()
