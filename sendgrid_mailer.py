import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = 'info@sbsdeutschland.com'

def send_invoice_notification(to_email, batch_id, file_paths):
    """
    Sendet Benachrichtigung über fertige Rechnungsverarbeitung
    
    Args:
        to_email: Empfänger-Email
        batch_id: Batch ID
        file_paths: Dict mit Pfaden zu Excel/CSV/DATEV Dateien
    """
    try:
        subject = f"✅ Rechnungsverarbeitung abgeschlossen - Batch {batch_id}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #003856; color: white; padding: 30px; text-align: center;">
                <h1>🎉 Verarbeitung abgeschlossen!</h1>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa;">
                <p>Ihre Rechnungen wurden erfolgreich verarbeitet.</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #003856;">Batch-ID: {batch_id}</h3>
                    <p>Die verarbeiteten Dateien finden Sie im Anhang:</p>
                    <ul>
                        <li>📊 Excel-Export (.xlsx)</li>
                        <li>📄 CSV-Export (.csv)</li>
                        <li>💼 DATEV-Export (.csv)</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px; text-align: center;">
                    <a href="http://207.154.200.239/" 
                       style="background: #FFB900; color: #003856; padding: 15px 30px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                        Weitere Rechnungen verarbeiten
                    </a>
                </p>
            </div>
            
            <div style="background: #003856; color: white; padding: 20px; text-align: center; font-size: 0.9em;">
                <p><strong>SBS Deutschland GmbH & Co. KG</strong></p>
                <p>In der Dell 19 | 69469 Weinheim</p>
                <p>📞 +49 6201 80 6109 | ✉ info@sbsdeutschland.com</p>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        # Attachments hinzufügen
        for file_type, file_path in file_paths.items():
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    encoded_file = base64.b64encode(file_data).decode()
                    
                    attachment = Attachment(
                        FileContent(encoded_file),
                        FileName(os.path.basename(file_path)),
                        FileType('application/octet-stream'),
                        Disposition('attachment')
                    )
                    message.add_attachment(attachment)
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ Email gesendet an {to_email} - Status: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"❌ Email-Fehler: {str(e)}")
        return False


def send_test_email(to_email):
    """Test-Email senden"""
    try:
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject='🧪 Test von SBS Rechnungsverarbeitung',
            html_content='''
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #003856; color: white; padding: 30px; text-align: center;">
                    <h1>✅ SendGrid funktioniert!</h1>
                </div>
                <div style="padding: 30px; background: #f8f9fa;">
                    <p style="font-size: 1.2em;">Die Email-Integration ist erfolgreich eingerichtet.</p>
                    <p>SBS Deutschland ist bereit, Benachrichtigungen zu versenden! 🚀</p>
                </div>
                <div style="background: #003856; color: white; padding: 20px; text-align: center; font-size: 0.9em;">
                    <p>SBS Deutschland GmbH & Co. KG</p>
                </div>
            </body>
            </html>
            '''
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ Test-Email gesendet! Status: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {str(e)}")
        return False


def send_subscription_email(to_email, user_name, product, plan, billing_cycle, amount_cents):
    """
    Sendet Abo-Bestätigung nach erfolgreichem Checkout
    
    Args:
        to_email: Empfänger-Email
        user_name: Name des Kunden
        product: 'invoice', 'contract', oder 'bundle'
        plan: 'starter', 'professional', 'enterprise'
        billing_cycle: 'monthly' oder 'yearly'
        amount_cents: Betrag in Cent
    """
    try:
        product_names = {
            "invoice": "KI-Rechnungsverarbeitung",
            "contract": "KI-Vertragsanalyse", 
            "bundle": "SBS Bundle (Rechnungen + Verträge)"
        }
        
        plan_names = {
            "starter": "Starter",
            "professional": "Professional",
            "enterprise": "Enterprise"
        }
        
        billing_text = "monatlich" if billing_cycle == "monthly" else "jährlich"
        amount_eur = amount_cents / 100
        
        product_display = product_names.get(product, product)
        plan_display = plan_names.get(plan, plan)
        
        # Rechnungsnummer generieren
        import datetime
        invoice_nr = f"SBS-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        invoice_date = datetime.datetime.now().strftime('%d.%m.%Y')
        
        subject = f"🎉 Willkommen bei SBS Deutschland - Ihre Abo-Bestätigung"
        
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 0 auto; background: #f4f7fa;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #003856 0%, #00507a 100%); color: white; padding: 40px 30px; text-align: center;">
                <div style="font-size: 2.5em; margin-bottom: 10px;">🏢</div>
                <h1 style="margin: 0; font-size: 1.8em;">Willkommen bei SBS Deutschland!</h1>
                <p style="margin: 10px 0 0; opacity: 0.9;">Ihr Abonnement ist jetzt aktiv</p>
            </div>
            
            <!-- Hauptinhalt -->
            <div style="background: white; padding: 40px 30px;">
                <p style="font-size: 1.1em; color: #333;">Hallo {user_name or 'Kunde'},</p>
                
                <p style="color: #555; line-height: 1.6;">
                    vielen Dank für Ihr Vertrauen! Ihr Abonnement wurde erfolgreich aktiviert. 
                    Sie können ab sofort alle Funktionen nutzen.
                </p>
                
                <!-- Abo-Details Box -->
                <div style="background: #f8f9fa; border-radius: 12px; padding: 25px; margin: 30px 0; border-left: 4px solid #FFB900;">
                    <h3 style="margin: 0 0 20px; color: #003856; font-size: 1.1em;">📋 Ihre Abo-Details</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #666;">Produkt:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #333;">{product_display}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666;">Plan:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #333;">{plan_display}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #666;">Abrechnungszyklus:</td>
                            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #333;">{billing_text}</td>
                        </tr>
                        <tr style="border-top: 1px solid #e0e0e0;">
                            <td style="padding: 15px 0 8px; color: #666; font-weight: 600;">Betrag:</td>
                            <td style="padding: 15px 0 8px; text-align: right; font-weight: 700; color: #003856; font-size: 1.3em;">€{amount_eur:.2f}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Rechnungsinfo -->
                <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin: 25px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                        <span style="color: #666; font-size: 0.9em;">Rechnungsnummer:</span>
                        <span style="font-weight: 600; color: #333;">{invoice_nr}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666; font-size: 0.9em;">Rechnungsdatum:</span>
                        <span style="font-weight: 600; color: #333;">{invoice_date}</span>
                    </div>
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="https://app.sbsdeutschland.com/dashboard" 
                       style="background: linear-gradient(135deg, #FFB900 0%, #e5a600 100%); 
                              color: #003856; 
                              padding: 16px 40px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: 700; 
                              font-size: 1.1em;
                              display: inline-block;
                              box-shadow: 0 4px 15px rgba(255,185,0,0.3);">
                        Jetzt loslegen →
                    </a>
                </div>
                
                <!-- Hilfe-Box -->
                <div style="background: #f0f9ff; border-radius: 8px; padding: 20px; margin-top: 30px;">
                    <p style="margin: 0; color: #0369a1; font-size: 0.95em;">
                        <strong>💡 Tipp:</strong> Laden Sie Ihre ersten Rechnungen hoch und erleben Sie, 
                        wie unsere KI sie in Sekunden verarbeitet!
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #003856; color: white; padding: 30px; text-align: center;">
                <p style="margin: 0 0 10px; font-weight: 600;">SBS Deutschland GmbH & Co. KG</p>
                <p style="margin: 0; font-size: 0.9em; opacity: 0.8;">
                    In der Dell 19 | 69469 Weinheim<br>
                    📞 +49 6201 80 6109 | ✉️ info@sbsdeutschland.com
                </p>
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                    <a href="https://sbsdeutschland.com/sbshomepage/impressum.html" style="color: rgba(255,255,255,0.7); text-decoration: none; font-size: 0.8em; margin: 0 10px;">Impressum</a>
                    <a href="https://sbsdeutschland.com/sbshomepage/datenschutz.html" style="color: rgba(255,255,255,0.7); text-decoration: none; font-size: 0.8em; margin: 0 10px;">Datenschutz</a>
                    <a href="https://sbsdeutschland.com/sbshomepage/agb.html" style="color: rgba(255,255,255,0.7); text-decoration: none; font-size: 0.8em; margin: 0 10px;">AGB</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ Abo-Bestätigung gesendet an {to_email} - Status: {response.status_code}")
        return True
        
    except Exception as e:
        print(f"❌ Abo-Email-Fehler: {str(e)}")
        return False
