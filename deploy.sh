#!/usr/bin/env bash
# =============================================================================
# FlowCheck / KI-Rechnungsverarbeitung – Deploy-Helfer (AUF DEM SERVER ausführen)
#
#   sudo bash /var/www/invoice-app/deploy.sh [BRANCH]
#
# Aktualisiert Code, installiert Deps, migriert Schema (idempotent) und startet
# den Dienst neu. Siehe DEPLOY.md für Details (nginx/systemd-Erststeinrichtung).
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/invoice-app}"
BRANCH="${1:-main}"
SERVICE="${SERVICE:-invoice-app}"
DB_PATH="${INVOICE_DB_PATH:-$APP_DIR/invoices.db}"
VENV="${VENV:-$APP_DIR/venv}"

echo "==> App-Verzeichnis: $APP_DIR | Branch: $BRANCH"
cd "$APP_DIR"

echo "==> Remote prüfen"
git remote -v | grep -q "Luyzz22/ki-rechnungsverarbeitung" \
  || echo "WARN: origin zeigt nicht auf Luyzz22 – ggf. 'git remote set-url origin ...'"

echo "==> Code aktualisieren ($BRANCH)"
git stash --include-untracked || true
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# Konsequent das venv des Dienstes verwenden (systemd startet uvicorn aus dem
# venv). System-pip3/python3 würde Deps am Dienst vorbei installieren.
echo "==> Python-venv sicherstellen ($VENV)"
if [ ! -x "$VENV/bin/python" ]; then
  echo "    venv fehlt – erstelle es"
  python3 -m venv "$VENV"
fi
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

echo "==> Abhängigkeiten installieren (venv)"
"$PIP" install --upgrade pip >/dev/null 2>&1 || true
"$PIP" install -r requirements.txt || {
  echo "WARN: pip-Konflikt – versuche PDF-Stack ohne Deps"
  "$PIP" install --no-deps pdfplumber pdfminer.six pypdfium2 || true
}

echo "==> .env Pflichtwerte prüfen"
miss=0
for k in SESSION_SECRET_KEY SECRET_KEY JWT_SECRET; do
  grep -q "^$k=" .env 2>/dev/null && echo "    OK  $k" || { echo "    FEHLT $k"; miss=1; }
done
[ "$miss" = "1" ] && { echo "ABBRUCH: Pflicht-ENV fehlen (App startet sonst nicht)."; exit 1; }

echo "==> Schema migrieren (idempotent, legt fehlende Tabellen/Spalten an)"
INVOICE_DB_PATH="$DB_PATH" "$PY" -c "import web.app; print('schema ok')"

# --- Zum Schluss: Dienst neu starten und Health prüfen -----------------------
echo "==> Dienst neu starten"
systemctl restart "$SERVICE"
sleep 2
systemctl --no-pager --lines=0 status "$SERVICE" || true

echo "==> Smoke-Test"
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || echo "000")
echo "    /api/health -> $code"
[ "$code" = "200" ] && echo "==> Deploy OK" || { echo "==> WARN: Health != 200, journalctl prüfen"; exit 1; }
