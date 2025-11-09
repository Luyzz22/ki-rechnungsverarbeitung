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
