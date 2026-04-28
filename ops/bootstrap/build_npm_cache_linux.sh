#!/bin/bash

# Build npm cache for Linux inside Docker container (like build_wheelhouse.sh)
# Must be run from <project root>
# This ensures all native binaries are Linux-compatible
#
# FAST INTERNET MODE: Set INCLUDE_CYPRESS=1 to download Cypress binary (~400MB)
#   Example: INCLUDE_CYPRESS=1 bash ops/bootstrap/build_npm_cache_linux.sh
# SLOW INTERNET MODE: Default skips Cypress (use for quick iteration)

INCLUDE_CYPRESS=${INCLUDE_CYPRESS:-0}

echo "========================================"
echo "Building npm cache for LINUX"
echo "========================================"
echo "Building inside Docker container..."
echo "Target: src/npm_cache/"

if [ "$INCLUDE_CYPRESS" = "1" ]; then
  echo "Mode: FULL (includes Cypress binary ~400MB)"
  SCRIPTS_FLAG=""
else
  echo "Mode: FAST (skips Cypress binary)"
  SCRIPTS_FLAG="--ignore-scripts"
fi

echo ""

docker run --rm \
  -v "$PWD/src/npm_cache:/cache" \
  -v "$PWD/src/frontend-angular:/source:ro" \
  --platform linux/arm64 \
  node:24-alpine \
  sh -c "
    set -e
    mkdir -p /app && \
    cp /source/package.json /source/package-lock.json /app/ && \
    cd /app && \
    npm ci --include=dev --legacy-peer-deps --prefer-offline $SCRIPTS_FLAG --cache /cache && \
    echo '' && \
    echo '✅ npm cache built successfully for Linux!' && \
    du -sh /cache
  "

echo ""
echo "========================================"
echo "✅ Complete!"
echo "========================================"
echo "Cache location: src/npm_cache/"
echo "This cache contains Linux binaries."

if [ "$INCLUDE_CYPRESS" = "1" ]; then
  echo ""
  echo "NOTE: Cypress binary included. Docker builds can use --ignore-scripts"
  echo "      or remove it to use the cached Cypress binary."
else
  echo ""
  echo "NOTE: Cypress binary NOT included (fast mode)."
  echo "      To include Cypress: INCLUDE_CYPRESS=1 bash $0"
fi

echo ""
