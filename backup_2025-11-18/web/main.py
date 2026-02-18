#!/usr/bin/env python3
"""
Erstellt ein professionelles Kontaktformular mit Backend
- Dropdown für Dienstleistungen
- Modern & Clean Design
- FastAPI Backend zum E-Mail-Versand
- Success/Error States
"""

from pathlib import Path

# HTML für das Kontaktformular (wird in kontakt.html eingefügt)
CONTACT_FORM_HTML = '''
    <div style="margin-top: 80px;">
      <h2 class="section-title">Nachricht senden</h2>
      <p class="section-subtitle">Füllen Sie das Formular aus und wir melden uns innerhalb von 24 Stunden bei Ihnen.</p>

      <div class="contact-form-container">
        <form id="contact-form" class="contact-form">
          <!-- Dienstleistung -->
          <div class="form-group">
            <label for="service">Interessiert an *</label>
            <select id="service" name="service" required>
              <option value="">Bitte wählen...</option>
              <option value="ki-rechnungsverarbeitung">🤖 KI-Rechnungsverarbeitung</option>
              <option value="it-consulting">💻 IT Consulting & Programming</option>
              <option value="sap-consulting">📊 SAP Consulting & Reporting</option>
              <option value="quality-risk">🎯 Quality & Risk Management</option>
              <option value="metrologie-pmo">📐 Metrologie & PMO</option>
              <option value="andere">💬 Allgemeine Anfrage</option>
            </select>
          </div>

          <!-- Name & E-Mail (2-spaltig) -->
          <div class="form-row">
            <div class="form-group">
              <label for="name">Name *</label>
              <input type="text" id="name" name="name" placeholder="Max Mustermann" required>
            </div>

            <div class="form-group">
              <label for="email">E-Mail *</label>
              <input type="email" id="email" name="email" placeholder="max@beispiel.de" required>
            </div>
          </div>

          <!-- Telefon & Unternehmen (2-spaltig, optional) -->
          <div class="form-row">
            <div class="form-group">
              <label for="phone">Telefon (optional)</label>
              <input type="tel" id="phone" name="phone" placeholder="+49 123 456789">
            </div>

            <div class="form-group">
              <label for="company">Unternehmen (optional)</label>
              <input type="text" id="company" name="company" placeholder="Firma GmbH">
            </div>
          </div>

          <!-- Nachricht -->
          <div class="form-group">
            <label for="message">Ihre Nachricht *</label>
            <textarea id="message" name="message" rows="6" placeholder="Beschreiben Sie Ihr Anliegen..." required></textarea>
          </div>

          <!-- Datenschutz -->
          <div class="form-group-checkbox">
            <input type="checkbox" id="privacy" name="privacy" required>
            <label for="privacy">
              Ich habe die <a href="/sbshomepage/datenschutz.html" target="_blank">Datenschutzerklärung</a> gelesen und akzeptiere diese. *
            </label>
          </div>

          <!-- Submit Button -->
          <button type="submit" class="btn btn-primary btn-submit" id="submit-btn">
            <span class="btn-text">Nachricht senden</span>
            <span class="btn-loading" style="display: none;">
              <span class="spinner"></span> Wird gesendet...
            </span>
          </button>

          <!-- Status Messages -->
          <div id="form-success" class="form-message form-success" style="display: none;">
            ✅ Vielen Dank! Ihre Nachricht wurde erfolgreich versendet. Wir melden uns innerhalb von 24 Stunden bei Ihnen.
          </div>

          <div id="form-error" class="form-message form-error" style="display: none;">
            ❌ Leider ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut oder kontaktieren Sie uns direkt per E-Mail.
          </div>
        </form>
      </div>
    </div>

    <style>
      .contact-form-container {
        max-width: 700px;
        margin: 0 auto;
        background: var(--sbs-white);
        padding: 48px;
        border-radius: 20px;
        box-shadow: 0 4px 30px rgba(0,0,0,0.08);
      }

      .contact-form {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
      }

      .form-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .form-group label {
        font-weight: 600;
        color: var(--sbs-dark);
        font-size: 0.95rem;
      }

      .form-group input,
      .form-group select,
      .form-group textarea {
        padding: 12px 16px;
        border: 2px solid rgba(0, 56, 86, 0.15);
        border-radius: 10px;
        font-size: 1rem;
        font-family: inherit;
        background: var(--sbs-bg);
        color: var(--sbs-text);
        transition: all 0.3s ease;
      }

      .form-group input:focus,
      .form-group select:focus,
      .form-group textarea:focus {
        outline: none;
        border-color: var(--sbs-accent);
        box-shadow: 0 0 0 3px rgba(255, 180, 0, 0.1);
      }

      .form-group select {
        cursor: pointer;
        appearance: none;
        background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L6 6L11 1' stroke='%23003856' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 16px center;
        padding-right: 48px;
      }

      .form-group textarea {
        resize: vertical;
        min-height: 120px;
      }

      .form-group-checkbox {
        display: flex;
        align-items: flex-start;
        gap: 12px;
      }

      .form-group-checkbox input[type="checkbox"] {
        margin-top: 4px;
        width: 20px;
        height: 20px;
        cursor: pointer;
        flex-shrink: 0;
      }

      .form-group-checkbox label {
        font-size: 0.9rem;
        color: var(--sbs-muted);
        line-height: 1.6;
        cursor: pointer;
      }

      .form-group-checkbox label a {
        color: var(--sbs-accent);
        text-decoration: none;
      }

      .form-group-checkbox label a:hover {
        text-decoration: underline;
      }

      .btn-submit {
        width: 100%;
        margin-top: 8px;
        position: relative;
      }

      .btn-submit:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .btn-loading {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid rgba(0,0,0,0.1);
        border-top-color: #111827;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }

      @keyframes spin {
        to { transform: rotate(360deg); }
      }

      .form-message {
        padding: 16px 20px;
        border-radius: 10px;
        font-weight: 500;
        line-height: 1.6;
        margin-top: 8px;
      }

      .form-success {
        background: rgba(16, 185, 129, 0.1);
        border: 2px solid rgba(16, 185, 129, 0.3);
        color: #059669;
      }

      .form-error {
        background: rgba(239, 68, 68, 0.1);
        border: 2px solid rgba(239, 68, 68, 0.3);
        color: #dc2626;
      }

      @media (max-width: 768px) {
        .contact-form-container {
          padding: 32px 24px;
        }

        .form-row {
          grid-template-columns: 1fr;
        }
      }
    </style>

    <script>
    (function() {
      const form = document.getElementById('contact-form');
      const submitBtn = document.getElementById('submit-btn');
      const btnText = submitBtn.querySelector('.btn-text');
      const btnLoading = submitBtn.querySelector('.btn-loading');
      const successMsg = document.getElementById('form-success');
      const errorMsg = document.getElementById('form-error');

      form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Hide previous messages
        successMsg.style.display = 'none';
        errorMsg.style.display = 'none';

        // Show loading state
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'flex';

        // Get form data
        const formData = new FormData(form);
        const data = {
          service: formData.get('service'),
          name: formData.get('name'),
          email: formData.get('email'),
          phone: formData.get('phone') || '',
          company: formData.get('company') || '',
          message: formData.get('message'),
          privacy: formData.get('privacy') === 'on'
        };

        try {
          const response = await fetch('/api/contact', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
          });

          if (response.ok) {
            // Success
            successMsg.style.display = 'block';
            form.reset();
            
            // Scroll to success message
            successMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } else {
            // Error
            throw new Error('Server error');
          }
        } catch (error) {
          console.error('Error:', error);
          errorMsg.style.display = 'block';
          errorMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } finally {
          // Reset button state
          submitBtn.disabled = false;
          btnText.style.display = 'inline';
          btnLoading.style.display = 'none';
        }
      });
    })();
    </script>'''

# FastAPI Backend Code
BACKEND_CODE = '''
# In main.py (FastAPI) einfügen:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# Router erstellen
contact_router = APIRouter()

class ContactForm(BaseModel):
    service: str
    name: str
    email: EmailStr
    phone: str = ""
    company: str = ""
    message: str
    privacy: bool

@contact_router.post("/api/contact")
async def submit_contact_form(form: ContactForm):
    """Verarbeitet Kontaktformular und sendet E-Mail"""
    
    # Service-Namen mapping
    service_names = {
        "ki-rechnungsverarbeitung": "🤖 KI-Rechnungsverarbeitung",
        "it-consulting": "💻 IT Consulting & Programming",
        "sap-consulting": "📊 SAP Consulting & Reporting",
        "quality-risk": "🎯 Quality & Risk Management",
        "metrologie-pmo": "📐 Metrologie & PMO",
        "andere": "💬 Allgemeine Anfrage"
    }
    
    # E-Mail zusammenstellen
    subject = f"Neue Kontaktanfrage: {service_names.get(form.service, form.service)}"
    
    body = f"""
Neue Kontaktanfrage über sbsdeutschland.com

Dienstleistung: {service_names.get(form.service, form.service)}
Datum: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}

--- KONTAKTDATEN ---
Name: {form.name}
E-Mail: {form.email}
Telefon: {form.phone if form.phone else "Nicht angegeben"}
Unternehmen: {form.company if form.company else "Nicht angegeben"}

--- NACHRICHT ---
{form.message}

--- DATENSCHUTZ ---
Datenschutzerklärung akzeptiert: {"Ja" if form.privacy else "Nein"}

---
Diese E-Mail wurde automatisch generiert von sbsdeutschland.com/sbshomepage/kontakt.html
    """
    
    try:
        # E-Mail senden (Gmail SMTP - anpassen an deine Config)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")  # z.B. "info@sbsdeutschland.com"
        smtp_password = os.getenv("SMTP_PASSWORD")  # App-Passwort
        recipient = os.getenv("CONTACT_EMAIL", "info@sbsdeutschland.com")
        
        # Erstelle E-Mail
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Reply-To'] = form.email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Sende E-Mail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        # Optional: Bestätigungs-E-Mail an Absender
        confirmation_body = f"""
Guten Tag {form.name},

vielen Dank für Ihre Anfrage zu {service_names.get(form.service, form.service)}.

Wir haben Ihre Nachricht erhalten und werden uns innerhalb von 24 Stunden bei Ihnen melden.

Mit freundlichen Grüßen
Ihr Team von SBS Deutschland

---
SBS Deutschland GmbH & Co. KG
In der Dell 19
69469 Weinheim
Tel: +49 6201 80 6109
Web: www.sbsdeutschland.com
        """
        
        confirmation_msg = MIMEMultipart()
        confirmation_msg['From'] = smtp_user
        confirmation_msg['To'] = form.email
        confirmation_msg['Subject'] = "Ihre Anfrage bei SBS Deutschland"
        confirmation_msg.attach(MIMEText(confirmation_body, 'plain', 'utf-8'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(confirmation_msg)
        
        return {"status": "success", "message": "E-Mail erfolgreich versendet"}
    
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Versenden der E-Mail")

# In main.py einbinden:
# app.include_router(contact_router)
'''

# Aktualisierte kontakt.html mit Formular
def create_contact_page_with_form():
    return '''<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kontakt | SBS Deutschland</title>
  <meta name="description" content="Nehmen Sie Kontakt mit SBS Deutschland auf. Wir beraten Sie gerne zu KI-Rechnungsverarbeitung und unseren Consulting-Dienstleistungen.">
  <link rel="icon" href="/static/favicon.ico">
  
  <style>
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

    /* HEADER */
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

    /* HERO */
    .hero {
      background: var(--sbs-gradient);
      padding: 80px 24px;
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
      max-width: 900px;
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
      font-size: 1.2rem;
      color: rgba(255, 255, 255, 0.9);
      line-height: 1.6;
      max-width: 700px;
      margin: 0 auto;
    }

    /* MAIN CONTENT */
    .main-content {
      max-width: 1200px;
      margin: 0 auto;
      padding: 80px 24px;
    }

    .section-title {
      font-size: 2.2rem;
      font-weight: 800;
      color: var(--sbs-dark);
      margin-bottom: 16px;
      text-align: center;
      letter-spacing: -0.02em;
    }

    .section-subtitle {
      font-size: 1.1rem;
      color: var(--sbs-muted);
      text-align: center;
      margin-bottom: 60px;
      max-width: 700px;
      margin-left: auto;
      margin-right: auto;
    }

    /* CONTACT CARDS */
    .contact-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 32px;
      margin-top: 48px;
    }

    .contact-card {
      background: var(--sbs-white);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.06);
      text-align: center;
    }

    .contact-card .icon {
      font-size: 3rem;
      margin-bottom: 16px;
      display: block;
    }

    .contact-card h3 {
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--sbs-dark);
      margin-bottom: 8px;
    }

    .contact-card p {
      color: var(--sbs-muted);
      margin-bottom: 8px;
    }

    .contact-card a {
      color: var(--sbs-accent);
      text-decoration: none;
      font-weight: 600;
    }

    .contact-card a:hover {
      text-decoration: underline;
    }

    /* CTA */
    .cta-section {
      background: var(--sbs-gradient);
      padding: 80px 24px;
      text-align: center;
      border-radius: 20px;
      margin: 80px 0;
    }

    .cta-section h2 {
      font-size: 2.5rem;
      font-weight: 800;
      color: white;
      margin-bottom: 16px;
    }

    .cta-section p {
      font-size: 1.2rem;
      color: rgba(255, 255, 255, 0.9);
      margin-bottom: 32px;
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
    }

    .btn-primary {
      background: var(--sbs-accent);
      color: #111827;
      box-shadow: 0 4px 20px rgba(255,180,0,0.3);
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(255,180,0,0.4);
    }

    /* FOOTER */
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

    /* RESPONSIVE */
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
      .section-title { font-size: 1.8rem; }
      .cta-section h2 { font-size: 2rem; }
      
      .contact-grid {
        grid-template-columns: 1fr;
      }

      .footer-content {
        grid-template-columns: 1fr;
        gap: 32px;
      }

      .footer-bottom {
        flex-direction: column;
        text-align: center;
      }
    }
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
        <a href="/sbshomepage/unternehmen.html">Über uns</a>
        <a href="/sbshomepage/kontakt.html" class="active">Kontakt</a>
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
        <p><a href="tel:+496201806109">+49 6201 80 6109</a></p>
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

''' + CONTACT_FORM_HTML + '''

    <div class="cta-section" style="margin-top: 80px;">
      <h2>Testen Sie unsere KI-Rechnungsverarbeitung</h2>
      <p>Für Produkt-Demos nutzen Sie gerne unser interaktives Formular und die Kontaktmöglichkeiten auf unserer KI-Seite.</p>
      <a href="/landing#demo" class="btn btn-primary">🚀 Zur Demo</a>
    </div>
  </div>

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
    print("=" * 70)
    print("📧 KONTAKTFORMULAR MIT BACKEND ERSTELLEN")
    print("=" * 70)
    print()
    
    # 1. Erstelle neue kontakt.html mit Formular
    contact_page = Path('/var/www/invoice-app/web/sbshomepage/kontakt.html')
    html = create_contact_page_with_form()
    
    # Backup erstellen
    if contact_page.exists():
        import shutil
        backup = contact_page.parent / f"{contact_page.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(contact_page, backup)
        print(f"💾 Backup erstellt: {backup.name}")
    
    # Schreiben
    with open(contact_page, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ kontakt.html aktualisiert")
    print()
    
    # 2. Backend-Code anzeigen
    print("=" * 70)
    print("📝 BACKEND-CODE (FastAPI)")
    print("=" * 70)
    print()
    print("Füge folgenden Code in deine FastAPI main.py ein:")
    print()
    print(BACKEND_CODE)
    print()
    
    print("=" * 70)
    print("✅ KONTAKTFORMULAR ERSTELLT")
    print("=" * 70)
    print()
    print("📋 Features:")
    print("   • Dropdown für Dienstleistungen")
    print("   • Name, E-Mail, Telefon, Unternehmen, Nachricht")
    print("   • Datenschutz-Checkbox")
    print("   • Loading-States & Success/Error Messages")
    print("   • Responsive Design")
    print("   • Dark Mode Support")
    print()
    print("🔧 Backend Setup:")
    print("   1. Füge den Code oben in main.py ein")
    print("   2. Setze ENV-Variablen:")
    print("      SMTP_SERVER=smtp.gmail.com")
    print("      SMTP_PORT=587")
    print("      SMTP_USER=info@sbsdeutschland.com")
    print("      SMTP_PASSWORD=<dein-app-passwort>")
    print("      CONTACT_EMAIL=info@sbsdeutschland.com")
    print()
    print("🧪 Testen:")
    print("   https://sbsdeutschland.com/sbshomepage/kontakt.html")
    print()
    print("💡 Das Formular sendet Daten an /api/contact")
    print()

if __name__ == '__main__':
    main()
