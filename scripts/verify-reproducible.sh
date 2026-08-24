#!/usr/bin/env bash
# =============================================================================
# Rebuilds the application and proves the release tree is reproducible.
#
#   ./scripts/verify-reproducible.sh
#
# The artifact-based deployment rests on the host verifying a SHA256 that CI
# produced. That is only meaningful if the same source really does build to the
# same bytes, so this rebuilds from scratch and compares file by file.
#
# Three files are expected to differ and are listed explicitly:
#
#   .next/prerender-manifest.json          draft-mode signing/encryption keys
#   .next/server/server-reference-manifest.js
#   .next/server/server-reference-manifest.json   server-action encryption key
#
# Next.js generates those cryptographic keys per build. They are deliberately
# NOT pinned: a key that is derivable from the commit is not a key, and this
# repository holds no secrets to pin them from. The site uses neither draft mode
# nor server actions, so their values never matter — but making them
# reproducible would be a security regression, not an improvement.
#
# Anything else differing is a real reproducibility bug and fails this script.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Files whose content is a per-build cryptographic key.
EXPECTED_DIFFERENT=(
  "sbs-web/.next/prerender-manifest.json"
  "sbs-web/.next/server/server-reference-manifest.js"
  "sbs-web/.next/server/server-reference-manifest.json"
)

log() { printf '\033[1m==>\033[0m %s\n' "$*"; }

log "Build 1"
rm -rf .next
npm run build > "$WORK/build1.log" 2>&1 || { tail -30 "$WORK/build1.log"; exit 1; }
./scripts/build-artifact.sh "$WORK/dist1" > "$WORK/pack1.log" 2>&1
A="$(ls -1 "$WORK/dist1"/*.tar.gz)"

log "Build 2"
rm -rf .next
npm run build > "$WORK/build2.log" 2>&1 || { tail -30 "$WORK/build2.log"; exit 1; }
./scripts/build-artifact.sh "$WORK/dist2" > "$WORK/pack2.log" 2>&1
B="$(ls -1 "$WORK/dist2"/*.tar.gz)"

DIGEST_A="$(sha256sum "$A" | cut -d' ' -f1)"
DIGEST_B="$(sha256sum "$B" | cut -d' ' -f1)"
printf '    build 1  %s\n' "$DIGEST_A"
printf '    build 2  %s\n' "$DIGEST_B"

if [ "$DIGEST_A" = "$DIGEST_B" ]; then
  echo
  echo "reproducibility: PASS — byte-identical artifacts"
  exit 0
fi

log "Digests differ — comparing trees"
mkdir -p "$WORK/a" "$WORK/b"
tar -xzf "$A" -C "$WORK/a"
tar -xzf "$B" -C "$WORK/b"

# diff runs with $WORK as the cwd, so it prints paths as "a/..." and "b/...".
( cd "$WORK" && diff -rq a b 2>&1 || true ) \
  | sed -E 's|^Files a/(.*) and b/.* differ$|\1|' \
  | sed -E 's|^Only in [ab]/([^:]*): (.*)$|MISSING \1/\2|' \
  | sort > "$WORK/differing.txt"

UNEXPECTED=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  known=0
  for allowed in "${EXPECTED_DIFFERENT[@]}"; do
    [ "$line" = "$allowed" ] && known=1 && break
  done
  if [ "$known" = 1 ]; then
    printf '    \033[1;33mkey\033[0m      %s\n' "$line"
  else
    printf '    \033[1;31munexpected\033[0m %s\n' "$line"
    UNEXPECTED=$((UNEXPECTED + 1))
  fi
done < "$WORK/differing.txt"

echo
if [ "$UNEXPECTED" -eq 0 ]; then
  echo "reproducibility: PASS — identical except the $(wc -l < "$WORK/differing.txt" | tr -d ' ') per-build key file(s)"
  exit 0
fi
echo "reproducibility: FAIL — $UNEXPECTED file(s) differ for reasons other than per-build keys" >&2
exit 1
