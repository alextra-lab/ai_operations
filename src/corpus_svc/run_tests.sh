#!/bin/bash
# Run pytest with PYTHONPATH set to the monorepo root and load .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$REPO_ROOT/src"
export PYTHONPATH="$SRC_DIR"
# Load .env if it exists in the repo root
if [ -f "$REPO_ROOT/.env" ]; then
  set -o allexport
  source "$REPO_ROOT/.env"
  set +o allexport
fi
pytest "$@"
