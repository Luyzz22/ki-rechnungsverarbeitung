#!/usr/bin/env bash
# =============================================================================
# Install the nginx configuration for the marketing hosts.
#
# Kept separate from deploy.sh so the application can be running and verified
# before any traffic is switched (§57). Existing server blocks — in particular
# app.sbsdeutschland.com — are left untouched.
# =============================================================================
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"

echo "==> Backing up the current nginx configuration to $BACKUP"
mkdir -p "$BACKUP"
cp -r /etc/nginx/sites-available "$BACKUP/"
cp -r /etc/nginx/sites-enabled "$BACKUP/"
[ -d /etc/nginx/snippets ] && cp -r /etc/nginx/snippets "$BACKUP/"

echo "==> Installing snippets"
mkdir -p /etc/nginx/snippets
install -m 0644 "$SOURCE_DIR/infra/nginx/snippets/"*.conf /etc/nginx/snippets/

echo "==> Installing the site configuration"
install -m 0644 "$SOURCE_DIR/infra/nginx/sbs-web.conf" /etc/nginx/sites-available/sbs-web.conf
ln -sfn /etc/nginx/sites-available/sbs-web.conf /etc/nginx/sites-enabled/sbs-web.conf

echo "==> Testing"
if ! nginx -t; then
  echo "nginx -t failed — rolling back"
  rm -f /etc/nginx/sites-enabled/sbs-web.conf
  cp -r "$BACKUP/sites-available/." /etc/nginx/sites-available/
  cp -r "$BACKUP/sites-enabled/." /etc/nginx/sites-enabled/
  nginx -t
  exit 1
fi

echo "==> Reloading nginx"
systemctl reload nginx

echo "==> Smoke test"
for host in sbsdeutschland.com industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '%-38s ' "$host"
  curl -s -o /dev/null -w '%{http_code}\n' -H "Host: $host" http://127.0.0.1/ || true
done
printf '%-38s ' "app.sbsdeutschland.com (unchanged)"
curl -s -o /dev/null -w '%{http_code}\n' -H "Host: app.sbsdeutschland.com" http://127.0.0.1/ || true

echo "Rollback: rm /etc/nginx/sites-enabled/sbs-web.conf && systemctl reload nginx"
echo "Full restore from: $BACKUP"
