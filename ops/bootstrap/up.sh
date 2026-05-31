#!/usr/bin/env bash
# ops/bootstrap/up.sh — Profile-aware bootstrap wrapper for docker compose up
#
# Usage:
#   ./ops/bootstrap/up.sh --profile local|enterprise|train [extra docker compose args...]
#
# Profiles:
#   local       Public PyPI + docker.io; uses docker-compose.local.yml overlay
#   enterprise  Artifactory mirrors (M3); placeholder URLs, prints warning
#   train       Offline mode; uses pre-built wheelhouse/npm_cache and staged models
#
# This script is idempotent — safe to run multiple times.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repo root relative to this script's location
# ---------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# ---------------------------------------------------------------------------
# Load config/env/.env into the environment (if it exists)
# Docker Compose does not auto-discover it at config/env/.env; exporting it
# here ensures all required env vars are available for variable substitution.
# ---------------------------------------------------------------------------
ENV_FILE="${REPO_ROOT}/config/env/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "==> Loading environment from ${ENV_FILE}..."
    # shellcheck disable=SC2046
    # Plain xargs (whitespace-splitting) correctly handles lines with inline # comments:
    # e.g. REDACT_LOGS=false  # comment → exports REDACT_LOGS=false; comment tokens ignored
    export $(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | xargs) 2>/dev/null || true
else
    echo "WARNING: ${ENV_FILE} not found." >&2
    echo "         Run: cp ${REPO_ROOT}/config/env/env.template ${ENV_FILE}" >&2
    echo "         Then edit it with real POSTGRES_PASSWORD, JWT_SECRET, TOOL_SECRETS_KEY values." >&2
    echo "         Continuing — some services may fail if required vars are unset." >&2
fi

# ---------------------------------------------------------------------------
# Parse --profile argument
# ---------------------------------------------------------------------------
PROFILE=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --profile requires a value (local|enterprise|train)" >&2
                exit 1
            fi
            PROFILE="$2"
            shift 2
            ;;
        --profile=*)
            PROFILE="${1#--profile=}"
            shift
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ -z "$PROFILE" ]]; then
    echo "ERROR: --profile is required. Usage: $0 --profile local|enterprise|train [extra args...]" >&2
    exit 1
fi

case "$PROFILE" in
    local|enterprise|train) ;;
    *)
        echo "ERROR: Unknown profile '${PROFILE}'. Must be one of: local, enterprise, train" >&2
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Idempotently create the observability Docker network
# ---------------------------------------------------------------------------
echo "==> Ensuring Docker network 'observability' exists..."
docker network create observability 2>/dev/null || true

# ---------------------------------------------------------------------------
# Idempotently create required data directories
# ---------------------------------------------------------------------------
echo "==> Ensuring data directories exist under ${REPO_ROOT}/data/ ..."
mkdir -p \
    "${REPO_ROOT}/data/postgres" \
    "${REPO_ROOT}/data/qdrant" \
    "${REPO_ROOT}/data/redis" \
    "${REPO_ROOT}/data/models" \
    "${REPO_ROOT}/data/llm-guard-models" \
    "${REPO_ROOT}/data/retrieval/tmp"

# ---------------------------------------------------------------------------
# Assemble compose files and build-args per profile
# ---------------------------------------------------------------------------
COMPOSE_FILES=()
BUILD_ARGS=()

case "$PROFILE" in
    local)
        COMPOSE_FILES=(
            "-f" "${REPO_ROOT}/deploy/docker-compose.yml"
            "-f" "${REPO_ROOT}/deploy/docker-compose.local.yml"
        )
        BUILD_ARGS=(
            "--build-arg" "BASE_REGISTRY=docker.io/library"
            "--build-arg" "PIP_INDEX_URL=https://pypi.org/simple"
            "--build-arg" "OFFLINE=0"
        )
        ;;
    enterprise)
        echo ""
        echo "WARNING: enterprise profile uses Artifactory mirror URLs that must be" >&2
        echo "         configured before M3. Update BASE_REGISTRY and PIP_INDEX_URL" >&2
        echo "         placeholders in this script once your Artifactory instance is ready." >&2
        echo ""
        COMPOSE_FILES=(
            "-f" "${REPO_ROOT}/deploy/docker-compose.yml"
        )
        BUILD_ARGS=(
            "--build-arg" "BASE_REGISTRY=<ARTIFACTORY_DOCKER_REGISTRY_PLACEHOLDER>"
            "--build-arg" "PIP_INDEX_URL=<ARTIFACTORY_PYPI_URL_PLACEHOLDER>"
            "--build-arg" "OFFLINE=0"
        )
        ;;
    train)
        COMPOSE_FILES=(
            "-f" "${REPO_ROOT}/deploy/docker-compose.yml"
        )
        BUILD_ARGS=(
            "--build-arg" "OFFLINE=1"
        )
        ;;
esac

# ---------------------------------------------------------------------------
# Print summary before running
# ---------------------------------------------------------------------------
echo ""
echo "==> Bootstrap summary"
echo "    Profile      : ${PROFILE}"
echo "    Repo root    : ${REPO_ROOT}"
echo "    Compose files: ${COMPOSE_FILES[*]}"
echo "    Build args   : ${BUILD_ARGS[*]}"
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    echo "    Extra args   : ${EXTRA_ARGS[*]}"
fi
echo ""

# ---------------------------------------------------------------------------
# Run docker compose — build then up
# `docker compose up --build` does not accept --build-arg in Compose v5.
# Separate the build step (with --build-arg) from the up step.
# ---------------------------------------------------------------------------
echo "==> Building images (DOCKER_BUILDKIT=0 to avoid BuildKit manifest-resolution timeout)..."
DOCKER_BUILDKIT=0 docker compose \
    "${COMPOSE_FILES[@]}" \
    build \
    "${BUILD_ARGS[@]}"

echo "==> Starting services..."
docker compose \
    "${COMPOSE_FILES[@]}" \
    up \
    "${EXTRA_ARGS[@]}"
