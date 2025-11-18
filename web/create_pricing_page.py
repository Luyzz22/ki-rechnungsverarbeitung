#!/usr/bin/env python3
"""
Preisseite für KI-Rechnungsverarbeitung
3 Pricing Tiers: Starter, Professional, Enterprise
"""

from pathlib import Path

PRICING_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preise – KI-Rechnungsverarbeitung | SBS Deutschland</title>
  <meta name="description" content="Transparente Preise für KI-Rechnungsverarbeitung. Von 50 bis unbegrenzt Rechnungen pro Monat. DSGVO-konform, Made in Germany.">
  <link rel="icon" href="/static/favicon.ico">
  
  <style>
    /* ================================================
       VARIABLES & RESET
       ================================================ */
    :root {
      --sbs-bg: #f5f6f8;
      --sbs-white: #ffffff;
      --sbs-dark: #003856;
      --sbs-dark-soft: #0b2435;
      --sbs-accent: #ffb400;
      --sbs-text: #17212b;
      --sbs-muted: #6b7280;
      --sbs-gradient: linear-gradient(135deg, #003856 0%, #005a8a 100%);
      --transition: all 0.3s ease;
    }
    
    [data-theme="dark"] {
      --sbs-bg: #0f172a;
      --sbs-white: #1e293b;
      --sbs-dark: #60a5fa;
      --sbs-dark-soft: #e2e8f0;
      --sbs-text: #e2e8f0;
      --sbs-muted: #94a3b8;
      --sbs-gradient: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--sbs-bg);
      color: var(--sbs-text);
      line-height: 1.6;
      transition: background 0.3s ease, color 0.3s ease;
    }

    /* ================================================
       HEADER (aus unified design)
       ================================================ */
    .sbs-header {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: var(--sbs-white);
      box-shadow: 0 1px 12px rgba(15,23,42,0.06);
      transition: var(--transition);
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
      transition: var(--transition);
    }

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
      transition: var(--transition);
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

    .dark-mode-toggle {
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
    }

    .dark-mode-toggle:hover {
      border-color: var(--sbs-accent);
      transform: scale(1.05);
    }

    .sun-icon, .moon-icon {
      font-size: 14px;
      transition: var(--transition);
    }

    [data-theme="dark"] .sun-icon { opacity: 0.3; }
    [data-theme="light"] .moon-icon { opacity: 0.3; }

    /* ================================================
       HERO SECTION
       ================================================ */
    .hero {
      background: var(--sbs-gradient);
      padding: 80px 24px 100px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }

    .hero::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
      opacity: 0.4;
    }

    .hero-content {
      max-width: 800px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }

    .hero-badge {
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
    }

    .hero h1 {
      font-size: 3rem;
      font-weight: 800;
      color: white;
      line-height: 1.2;
      margin-bottom: 20px;
      letter-spacing: -0.02em;
    }

    .hero-subtitle {
      font-size: 1.25rem;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 16px;
      line-height: 1.6;
    }

    /* ================================================
       PRICING SECTION
       ================================================ */
    .pricing {
      padding: 80px 24px;
      background: var(--sbs-bg);
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
    }

    .pricing-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 32px;
      margin-top: 60px;
    }

    .pricing-card {
      background: var(--sbs-white);
      border-radius: 20px;
      padding: 40px 32px;
      box-shadow: 0 4px 30px rgba(0,0,0,0.08);
      transition: var(--transition);
      border: 2px solid transparent;
      position: relative;
      overflow: hidden;
    }

    .pricing-card:hover {
      transform: translateY(-8px);
      box-shadow: 0 12px 50px rgba(0,0,0,0.15);
    }

    .pricing-card.featured {
      border-color: var(--sbs-accent);
      box-shadow: 0 8px 40px rgba(255,180,0,0.2);
    }

    .pricing-card.featured::before {
      content: 'BELIEBT';
      position: absolute;
      top: 20px;
      right: -35px;
      background: var(--sbs-accent);
      color: #111827;
      padding: 6px 50px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      transform: rotate(45deg);
      box-shadow: 0 4px 12px rgba(255,180,0,0.3);
    }

    .plan-name {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--sbs-dark);
      margin-bottom: 12px;
    }

    .plan-description {
      color: var(--sbs-muted);
      margin-bottom: 24px;
      font-size: 0.95rem;
    }

    .plan-price {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
    }

    .price-amount {
      font-size: 3rem;
      font-weight: 800;
      color: var(--sbs-dark);
      line-height: 1;
    }

    .price-currency {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--sbs-muted);
    }

    .price-period {
      font-size: 1rem;
      color: var(--sbs-muted);
    }

    .price-note {
      font-size: 0.85rem;
      color: var(--sbs-muted);
      margin-bottom: 32px;
    }

    .plan-features {
      list-style: none;
      margin-bottom: 32px;
    }

    .plan-features li {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid rgba(0,0,0,0.05);
    }

    .plan-features li:last-child {
      border-bottom: none;
    }

    .feature-icon {
      flex-shrink: 0;
      width: 20px;
      height: 20px;
      background: rgba(255,180,0,0.15);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      margin-top: 2px;
    }

    .feature-icon.check {
      color: #10b981;
    }

    .feature-icon.cross {
      opacity: 0.3;
    }

    .plan-cta {
      display: block;
      width: 100%;
      padding: 16px 32px;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      text-align: center;
      text-decoration: none;
      transition: var(--transition);
      cursor: pointer;
      border: 2px solid var(--sbs-dark);
      background: transparent;
      color: var(--sbs-dark);
    }

    .plan-cta:hover {
      background: var(--sbs-dark);
      color: white;
      transform: translateY(-2px);
    }

    .pricing-card.featured .plan-cta {
      background: var(--sbs-accent);
      color: #111827;
      border-color: var(--sbs-accent);
      box-shadow: 0 4px 20px rgba(255,180,0,0.3);
    }

    .pricing-card.featured .plan-cta:hover {
      box-shadow: 0 8px 30px rgba(255,180,0,0.4);
      transform: translateY(-2px);
    }

    /* ================================================
       FAQ SECTION
       ================================================ */
    .faq {
      padding: 80px 24px;
      background: var(--sbs-white);
    }

    .section-header {
      text-align: center;
      margin-bottom: 60px;
    }

    .section-badge {
      display: inline-block;
      padding: 8px 16px;
      background: rgba(255, 180, 0, 0.1);
      color: var(--sbs-accent);
      border-radius: 999px;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 16px;
    }

    .section-title {
      font-size: 2.5rem;
      font-weight: 700;
      color: var(--sbs-dark);
      margin-bottom: 16px;
    }

    .faq-list {
      max-width: 800px;
      margin: 0 auto;
    }

    .faq-item {
      background: var(--sbs-bg);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 16px;
      transition: var(--transition);
    }

    .faq-item:hover {
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    .faq-question {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--sbs-dark);
      margin-bottom: 12px;
    }

    .faq-answer {
      color: var(--sbs-muted);
      line-height: 1.7;
    }

    /* ================================================
       CTA SECTION
       ================================================ */
    .cta-section {
      padding: 100px 24px;
      background: var(--sbs-gradient);
      text-align: center;
      position: relative;
      overflow: hidden;
    }

    .cta-section::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
      opacity: 0.3;
    }

    .cta-content {
      max-width: 800px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }

    .cta-section h2 {
      font-size: 2.75rem;
      font-weight: 800;
      color: white;
      margin-bottom: 20px;
      line-height: 1.2;
    }

    .cta-section p {
      font-size: 1.25rem;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 40px;
    }

    .btn {
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
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }

    .btn-primary {
      background: var(--sbs-accent);
      color: #111827;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(255,180,0,0.4);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(10px);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.25);
      transform: translateY(-2px);
    }

    .hero-cta-group {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      justify-content: center;
    }

    /* ================================================
       FOOTER
       ================================================ */
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
      transition: var(--transition);
    }

    #sbs-footer-global a:hover {
      opacity: 1;
      color: var(--sbs-accent);
    }

    /* ================================================
       RESPONSIVE
       ================================================ */
    @media (max-width: 768px) {
      .burger-menu { display: flex; }
      
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
      }
      
      .sbs-nav.active { right: 0; }
      
      .hero h1 { font-size: 2rem; }
      .section-title { font-size: 2rem; }
      .cta-section h2 { font-size: 2rem; }
      
      .pricing-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>

  <!-- HEADER -->
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
        <a href="/sbshomepage/">Startseite</a>
        <a href="/landing">KI-Rechnungsverarbeitung</a>
        <a href="/preise" class="active">Preise</a>
        <a href="/sbshomepage/unternehmen.html">Über uns</a>
        <a href="/sbshomepage/kontakt.html">Kontakt</a>
        <a href="https://app.sbsdeutschland.com/" class="sbs-nav-cta">Upload / Demo</a>
        
        <button class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <span class="sun-icon">☀️</span>
          <span class="moon-icon">🌙</span>
        </button>
      </nav>
    </div>
  </header>

  <!-- HERO -->
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">
        💰 TRANSPARENTE PREISE
      </div>
      
      <h1>Faire Preise für jede Unternehmensgröße</h1>
      
      <p class="hero-subtitle">
        Von Einzelunternehmen bis zum Konzern. Keine versteckten Kosten. 
        Jederzeit kündbar. 30 Tage Geld-zurück-Garantie.
      </p>
    </div>
  </section>

  <!-- PRICING -->
  <section class="pricing">
    <div class="container">
      <div class="pricing-grid">
        
        <!-- STARTER -->
        <div class="pricing-card">
          <h3 class="plan-name">Starter</h3>
          <p class="plan-description">Perfekt für kleine Unternehmen und Freiberufler</p>
          
          <div class="plan-price">
            <span class="price-amount">49</span>
            <span class="price-currency">€</span>
          </div>
          <p class="price-period">pro Monat</p>
          <p class="price-note">zzgl. MwSt.</p>
          
          <ul class="plan-features">
            <li>
              <span class="feature-icon check">✓</span>
              <span><strong>Bis zu 50 Rechnungen/Monat</strong></span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Multi-Model KI-Verarbeitung</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>DATEV & CSV Export</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>DSGVO-konform & Deutschland-Hosting</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>E-Mail Support</span>
            </li>
            <li>
              <span class="feature-icon cross">✗</span>
              <span style="opacity: 0.5;">API-Zugang</span>
            </li>
            <li>
              <span class="feature-icon cross">✗</span>
              <span style="opacity: 0.5;">Priority Support</span>
            </li>
          </ul>
          
          <a href="https://app.sbsdeutschland.com/" class="plan-cta">Jetzt starten</a>
        </div>

        <!-- PROFESSIONAL (Featured) -->
        <div class="pricing-card featured">
          <h3 class="plan-name">Professional</h3>
          <p class="plan-description">Ideal für wachsende Unternehmen und Steuerkanzleien</p>
          
          <div class="plan-price">
            <span class="price-amount">149</span>
            <span class="price-currency">€</span>
          </div>
          <p class="price-period">pro Monat</p>
          <p class="price-note">zzgl. MwSt.</p>
          
          <ul class="plan-features">
            <li>
              <span class="feature-icon check">✓</span>
              <span><strong>Bis zu 300 Rechnungen/Monat</strong></span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Multi-Model KI-Verarbeitung</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>DATEV, CSV & Excel Export</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>DSGVO-konform & Deutschland-Hosting</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>API-Zugang für Integrationen</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Priority E-Mail & Chat Support</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Monatliche Reports & Analytics</span>
            </li>
          </ul>
          
          <a href="https://app.sbsdeutschland.com/" class="plan-cta">Jetzt starten</a>
        </div>

        <!-- ENTERPRISE -->
        <div class="pricing-card">
          <h3 class="plan-name">Enterprise</h3>
          <p class="plan-description">Für große Unternehmen mit individuellen Anforderungen</p>
          
          <div class="plan-price">
            <span class="price-amount" style="font-size: 2.25rem;">Individuell</span>
          </div>
          <p class="price-period">auf Anfrage</p>
          <p class="price-note">Maßgeschneiderte Lösungen</p>
          
          <ul class="plan-features">
            <li>
              <span class="feature-icon check">✓</span>
              <span><strong>Unbegrenzte Rechnungen</strong></span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Multi-Model KI + Custom Models</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Alle Export-Formate + Custom</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Dedicated Server & VPN</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Full API + Webhooks</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>24/7 Premium Support + Telefon</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>Persönlicher Account Manager</span>
            </li>
            <li>
              <span class="feature-icon check">✓</span>
              <span>SLA-Garantien & Custom Training</span>
            </li>
          </ul>
          
          <a href="/sbshomepage/kontakt.html" class="plan-cta">Kontakt aufnehmen</a>
        </div>

      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="faq">
    <div class="container">
      <div class="section-header">
        <span class="section-badge">HÄUFIGE FRAGEN</span>
        <h2 class="section-title">Fragen zu den Preisen?</h2>
      </div>
      
      <div class="faq-list">
        <div class="faq-item">
          <h3 class="faq-question">Was passiert, wenn ich mehr Rechnungen verarbeiten möchte?</h3>
          <p class="faq-answer">
            Kein Problem! Sie können jederzeit auf einen höheren Plan upgraden. Zusätzliche Rechnungen 
            können auch einzeln hinzugebucht werden: Starter +2€/Rechnung, Professional +1€/Rechnung.
          </p>
        </div>
        
        <div class="faq-item">
          <h3 class="faq-question">Gibt es eine Vertragsbindung?</h3>
          <p class="faq-answer">
            Nein, alle Pläne sind monatlich kündbar. Sie haben volle Flexibilität und können jederzeit 
            upgraden, downgraden oder kündigen.
          </p>
        </div>
        
        <div class="faq-item">
          <h3 class="faq-question">Kann ich den Service vorab testen?</h3>
          <p class="faq-answer">
            Ja! Wir bieten eine 30-tägige Geld-zurück-Garantie. Außerdem können Sie mit unserem 
            kostenlosen Demo-Zugang die KI-Verarbeitung ohne Anmeldung testen.
          </p>
        </div>
        
        <div class="faq-item">
          <h3 class="faq-question">Welche Zahlungsmethoden werden akzeptiert?</h3>
          <p class="faq-answer">
            Wir akzeptieren Kreditkarte, Lastschrift (SEPA), PayPal und Rechnung (ab Professional). 
            Für Enterprise-Kunden sind auch individuelle Zahlungsbedingungen möglich.
          </p>
        </div>
        
        <div class="faq-item">
          <h3 class="faq-question">Wie sicher sind meine Daten?</h3>
          <p class="faq-answer">
            Höchste Sicherheit! Alle Daten werden ausschließlich in Deutschland gehostet, SSL-verschlüsselt 
            übertragen und DSGVO-konform verarbeitet. Keine Weitergabe an Dritte.
          </p>
        </div>
        
        <div class="faq-item">
          <h3 class="faq-question">Bekomme ich Support auf Deutsch?</h3>
          <p class="faq-answer">
            Ja! Unser gesamtes Team sitzt in Weinheim und bietet deutschsprachigen Support per E-Mail, 
            Chat und Telefon (je nach Plan). Persönlich, kompetent und schnell.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-section">
    <div class="cta-content">
      <h2>Bereit zum Start?</h2>
      <p>
        Wählen Sie Ihren Plan und automatisieren Sie Ihre Rechnungsverarbeitung noch heute. 
        30 Tage Geld-zurück-Garantie. Keine Kreditkarte für den Test erforderlich.
      </p>
      <div class="hero-cta-group">
        <a href="https://app.sbsdeutschland.com/" class="btn btn-primary" style="box-shadow: 0 8px 30px rgba(0,0,0,0.25);">
          🚀 Jetzt kostenlos testen
        </a>
        <a href="/sbshomepage/kontakt.html" class="btn btn-secondary">
          💬 Beratung anfragen
        </a>
      </div>
    </div>
  </section>

  <!-- FOOTER -->
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
  </footer>

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
  </script>

</body>
</html>'''

def main():
    # Preisseite im static Ordner erstellen
    pricing_path = Path('/var/www/invoice-app/web/static/preise')
    pricing_path.mkdir(exist_ok=True)
    
    pricing_file = pricing_path / 'index.html'
    
    with open(pricing_file, 'w', encoding='utf-8') as f:
        f.write(PRICING_HTML)
    
    print("=" * 70)
    print("💰 PREISSEITE ERSTELLT!")
    print("=" * 70)
    print()
    print("✅ Erstellt: /static/preise/index.html")
    print()
    print("📊 3 PRICING TIERS:")
    print("  • Starter: 49€/Monat (50 Rechnungen)")
    print("  • Professional: 149€/Monat (300 Rechnungen) - BELIEBT")
    print("  • Enterprise: Individuell (unbegrenzt)")
    print()
    print("🎨 FEATURES:")
    print("  • Modernes Card-Design")
    print("  • 'Beliebt'-Badge auf Professional")
    print("  • FAQ-Section")
    print("  • Dark Mode Support")
    print("  • Responsive")
    print()
    print("🧪 TESTEN:")
    print("  https://sbsdeutschland.com/preise")
    print()
    print("📝 NÄCHSTER SCHRITT:")
    print("  Preise in Hauptnavigation einbinden (alle Seiten)")
    print()

if __name__ == '__main__':
    main()
