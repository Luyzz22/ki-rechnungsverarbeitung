#!/usr/bin/env python3
"""
Neue, moderne Landing Page für KI-Rechnungsverarbeitung
Alle Infos, aber komplett neues Design
"""

from pathlib import Path

LANDING_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KI-Rechnungsverarbeitung – SBS Deutschland</title>
  <meta name="description" content="Automatisierte Rechnungsverarbeitung mit KI aus Weinheim. DSGVO-konform, Multi-Model KI, DATEV-Export. Rechnungen in Sekunden verarbeiten.">
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
      max-width: 1200px;
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
      font-size: 3.5rem;
      font-weight: 800;
      color: white;
      line-height: 1.15;
      margin-bottom: 20px;
      letter-spacing: -0.02em;
    }

    .hero-subtitle {
      font-size: 1.35rem;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 40px;
      max-width: 700px;
      line-height: 1.6;
    }

    .hero-cta-group {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
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

    /* ================================================
       FEATURES SECTION
       ================================================ */
    .features {
      padding: 80px 24px;
      background: var(--sbs-bg);
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
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

    .section-description {
      font-size: 1.15rem;
      color: var(--sbs-muted);
      max-width: 700px;
      margin: 0 auto;
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 32px;
    }

    .feature-card {
      background: var(--sbs-white);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 2px 20px rgba(0,0,0,0.05);
      transition: var(--transition);
      border: 1px solid rgba(0,0,0,0.05);
    }

    .feature-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 40px rgba(0,0,0,0.1);
    }

    .feature-icon {
      font-size: 2.5rem;
      margin-bottom: 20px;
      display: block;
    }

    .feature-title {
      font-size: 1.35rem;
      font-weight: 600;
      color: var(--sbs-dark);
      margin-bottom: 12px;
    }

    .feature-description {
      color: var(--sbs-muted);
      line-height: 1.7;
    }

    /* ================================================
       PROCESS SECTION
       ================================================ */
    .process {
      padding: 80px 24px;
      background: var(--sbs-white);
    }

    .process-steps {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 40px;
      margin-top: 60px;
    }

    .process-step {
      position: relative;
      text-align: center;
    }

    .step-number {
      width: 60px;
      height: 60px;
      background: var(--sbs-gradient);
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      font-weight: 700;
      margin: 0 auto 20px;
      box-shadow: 0 4px 20px rgba(0,56,86,0.2);
    }

    .step-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--sbs-dark);
      margin-bottom: 12px;
    }

    .step-description {
      color: var(--sbs-muted);
      line-height: 1.6;
    }

    /* ================================================
       BENEFITS SECTION
       ================================================ */
    .benefits {
      padding: 80px 24px;
      background: var(--sbs-bg);
    }

    .benefits-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
      margin-top: 60px;
    }

    .benefit-item {
      display: flex;
      gap: 16px;
      padding: 24px;
      background: var(--sbs-white);
      border-radius: 12px;
      transition: var(--transition);
    }

    .benefit-item:hover {
      transform: translateX(4px);
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    .benefit-icon {
      flex-shrink: 0;
      width: 32px;
      height: 32px;
      background: rgba(255, 180, 0, 0.15);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
    }

    .benefit-text {
      flex: 1;
    }

    .benefit-text strong {
      display: block;
      color: var(--sbs-dark);
      font-weight: 600;
      margin-bottom: 4px;
    }

    .benefit-text span {
      color: var(--sbs-muted);
      font-size: 0.95rem;
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
      
      .hero h1 { font-size: 2.25rem; }
      .hero-subtitle { font-size: 1.1rem; }
      .section-title { font-size: 2rem; }
      .cta-section h2 { font-size: 2rem; }
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
        <a href="/landing" class="active">KI-Rechnungsverarbeitung</a>
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

  <!-- HERO SECTION -->
  <section class="hero">
    <div class="hero-content">
      <div class="hero-badge">
        📍 KI-GESTÜTZTE RECHNUNGSVERARBEITUNG AUS DER RHEIN-NECKAR-REGION
      </div>
      
      <h1>Rechnungen verarbeiten<br>in Sekunden</h1>
      
      <p class="hero-subtitle">
        Mit KI, entwickelt & betrieben von SBS Deutschland aus Weinheim. Automatisierte Erkennung, 
        Validierung und Übergabe Ihrer Eingangsrechnungen – sicher, DSGVO-konform und optimiert 
        für Steuerkanzleien, Buchhaltungen und mittelständische Unternehmen.
      </p>
      
      <div class="hero-cta-group">
        <a href="https://app.sbsdeutschland.com/" class="btn btn-primary">
          🚀 Kostenlos testen
        </a>
        <a href="#features" class="btn btn-secondary">
          📖 Mehr erfahren
        </a>
      </div>
    </div>
  </section>

  <!-- FEATURES -->
  <section class="features" id="features">
    <div class="container">
      <div class="section-header">
        <span class="section-badge">WARUM UNSERE KI-LÖSUNG?</span>
        <h2 class="section-title">Intelligente Automatisierung für Ihre Buchhaltung</h2>
        <p class="section-description">
          Upload mehrerer Rechnungen & automatische Verarbeitung. Valider Export für DATEV, Excel & FiBu-Systeme.
        </p>
      </div>
      
      <div class="features-grid">
        <div class="feature-card">
          <span class="feature-icon">🤖</span>
          <h3 class="feature-title">Multi-Model KI</h3>
          <p class="feature-description">
            Kombination mehrerer KI-Modelle für höchste Genauigkeit. Automatische Erkennung von 
            Rechnungsnummer, Beträgen, Lieferanten und Steuersätzen.
          </p>
        </div>
        
        <div class="feature-card">
          <span class="feature-icon">🔒</span>
          <h3 class="feature-title">DSGVO & Hosting in Deutschland</h3>
          <p class="feature-description">
            Alle Daten bleiben in Deutschland. Vollständige DSGVO-Konformität. Keine Übermittlung 
            an Drittländer. Ihre Sicherheit ist unsere Priorität.
          </p>
        </div>
        
        <div class="feature-card">
          <span class="feature-icon">💾</span>
          <h3 class="feature-title">DATEV-, CSV- & ERP-Export</h3>
          <p class="feature-description">
            Direkt exportierbar in DATEV, Excel, CSV oder FiBu-Systeme. Nahtlose Integration in 
            Ihre bestehenden Buchhaltungsprozesse.
          </p>
        </div>
        
        <div class="feature-card">
          <span class="feature-icon">✅</span>
          <h3 class="feature-title">Prüfung von Pflichtangaben & Plausibilität</h3>
          <p class="feature-description">
            Automatische Validierung auf Vollständigkeit und Plausibilität. Warnung bei fehlenden 
            Pflichtangaben oder Unstimmigkeiten.
          </p>
        </div>
        
        <div class="feature-card">
          <span class="feature-icon">⚡</span>
          <h3 class="feature-title">99% Genauigkeit</h3>
          <p class="feature-description">
            Durch Multi-Model-KI erreichen wir eine Erkennungsgenauigkeit von über 99%. 
            Weniger Nacharbeit, mehr Zeit für wichtige Aufgaben.
          </p>
        </div>
        
        <div class="feature-card">
          <span class="feature-icon">📍</span>
          <h3 class="feature-title">Regional verankert in Weinheim</h3>
          <p class="feature-description">
            Infrastruktur & Support durch SBS Deutschland (Weinheim). Persönliche Ansprechpartner, 
            deutschsprachiger Support und kurze Wege.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- PROCESS -->
  <section class="process">
    <div class="container">
      <div class="section-header">
        <span class="section-badge">SO FUNKTIONIERT'S</span>
        <h2 class="section-title">In 3 Schritten zur verarbeiteten Rechnung</h2>
        <p class="section-description">
          Einfach, schnell und vollständig automatisiert. Keine manuelle Dateneingabe mehr nötig.
        </p>
      </div>
      
      <div class="process-steps">
        <div class="process-step">
          <div class="step-number">1</div>
          <h3 class="step-title">PDF hochladen</h3>
          <p class="step-description">
            Laden Sie Ihre Rechnungen als PDF hoch. Mehrere Dateien gleichzeitig möglich. 
            Drag & Drop oder Auswahl aus Ordner.
          </p>
        </div>
        
        <div class="process-step">
          <div class="step-number">2</div>
          <h3 class="step-title">KI-Verarbeitung</h3>
          <p class="step-description">
            Unsere KI extrahiert automatisch alle relevanten Daten: Rechnungsnummer, Beträge, 
            Steuersätze, Lieferant und mehr. In Sekunden.
          </p>
        </div>
        
        <div class="process-step">
          <div class="step-number">3</div>
          <h3 class="step-title">Export & Fertig</h3>
          <p class="step-description">
            Exportieren Sie die Daten direkt in DATEV, Excel oder Ihr FiBu-System. 
            Strukturiert, validiert und ready to use.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- BENEFITS -->
  <section class="benefits">
    <div class="container">
      <div class="section-header">
        <span class="section-badge">IHRE VORTEILE</span>
        <h2 class="section-title">Mehr Zeit für das Wesentliche</h2>
      </div>
      
      <div class="benefits-grid">
        <div class="benefit-item">
          <div class="benefit-icon">⏱️</div>
          <div class="benefit-text">
            <strong>Zeit sparen</strong>
            <span>Bis zu 80% Zeitersparnis bei der Rechnungserfassung</span>
          </div>
        </div>
        
        <div class="benefit-item">
          <div class="benefit-icon">💰</div>
          <div class="benefit-text">
            <strong>Kosten senken</strong>
            <span>Weniger manuelle Arbeit = geringere Personalkosten</span>
          </div>
        </div>
        
        <div class="benefit-item">
          <div class="benefit-icon">🎯</div>
          <div class="benefit-text">
            <strong>Fehler minimieren</strong>
            <span>KI macht weniger Fehler als manuelle Eingabe</span>
          </div>
        </div>
        
        <div class="benefit-item">
          <div class="benefit-icon">📊</div>
          <div class="benefit-text">
            <strong>Transparenz</strong>
            <span>Vollständiger Überblick über alle Rechnungen</span>
          </div>
        </div>
        
        <div class="benefit-item">
          <div class="benefit-icon">🔄</div>
          <div class="benefit-text">
            <strong>Skalierbar</strong>
            <span>Von 10 bis 10.000 Rechnungen pro Monat</span>
          </div>
        </div>
        
        <div class="benefit-item">
          <div class="benefit-icon">🛡️</div>
          <div class="benefit-text">
            <strong>Sicher & DSGVO-konform</strong>
            <span>Deutsche Server, höchste Datenschutzstandards</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-section">
    <div class="cta-content">
      <h2>Bereit für automatisierte Rechnungsverarbeitung?</h2>
      <p>
        Starten Sie jetzt kostenlos und überzeugen Sie sich selbst. 
        Keine Kreditkarte erforderlich. Keine versteckten Kosten.
      </p>
      <div class="hero-cta-group" style="justify-content: center;">
        <a href="https://app.sbsdeutschland.com/" class="btn btn-primary" style="box-shadow: 0 8px 30px rgba(0,0,0,0.25);">
          🚀 Jetzt kostenlos testen
        </a>
        <a href="/sbshomepage/kontakt.html" class="btn btn-secondary">
          💬 Mit uns sprechen
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
    landing_path = Path('/var/www/invoice-app/web/static/landing/index.html')
    
    # Backup erstellen
    if landing_path.exists():
        import shutil
        backup = landing_path.parent / 'index.html.backup'
        shutil.copy(landing_path, backup)
        print(f"📦 Backup erstellt: {backup}")
    
    # Neue Landing Page speichern
    with open(landing_path, 'w', encoding='utf-8') as f:
        f.write(LANDING_HTML)
    
    print()
    print("=" * 70)
    print("🎨 NEUE LANDING PAGE ERSTELLT!")
    print("=" * 70)
    print()
    print("✅ Features:")
    print("  • Modernes, responsives Design")
    print("  • Alle Infos erhalten")
    print("  • Dark Mode funktioniert")
    print("  • Optimiert für Conversions")
    print()
    print("🧪 TESTEN:")
    print("  https://sbsdeutschland.com/landing")
    print()
    print("📝 BACKUP:")
    print("  Falls du die alte Version willst:")
    print("  mv /var/www/invoice-app/web/static/landing/index.html.backup index.html")
    print()

if __name__ == '__main__':
    main()
