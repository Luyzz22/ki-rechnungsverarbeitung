# Deployment-Runbook — FlowCheck / KI-Rechnungsverarbeitung

> Server: `root@207.154.200.239` (DigitalOcean Frankfurt) · App: `/var/www/invoice-app`
> Diese Schritte werden **auf dem Server** ausgeführt (per SSH).

---

## ⚠️ Wichtige Korrekturen zum ursprünglichen Skript

| Im Skript | Problem | Korrekt |
|-----------|---------|---------|
| `git checkout main && git pull origin main` | Die aktuellen Fixes liegen auf Branch **`claude/amazing-brown-rlcXf`**, *noch nicht* auf `main`. Ein Pull von `main` zieht **keine** der Fixes. | Erst Branch nach `main` mergen (PR) **oder** gezielt den Feature-Branch deployen. |
| `from database import init_db; init_db()` | Funktion heißt `init_database` – `init_db` existiert nicht. Außerdem legt `init_database()` allein **nicht** `roles`/`user_roles` an. | `python3 -c "import web.app"` – der App-Import legt **alle** Tabellen an. |
| `ls -la data/*.db`, `data/invoices.db` | DB liegt **nicht** unter `data/`. | `/var/www/invoice-app/invoices.db` (bzw. `$INVOICE_DB_PATH`). |
| `--workers 2` | `processing_jobs` ist **In-Process-RAM**; mit 2 Workern landet Upload/Process ggf. in verschiedenen Prozessen → „job not found“. | **`--workers 1`** verwenden. |
| `CSRF_SECRET`, `DATABASE_URL` | Werden vom Code **nicht** gelesen (CSRF nutzt Session-Token; DB ist SQLite). | Stattdessen Pflicht: `SESSION_SECRET_KEY`, `SECRET_KEY`, `JWT_SECRET`. |

In Produktion (`ENVIRONMENT=production`) **startet die App nicht ohne**
`SESSION_SECRET_KEY` **und** `SECRET_KEY`/`JWT_SECRET` (bewusste Sicherheitsabbruch).

---

## 1. Stand prüfen
```bash
systemctl status invoice-app
cd /var/www/invoice-app && git remote -v && git log --oneline -5 && git status
python3 --version
```
`git remote -v` muss auf `Luyzz22/ki-rechnungsverarbeitung` zeigen. Falls nicht:
```bash
git remote set-url origin https://github.com/Luyzz22/ki-rechnungsverarbeitung.git
```

## 2. Code aktualisieren
```bash
cd /var/www/invoice-app
git stash            # lokale Änderungen sichern (falls vorhanden)
git fetch origin
# Variante A (empfohlen): Feature-Branch nach main mergen (per PR auf GitHub), dann:
git checkout main && git pull origin main
# Variante B (vor dem Merge): direkt den Feature-Branch deployen:
# git checkout claude/amazing-brown-rlcXf && git pull origin claude/amazing-brown-rlcXf
```

## 3. Abhängigkeiten
```bash
# Empfohlen: virtualenv. Falls global installiert wird:
pip3 install -r requirements.txt --break-system-packages
# Falls pdfplumber/cryptography einen RECORD-Konflikt wirft:
#   pip3 install --no-deps pdfplumber pdfminer.six pypdfium2 --break-system-packages
```

## 4. .env prüfen (Pflichtwerte)
```bash
cd /var/www/invoice-app
for k in SESSION_SECRET_KEY SECRET_KEY JWT_SECRET OPENAI_API_KEY ANTHROPIC_API_KEY; do
  grep -q "^$k=" .env && echo "OK  $k gesetzt" || echo "FEHLT $k"
done
# Referenz aller Variablen: cat .env.example
```

## 5. DB initialisieren / migrieren (idempotent)
```bash
cd /var/www/invoice-app
# Import legt fehlende Tabellen/Spalten an (jobs, invoices, users, roles,
# user_roles, audit_events, freigabe_*, approval_* (legacy), export_history,
# zahlungsbedingungen, spend_alerts, retention_policies, export_protocol, ...)
INVOICE_DB_PATH=/var/www/invoice-app/invoices.db python3 -c "import web.app; print('schema ok')"

# Tabellen prüfen:
python3 - <<'PY'
import sqlite3
con = sqlite3.connect("/var/www/invoice-app/invoices.db")
for (t,) in sorted(con.execute("SELECT name FROM sqlite_master WHERE type='table'")):
    print(t)
PY
```

## 6. systemd-Service
`/etc/systemd/system/invoice-app.service` (Workers = 1!):
```ini
[Unit]
Description=FlowCheck AI - KI-Rechnungsverarbeitung
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/invoice-app
EnvironmentFile=/var/www/invoice-app/.env
ExecStart=/usr/local/bin/uvicorn web.app:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable invoice-app && systemctl restart invoice-app
systemctl status invoice-app --no-pager
journalctl -u invoice-app -n 50 --no-pager
```

## 7. Smoke-Test (lokal auf dem Server)
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/health   # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/login         # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/dashboard     # 303 -> /login (nicht eingeloggt)
```

## 8. Nginx
`client_max_body_size` muss zur App passen (Upload-Limit 20 MB):
```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 20M;
}
```
```bash
nginx -t && systemctl reload nginx
```
> HSTS/X-Frame-Options/CSP setzt die App bereits selbst – im Nginx nicht doppeln.

## 9. Health-Cron (optional)
```bash
cat > /var/www/invoice-app/health_check.sh <<'EOF'
#!/bin/bash
S=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health)
[ "$S" != "200" ] && { echo "$(date): DOWN ($S)" >> /var/log/flowcheck-health.log; systemctl restart invoice-app; }
EOF
chmod +x /var/www/invoice-app/health_check.sh
( crontab -l 2>/dev/null; echo "*/5 * * * * /var/www/invoice-app/health_check.sh" ) | crontab -
```
