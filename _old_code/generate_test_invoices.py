#!/usr/bin/env python3
"""
Generiere 100 Test-Rechnungen mit mehreren Positionen
"""

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import random
from datetime import datetime, timedelta
from pathlib import Path

fake = Faker('de_DE')

# Output Ordner
output_dir = Path("test_rechnungen_100")
output_dir.mkdir(exist_ok=True)

# Firmen-Pool
companies = [
    "Amazon Web Services", "Microsoft Azure", "Google Cloud",
    "Deutsche Telekom", "Vodafone", "1&1", "Strato",
    "Office Depot", "Staples", "Viking Direct",
    "DHL", "UPS", "Hermes", "DPD",
    "Aral", "Shell", "Esso", "Total",
    "Deutsche Bahn", "Lufthansa", "Sixt", "Europcar",
    "REWE", "EDEKA", "Kaufland", "Penny",
    "Media Markt", "Saturn", "Conrad Electronic",
    "Bauhaus", "OBI", "Hornbach", "Toom"
]

def generate_invoice(invoice_num):
    """Generiere eine Rechnung mit mehreren Positionen"""
    
    filename = output_dir / f"Testrechnung_{invoice_num:04d}.pdf"
    c = canvas.Canvas(str(filename), pagesize=A4)
    width, height = A4
    
    # Absender
    company = random.choice(companies)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(3*cm, height - 3*cm, company)
    
    c.setFont("Helvetica", 10)
    c.drawString(3*cm, height - 3.5*cm, fake.street_address())
    c.drawString(3*cm, height - 4*cm, f"{fake.postcode()} {fake.city()}")
    
    # Empfänger
    c.drawString(12*cm, height - 6*cm, "Empfänger:")
    c.drawString(12*cm, height - 6.5*cm, fake.company())
    c.drawString(12*cm, height - 7*cm, fake.street_address())
    c.drawString(12*cm, height - 7.5*cm, f"{fake.postcode()} {fake.city()}")
    
    # Rechnungsdaten
    invoice_date = fake.date_between(start_date='-2y', end_date='today')
    due_date = invoice_date + timedelta(days=random.choice([14, 30, 60]))
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(3*cm, height - 9*cm, f"RECHNUNG")
    
    c.setFont("Helvetica", 10)
    c.drawString(3*cm, height - 10*cm, f"Rechnungsnummer: RE-{invoice_num:06d}")
    c.drawString(3*cm, height - 10.5*cm, f"Rechnungsdatum: {invoice_date.strftime('%d.%m.%Y')}")
    c.drawString(3*cm, height - 11*cm, f"Fälligkeitsdatum: {due_date.strftime('%d.%m.%Y')}")
    c.drawString(3*cm, height - 11.5*cm, f"Kundennummer: KD-{random.randint(10000, 99999)}")
    
    # Positionen (2-8 Positionen)
    num_positions = random.randint(2, 8)
    y_pos = height - 13*cm
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(3*cm, y_pos, "Pos")
    c.drawString(4*cm, y_pos, "Bezeichnung")
    c.drawString(12*cm, y_pos, "Menge")
    c.drawString(14*cm, y_pos, "Einzelpreis")
    c.drawString(17*cm, y_pos, "Betrag")
    
    c.line(3*cm, y_pos - 0.2*cm, 19*cm, y_pos - 0.2*cm)
    
    y_pos -= 0.7*cm
    c.setFont("Helvetica", 9)
    
    positions = []
    total_netto = 0
    
    services = [
        "Software-Lizenz", "Cloud-Hosting", "Support-Stunden", 
        "Beratungsleistung", "Projektmanagement", "Entwicklung",
        "Server-Wartung", "Backup-Service", "Domain-Registrierung",
        "SSL-Zertifikat", "E-Mail-Hosting", "Datenbank-Service",
        "API-Zugriffe", "Storage-Volumen", "Traffic-Gebühren",
        "Office-Material", "Büromöbel", "IT-Hardware",
        "Lizenzen", "Wartungsvertrag", "Schulung"
    ]
    
    for i in range(num_positions):
        service = random.choice(services)
        quantity = random.choice([1, 2, 3, 5, 10, 12, 24])
        unit_price = round(random.uniform(10, 500), 2)
        line_total = quantity * unit_price
        total_netto += line_total
        
        positions.append({
            'pos': i+1,
            'description': service,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': line_total
        })
        
        c.drawString(3*cm, y_pos, str(i+1))
        c.drawString(4*cm, y_pos, service)
        c.drawString(12*cm, y_pos, f"{quantity}")
        c.drawString(14*cm, y_pos, f"{unit_price:.2f} €")
        c.drawString(17*cm, y_pos, f"{line_total:.2f} €")
        
        y_pos -= 0.5*cm
    
    # Summen
    y_pos -= 0.5*cm
    c.line(14*cm, y_pos, 19*cm, y_pos)
    y_pos -= 0.5*cm
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(14*cm, y_pos, "Nettobetrag:")
    c.drawString(17*cm, y_pos, f"{total_netto:.2f} €")
    
    y_pos -= 0.5*cm
    vat_rate = random.choice([0.07, 0.19])  # 7% oder 19%
    vat_amount = total_netto * vat_rate
    
    c.setFont("Helvetica", 10)
    c.drawString(14*cm, y_pos, f"MwSt. {int(vat_rate*100)}%:")
    c.drawString(17*cm, y_pos, f"{vat_amount:.2f} €")
    
    y_pos -= 0.5*cm
    total_brutto = total_netto + vat_amount
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(14*cm, y_pos, "Gesamtbetrag:")
    c.drawString(17*cm, y_pos, f"{total_brutto:.2f} €")
    
    # Bankverbindung
    y_pos -= 2*cm
    c.setFont("Helvetica", 9)
    c.drawString(3*cm, y_pos, "Bankverbindung:")
    c.drawString(3*cm, y_pos - 0.4*cm, f"IBAN: {fake.iban()}")
    c.drawString(3*cm, y_pos - 0.8*cm, f"BIC: {fake.swift()}")
    c.drawString(3*cm, y_pos - 1.2*cm, f"Bank: {fake.company()} Bank")
    
    # USt-ID
    c.drawString(3*cm, y_pos - 1.8*cm, f"USt-IdNr.: DE{random.randint(100000000, 999999999)}")
    
    # Zahlungsbedingungen
    y_pos -= 2.5*cm
    c.drawString(3*cm, y_pos, f"Zahlungsbedingungen: Zahlbar innerhalb von {(due_date - invoice_date).days} Tagen ohne Abzug.")
    
    c.save()
    print(f"✅ Erstellt: {filename.name} ({num_positions} Positionen, {total_brutto:.2f}€)")
    
    return total_brutto

# Generiere 100 Rechnungen
print("🚀 Generiere 100 Test-Rechnungen...\n")

total_sum = 0
for i in range(1, 101):
    amount = generate_invoice(i)
    total_sum += amount

print(f"\n✨ FERTIG!")
print(f"📊 100 Rechnungen erstellt")
print(f"📁 Ordner: {output_dir}")
print(f"💰 Gesamt-Volumen: {total_sum:,.2f}€")
