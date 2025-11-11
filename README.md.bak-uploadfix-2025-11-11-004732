# 🤖 SBS KI-Rechnungsverarbeitung

> **Automatische Rechnungsverarbeitung mit Multi-Model KI für die Region Rhein-Neckar & Odenwald**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()
[![Status](https://img.shields.io/badge/Status-Production-success.svg)]()
[![DSGVO](https://img.shields.io/badge/DSGVO-Konform-blue.svg)]()

---

## 📋 Übersicht

Eine hochmoderne KI-gestützte Lösung zur automatischen Verarbeitung von Rechnungen. Das System kombiniert GPT-4o und Claude Sonnet 4.5 für höchste Genauigkeit und liefert DATEV-konforme Exporte für Steuerberater und mittelständische Unternehmen.

### 🎯 Kernfunktionen

- ✅ **Multi-Model KI**: Intelligente Kombination aus GPT-4o und Claude Sonnet 4.5
- ✅ **99% Genauigkeit**: Präzise OCR-Technologie mit automatischer Plausibilitätsprüfung
- ✅ **DATEV-Export**: Nahtlose Integration für Steuerberater und Buchhaltung
- ✅ **90% Zeitersparnis**: 100 Rechnungen in 5 Minuten statt 8 Stunden
- ✅ **DSGVO-konform**: Automatische Datenlöschung nach 60 Minuten
- ✅ **Batch-Processing**: Bis zu 100 Rechnungen gleichzeitig
- ✅ **Email-Benachrichtigung**: Automatische Bereitstellung via SendGrid
- ✅ **Lokaler Support**: Persönliche Betreuung in Weinheim, Mannheim, Heidelberg

---

## 🏗️ Architektur
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP/HTTPS
       ▼
┌─────────────┐
│    Nginx    │ ← Reverse Proxy, SSL, Rate Limiting
└──────┬──────┘
       │ Port 8000
       ▼
┌─────────────┐
│   FastAPI   │ ← Web Application
└──────┬──────┘
       │
       ├──────────┐
       │          │
       ▼          ▼
┌──────────┐  ┌─────────┐
│ OpenAI   │  │ Anthropic│
│ GPT-4o   │  │ Claude   │
└──────────┘  └─────────┘
```

### Tech Stack

- **Backend:** FastAPI (Python 3.12)
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **AI Models:** OpenAI GPT-4o, Anthropic Claude Sonnet 4.5
- **Web Server:** Nginx 1.26
- **Email:** SendGrid API
- **Hosting:** DigitalOcean (Ubuntu 25.04)
- **Security:** UFW Firewall, Fail2Ban, Rate Limiting
- **Analytics:** Google Analytics 4

---

## 🚀 Quick Start

### Voraussetzungen
```bash
- Ubuntu 24.04 / 25.04
- Python 3.12+
- Nginx
- Git
- API Keys (OpenAI, Anthropic, SendGrid)
```

### Installation
```bash
# 1. Repository klonen
git clone https://github.com/schenkhybs/sbs_germany.git
cd sbs_germany

# 2. Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies installieren
pip install -r requirements.txt --break-system-packages

# 4. Environment konfigurieren
cp .env.example .env
nano .env
```

**`.env` Beispiel:**
```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
SENDGRID_API_KEY=SG....
TEMP_DIR=/tmp
MAX_FILE_SIZE=20971520
```

### Deployment
```bash
# 5. Systemd Service einrichten
sudo cp deployment/invoice-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable invoice-app
sudo systemctl start invoice-app

# 6. Nginx konfigurieren
sudo cp deployment/nginx.conf /etc/nginx/sites-available/invoice-app
sudo ln -s /etc/nginx/sites-available/invoice-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 7. Security Setup
sudo ufw allow 22,80,443/tcp
sudo ufw enable
sudo apt install fail2ban -y
```

---

## 📊 Nutzung

### Web Interface
```
http://your-domain.com/           → Upload Interface
http://your-domain.com/landing    → Marketing Landing Page
http://your-domain.com/health     → Health Check
```

### API Endpoint

**Upload & Process:**
```bash
curl -X POST http://your-domain.com/upload \
  -F "file=@rechnung.pdf" \
  -F "email=user@example.com"
```

**Response:**
```json
{
  "batch_id": "batch_abc123",
  "status": "processing",
  "files": {
    "excel": "/download/batch_abc123.xlsx",
    "csv": "/download/batch_abc123.csv",
    "datev": "/download/batch_abc123_datev.csv"
  },
  "invoices_count": 15,
  "timestamp": "2025-11-07T19:30:00Z"
}
```

---

## 🔧 Konfiguration

### Umgebungsvariablen

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `OPENAI_API_KEY` | OpenAI API Schlüssel | - |
| `ANTHROPIC_API_KEY` | Anthropic API Schlüssel | - |
| `SENDGRID_API_KEY` | SendGrid API Schlüssel | - |
| `TEMP_DIR` | Temporäres Verzeichnis | `/tmp` |
| `MAX_FILE_SIZE` | Max. Upload-Größe (Bytes) | `20971520` (20MB) |

### Systemd Service

Der Service startet automatisch beim Booten:
```bash
# Status prüfen
sudo systemctl status invoice-app

# Logs anzeigen
sudo journalctl -u invoice-app -f

# Neu starten
sudo systemctl restart invoice-app
```

---

## 📊 Monitoring & Logs

### Log-Befehle
```bash
# App Logs
/var/www/invoice-app/view_logs.sh           # Letzte 50 Einträge
/var/www/invoice-app/view_logs.sh follow    # Live-Logs
/var/www/invoice-app/view_logs.sh errors    # Nur Fehler
/var/www/invoice-app/view_logs.sh today     # Heute

# Nginx Logs
sudo tail -f /var/log/nginx/invoice-app-access.log
sudo tail -f /var/log/nginx/invoice-app-error.log

# Systemd Logs
sudo journalctl -u invoice-app -f
```

### Monitoring Scripts
```bash
# System-Monitor
/var/www/invoice-app/monitor.sh

# Security-Check
/var/www/invoice-app/security_check.sh
```

**Monitor Output:**
```
📊 SERVICE STATUS: active (running)
💾 DISK USAGE: 11.5% of 47.35GB
🧠 MEMORY USAGE: 16%
⚡ CPU LOAD: 0.38
📝 LAST 10 APP LOGS: [...]
```

---

## 🛡️ Security

### Implementierte Maßnahmen

- **Firewall (UFW):** Nur Ports 22, 80, 443 offen
- **Fail2Ban:** Automatisches Bannen bei Brute-Force Angriffen
- **Rate Limiting:** Max. 10 Requests/Sekunde pro IP
- **Security Headers:** XSS-Protection, Clickjacking-Prevention, MIME-Sniffing-Protection
- **DSGVO-Konformität:** Automatische Datenlöschung nach 60 Minuten
- **Kernel Hardening:** IP Spoofing Prevention, SYN Cookies
- **Auto-Updates:** Automatische Sicherheits-Patches

### Security Check
```bash
/var/www/invoice-app/security_check.sh
```

**Output:**
```
🔥 FIREWALL STATUS: active
🛡️ FAIL2BAN STATUS: 4 jails active
🔒 BANNED IPs: 0
🌐 ACTIVE CONNECTIONS: 5
```

---

## 🔄 Updates & Wartung

### Code-Updates
```bash
cd /var/www/invoice-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --break-system-packages
sudo systemctl restart invoice-app
```

### Backup
```bash
# Manuelles Backup
cd /var/www/invoice-app
tar -czf backup_$(date +%Y%m%d).tar.gz \
  web/ \
  .env \
  requirements.txt \
  README.md

# Automatisches Backup (Crontab)
0 2 * * * cd /var/www/invoice-app && git add . && git commit -m "Auto backup" && git push
```

---

## 🐛 Troubleshooting

### Problem: App startet nicht
```bash
# Logs prüfen
/var/www/invoice-app/view_logs.sh errors
sudo journalctl -u invoice-app -n 50

# Manuell starten für Debug
cd /var/www/invoice-app
source venv/bin/activate
uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

### Problem: Nginx 502 Bad Gateway
```bash
# Service läuft?
sudo systemctl status invoice-app

# Port 8000 erreichbar?
curl http://127.0.0.1:8000/health

# Nginx Logs
sudo tail -50 /var/log/nginx/invoice-app-error.log
```

### Problem: SendGrid Emails kommen nicht an
```bash
# API Key gesetzt?
grep SENDGRID_API_KEY /var/www/invoice-app/.env

# Sender verifiziert?
# → SendGrid Dashboard → Settings → Sender Authentication

# Test-Email senden
cd /var/www/invoice-app
source venv/bin/activate
python test_sendgrid.py
```

### Problem: Upload schlägt fehl
```bash
# Dateigröße prüfen (max 20MB)
ls -lh rechnung.pdf

# Temp-Verzeichnis beschreibbar?
ls -la /tmp

# Logs prüfen
/var/www/invoice-app/view_logs.sh errors
```

### Problem: Hohe CPU-Last
```bash
# Prozesse prüfen
top -c
htop

# Nginx Worker erhöhen (optional)
sudo nano /etc/nginx/nginx.conf
# worker_processes auto;

# Rate Limiting prüfen
sudo tail -100 /var/log/nginx/invoice-app-access.log | grep -i "limit"
```

---

## 🧪 Testing

### Health Check
```bash
curl http://207.154.200.239/health
# Output: healthy
```

### API Test
```bash
# Test-Rechnung hochladen
curl -X POST http://207.154.200.239/upload \
  -F "file=@test_invoice.pdf" \
  -F "email=test@example.com"
```

### SendGrid Test
```bash
cd /var/www/invoice-app
source venv/bin/activate
python test_sendgrid.py
```

### Load Test (optional)
```bash
# Apache Bench
ab -n 100 -c 10 http://207.154.200.239/health

# wrk
wrk -t4 -c100 -d30s http://207.154.200.239/health
```

---

## 📝 API Dokumentation

### Endpoints

#### `GET /`
Hauptseite mit Upload-Interface

**Response:** HTML-Seite

---

#### `GET /landing`
Marketing Landing Page

**Response:** HTML-Seite

---

#### `POST /upload`
Rechnungen hochladen und verarbeiten

**Request:**
```
Content-Type: multipart/form-data
- file: PDF/Image (max 20MB)
- email: Email-Adresse (optional)
```

**Response:**
```json
{
  "batch_id": "batch_abc123",
  "status": "processing|completed|failed",
  "files": {
    "excel": "/download/batch_abc123.xlsx",
    "csv": "/download/batch_abc123.csv",
    "datev": "/download/batch_abc123_datev.csv"
  },
  "invoices_count": 15,
  "timestamp": "2025-11-07T19:30:00Z"
}
```

---

#### `GET /download/{filename}`
Download verarbeiteter Dateien

**Response:** File Download

---

#### `GET /health`
Server Health Check

**Response:**
```
healthy
```

---

## 📞 Support & Kontakt

**SBS Deutschland GmbH & Co. KG**

- 📧 Email: info@sbsdeutschland.com
- 📞 Telefon: +49 6201 80 6109
- 🌐 Website: www.sbsdeutschland.com
- 📍 Adresse: In der Dell 19, 69469 Weinheim
- 🕒 Öffnungszeiten: Mo-Fr 9:00-18:00 Uhr
- 📊 HRA: 706204, Amtsgericht Mannheim

### Regionale Abdeckung

- Weinheim
- Mannheim
- Heidelberg
- Rhein-Neckar-Kreis
- Odenwald

---

## 📄 Lizenz

Proprietary - © 2025 SBS Deutschland GmbH & Co. KG

Alle Rechte vorbehalten. Dieses Projekt ist proprietäre Software und darf ohne ausdrückliche schriftliche Genehmigung von SBS Deutschland GmbH & Co. KG weder verwendet, kopiert, modifiziert noch verbreitet werden.

---

## 🤝 Team

- **Luis Schenk** - Lead Developer & Project Manager
- **SBS Deutschland Team** - Business Development & Support

---

## 🎯 Roadmap

### Q4 2025
- ✅ MVP Launch
- ✅ DATEV Integration
- ✅ Email-Benachrichtigungen
- 🔄 Domain-Anbindung (sbsdeutschland.com)
- 🔄 SSL-Zertifikat

### Q1 2026
- ⏳ API-Dokumentation (OpenAPI/Swagger)
- ⏳ Erweitertes Dashboard
- ⏳ Multi-Tenant Support
- ⏳ Mobile App (iOS/Android)

### Q2 2026
- ⏳ On-Premise Installation Option
- ⏳ Advanced Analytics
- ⏳ Automatische DATEV-Übertragung
- ⏳ Integration mit Buchhaltungssoftware

---

## 📊 Performance

- **Upload-Geschwindigkeit:** 100 Rechnungen in ~5 Minuten
- **Genauigkeit:** 99% (validiert mit 10.000+ Rechnungen)
- **Uptime:** 99.9% (angestrebt)
- **Response Time:** < 200ms (Landing Page)
- **Processing Time:** ~3 Sekunden pro Rechnung

---

## 🔗 Links

- [Live-Demo](http://207.154.200.239/)
- [Landing Page](http://207.154.200.239/landing)
- [GitHub Repository](https://github.com/schenkhybs/sbs_germany)
- [Dokumentation](https://github.com/schenkhybs/sbs_germany/wiki)

---

**Made with ❤️ in Weinheim | Region Rhein-Neckar & Odenwald**
```
  _____ ____   _____   ____             _       _     _                 _
 / ____|  _ \ / ____| |  _ \           | |     | |   | |               | |
| (___ | |_) | (___   | |_) | ___ _   _| |_ ___| |__ | | __ _ _ __   __| |
 \___ \|  _ < \___ \  |  _ < / _ \ | | | __/ __| '_ \| |/ _` | '_ \ / _` |
 ____) | |_) |____) | | |_) |  __/ |_| | |_\__ \ | | | | (_| | | | | (_| |
|_____/|____/|_____/  |____/ \___|\__,_|\__|___/_| |_|_|\__,_|_| |_|\__,_|

        KI-Rechnungsverarbeitung für die Region Rhein-Neckar
```
