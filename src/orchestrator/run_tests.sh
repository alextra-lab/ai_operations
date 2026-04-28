#!/bin/bash
# Run pytest with PYTHONPATH set to the monorepo root and load .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
# Load .env if it exists in the repo root
if [ -f "$REPO_ROOT/.env" ]; then
  set -o allexport
  source "$REPO_ROOT/.env"
  set +o allexport
fi
pytest "$@"
