#!/usr/bin/env bash
# =============================================================================
# FlowCheck / KI-Rechnungsverarbeitung – Deploy-Helfer (AUF DEM SERVER ausführen)
#
#   sudo bash /var/www/invoice-app/deploy.sh [BRANCH]
#
# Aktualisiert Code, installiert Deps ins venv des Dienstes, migriert das Schema
# (idempotent) und startet den Dienst neu. Siehe DEPLOY.md für Details.
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/invoice-app}"
BRANCH="${1:-main}"
SERVICE="${SERVICE:-invoice-app}"
DB_PATH="${INVOICE_DB_PATH:-$APP_DIR/invoices.db}"
VENV="${VENV:-$APP_DIR/venv}"

cd "$APP_DIR"

# --- Phase 1: Code deterministisch auf origin/$BRANCH bringen, dann re-exec ---
# Wichtig: deploy.sh aktualisiert sich im Update selbst. Läuft danach dieselbe
# bash-Instanz weiter, führt sie u. U. VERALTETE Bytes dieses Scripts aus – das
# ließ zuvor weiter System-pip/-python statt des venv laufen. Deshalb nach dem
# Update EINMAL die frische Fassung neu ausführen (Guard verhindert Endlosschleife).
if [ "${DEPLOY_REEXEC:-0}" != "1" ]; then
  echo "==> App-Verzeichnis: $APP_DIR | Branch: $BRANCH"
  git remote -v | grep -q "Luyzz22/ki-rechnungsverarbeitung" \
    || echo "WARN: origin zeigt nicht auf Luyzz22 – ggf. 'git remote set-url origin ...'"

  echo "==> Code aktualisieren – harter Reset auf origin/$BRANCH (kein Stash)"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH" 2>/dev/null || git checkout -B "$BRANCH" "origin/$BRANCH"
  # Server-Handedits an versionierten Dateien werden bewusst verworfen (das Repo
  # ist die Quelle der Wahrheit). venv/.env/invoices.db sind untracked/ignored
  # und bleiben durch reset --hard unangetastet.
  git reset --hard "origin/$BRANCH"

  echo "==> Frische deploy.sh-Fassung übernehmen (re-exec)"
  DEPLOY_REEXEC=1 exec bash "$APP_DIR/deploy.sh" "$BRANCH"
fi

# --- Ab hier läuft GARANTIERT die frisch gezogene Script-Fassung -------------
echo "==> Python-venv sicherstellen ($VENV)"
if [ ! -x "$VENV/bin/python" ]; then
  echo "    venv fehlt – erstelle es"
  python3 -m venv "$VENV"
fi
PY="$VENV/bin/python"

echo "==> Abhängigkeiten installieren (venv: $PY)"
# Immer 'python -m pip' des venv verwenden – nie system pip3.
"$PY" -m pip install --upgrade pip >/dev/null 2>&1 || true
if ! "$PY" -m pip install -r requirements.txt; then
  echo "WARN: pip-Konflikt bei requirements.txt – versuche PDF-Stack ohne Deps"
  "$PY" -m pip install --no-deps pdfplumber pdfminer.six pypdfium2 || true
fi

# Harte Vorbedingung: ohne fastapi startet der Dienst nicht. Klar abbrechen,
# statt später mit ModuleNotFoundError im Migrationsschritt zu scheitern.
if ! "$PY" -c "import fastapi" 2>/dev/null; then
  echo "ABBRUCH: 'fastapi' ist im venv nicht installiert."
  echo "         Prüfe: $PY -m pip install -r requirements.txt"
  exit 1
fi

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

echo "==> Smoke-Test (mit Retry – Startup dauert einige Sekunden)"
code="000"
i=0
for i in $(seq 1 10); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || echo "000")
  [ "$code" = "200" ] && break
  sleep 1
done
echo "    /api/health -> $code (nach $i Versuch(en))"

if [ "$code" = "200" ]; then
  echo "==> Deploy OK"
else
  # Fallback: /api/health nicht 200 → prüfe Root. Die App leitet '/' per Redirect
  # (303/302) auf die Login-/App-Seite; das genügt als Lebendigkeits-Nachweis.
  root=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ || echo "000")
  echo "    / -> $root"
  case "$root" in
    200|302|303) echo "==> Deploy OK (Lebendigkeit via / bestätigt)";;
    *) echo "==> WARN: /api/health != 200 und / != 200/302/303 – 'journalctl -u $SERVICE -n 50' prüfen"; exit 1;;
  esac
fi
