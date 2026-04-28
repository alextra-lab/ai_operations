#!/bin/bash
# List Python packages that have newer versions on PyPI than currently installed.
# Requires: project deps already installed (e.g. in an active venv after
#   pip install -r requirements-all.txt or from wheelhouse).
# Run from project root. For security audit, run: pip-audit -r requirements-all.txt

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Checking for outdated packages (installed vs PyPI latest)..."
echo "Using: $(which python) ($(python --version 2>&1))"
echo ""

if ! python -c "import pip" 2>/dev/null; then
  echo "Error: pip not available. Activate a venv with project deps installed."
  exit 1
fi

pip list --outdated 2>/dev/null || true
OUTDATED_EXIT=$?

if [ "$OUTDATED_EXIT" -ne 0 ]; then
  echo ""
  echo "If the command failed, ensure you have installed project dependencies first:"
  echo "  python -m venv .venv && source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows"
  echo "  pip install -r requirements-all.txt"
  echo "  bash ops/bootstrap/check_outdated_packages.sh"
  exit "$OUTDATED_EXIT"
fi

echo ""
echo "Optional: run 'pip-audit -r requirements-all.txt' for known-vulnerability check."
