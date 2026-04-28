#!/usr/bin/env bash
# run_tests.sh  – execute the whole test suite with correct import path

# Always run from the directory that contains this script
cd "$(dirname "$0")" || exit 1       #  ← /Users/Alex/Documents/Cline/ai_operations/src

# Prepend repo root and backend/ to PYTHONPATH
export PYTHONPATH="$PWD:$PWD/shared:$PWD/backend${PYTHONPATH:+:$PYTHONPATH}"



pytest --cov=backend.app --cov-report=term-missing backend/tests "$@"
