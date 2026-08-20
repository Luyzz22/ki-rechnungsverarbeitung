#!/usr/bin/env bash
# =============================================================================
# Extend the existing Let's Encrypt certificate to the two new hostnames.
#
# This EXPANDS the certificate that already covers sbsdeutschland.com rather
# than issuing a separate one, so renewal stays a single job. Run only after
# the DNS records for the new hosts resolve to this server.
# =============================================================================
set -euo pipefail

echo "==> Checking DNS before requesting certificates"
for host in industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  if ! getent hosts "$host" > /dev/null; then
    echo "ERROR: $host does not resolve yet. Create the DNS record first."
    exit 1
  fi
  printf '%-34s %s\n' "$host" "$(getent hosts "$host" | awk '{print $1}' | head -1)"
done

echo "==> Expanding the certificate"
certbot --nginx --expand \
  -d sbsdeutschland.com \
  -d www.sbsdeutschland.com \
  -d industrie.sbsdeutschland.com \
  -d legal.sbsdeutschland.com \
  --keep-until-expiring --non-interactive --agree-tos

echo "==> Verifying"
for host in industrie.sbsdeutschland.com legal.sbsdeutschland.com; do
  printf '%-34s ' "$host"
  curl -sI "https://$host" | head -1 || true
done

echo "==> Renewal dry run"
certbot renew --dry-run
