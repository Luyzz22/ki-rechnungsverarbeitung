#!/usr/bin/env bash
# =============================================================================
# Runs every infrastructure test in this directory.
#
#   sudo ./infra/tests/run-all.sh [artifact.tar.gz]
#
# Without an artifact the deployment scenarios are skipped and reported as
# skipped — never as passed. Build one first with:
#
#   npm run build && ./scripts/build-artifact.sh dist
#
# These tests need root because they inspect /etc/nginx, run `nginx -t` and
# start the runtime as the service user. None of them writes to /etc/nginx,
# /etc/systemd/system or the real services; that is itself one of the things
# they assert.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT="${1:-}"

if [ -z "$ARTIFACT" ]; then
  ARTIFACT="$(ls -1t "$HERE/../../dist/"*.tar.gz 2>/dev/null | head -1 || true)"
fi

[ "$(id -u)" = "0" ] || { echo "must run as root" >&2; exit 2; }

TOTAL=0
FAILED=0
SKIPPED=0
RESULTS=()

run() {
  local name="$1"; shift
  TOTAL=$((TOTAL + 1))
  printf '\n\033[1m### %s\033[0m\n' "$name"
  if "$@"; then
    RESULTS+=("PASS  $name")
  else
    RESULTS+=("FAIL  $name")
    FAILED=$((FAILED + 1))
  fi
}

skip() {
  local name="$1" why="$2"
  TOTAL=$((TOTAL + 1))
  SKIPPED=$((SKIPPED + 1))
  printf '\n\033[1m### %s\033[0m\n  \033[1;33mSKIP\033[0m %s\n' "$name" "$why"
  RESULTS+=("SKIP  $name — $why")
}

run "A0  check-only immutability — self-test"   "$HERE/check-only-immutability.sh" --self-test
run "A   check-only immutability — /etc/nginx"  "$HERE/check-only-immutability.sh"
run "    nginx HTTP/2 syntax matrix"            "$HERE/nginx-syntax-matrix.sh"

if [ -n "$ARTIFACT" ] && [ -f "$ARTIFACT" ]; then
  run "B-F deploy invoice-app gate"             "$HERE/deploy-invoice-gate.sh" "$ARTIFACT"
else
  skip "B-F deploy invoice-app gate" "no artifact in dist/ — pass one as an argument"
fi

printf '\n\033[1m=== infra test summary ===\033[0m\n'
for r in "${RESULTS[@]}"; do
  case "$r" in
    PASS*) printf '  \033[1;32m%s\033[0m\n' "$r" ;;
    FAIL*) printf '  \033[1;31m%s\033[0m\n' "$r" ;;
    *)     printf '  \033[1;33m%s\033[0m\n' "$r" ;;
  esac
done
printf '\n%s suite(s): %s failed, %s skipped\n' "$TOTAL" "$FAILED" "$SKIPPED"
[ "$FAILED" -eq 0 ] || exit 1
[ "$SKIPPED" -eq 0 ] || exit 0
