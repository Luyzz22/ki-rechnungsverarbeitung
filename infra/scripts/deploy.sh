#!/usr/bin/env bash
# =============================================================================
# Deploy the SBS marketing web layer to the DigitalOcean host.
#
# Zero-downtime oriented (§57): the new build is assembled beside the running
# one and only swapped in once it answers a health check on its own port. The
# invoice application on port 8000 is never touched.
#
# Run from a checkout of this repository on the target host, as root:
#   sbs-web/infra/scripts/deploy.sh
# =============================================================================
set -euo pipefail

APP_DIR="/var/www/sbs-web"
RELEASE_DIR="/var/www/sbs-web-next"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${PORT:-3100}"
STAGING_PORT="${STAGING_PORT:-3199}"

log() { printf '\033[1m==>\033[0m %s\n' "$*"; }

# ---- 0. Record the state we are moving away from (§89) ----------------------
log "Recording current state"
mkdir -p /var/log/sbs-web
{
  echo "date:        $(date --iso-8601=seconds)"
  echo "commit:      $(git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || echo 'n/a')"
  echo "nginx:       $(nginx -v 2>&1)"
  echo "node:        $(node --version)"
  echo "invoice-app: $(systemctl is-active invoice-app 2>/dev/null || echo unknown)"
  echo "sbs-web:     $(systemctl is-active sbs-web 2>/dev/null || echo not-installed)"
} | tee "/var/log/sbs-web/deploy-$(date +%Y%m%d-%H%M%S).state"

# ---- 1. Build --------------------------------------------------------------
log "Installing dependencies and building"
cd "$SOURCE_DIR"
npm ci --omit=dev --ignore-scripts || npm ci
npm run build

# ---- 2. Assemble the standalone release ------------------------------------
log "Assembling standalone release in $RELEASE_DIR"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
cp -r .next/standalone/. "$RELEASE_DIR/"
mkdir -p "$RELEASE_DIR/.next"
cp -r .next/static "$RELEASE_DIR/.next/static"
[ -d public ] && cp -r public "$RELEASE_DIR/public"
chown -R www-data:www-data "$RELEASE_DIR"

# ---- 3. Health-check the new build on a staging port ------------------------
log "Health-checking the new build on port $STAGING_PORT"
PORT="$STAGING_PORT" HOSTNAME=127.0.0.1 setsid sudo -u www-data \
  node "$RELEASE_DIR/server.js" > /tmp/sbs-web-staging.log 2>&1 &
STAGING_PID=$!
trap 'kill "$STAGING_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://127.0.0.1:$STAGING_PORT/"; then break; fi
  sleep 1
done

for path in / /industrie /legal /plattform /academy; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$STAGING_PORT$path")
  [ "$code" = "200" ] || { echo "Health check failed: $path → $code"; exit 1; }
done
log "Health checks passed"

kill "$STAGING_PID" 2>/dev/null || true
trap - EXIT

# ---- 4. Swap ---------------------------------------------------------------
log "Swapping release into $APP_DIR"
if [ -d "$APP_DIR" ]; then
  rm -rf "$APP_DIR.previous"
  mv "$APP_DIR" "$APP_DIR.previous"
fi
mv "$RELEASE_DIR" "$APP_DIR"

install -m 0644 "$SOURCE_DIR/infra/systemd/sbs-web.service" /etc/systemd/system/sbs-web.service
systemctl daemon-reload
systemctl enable sbs-web
systemctl restart sbs-web

for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/"; then break; fi
  sleep 1
done
curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" || { echo "sbs-web did not come up"; exit 1; }

# ---- 5. Verify the invoice application is untouched -------------------------
log "Verifying the invoice application is still healthy"
systemctl is-active --quiet invoice-app || echo "WARNING: invoice-app is not active"
curl -s -o /dev/null -w 'invoice-app: %{http_code}\n' http://127.0.0.1:8000/ || true

log "Deploy complete. Nginx has NOT been reloaded — see infra/scripts/enable-nginx.sh"
