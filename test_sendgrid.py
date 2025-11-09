from sendgrid_mailer import send_test_email

# DEINE EMAIL:
test_email = "luis.schenk05@gmail.com"

print(f"📧 Sende Test-Email an {test_email}...")
success = send_test_email(test_email)

if success:
    print("✅ SUCCESS! Check deine Inbox!")
else:
    print("❌ Fehler!")
