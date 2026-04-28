#!/bin/bash
###############################################################################
# Reset Demo Database Script
# AI Operations Platform
#
# This script resets the demo database to a clean state with RBAC V2 schema
# and all demo seed data. It is designed for demo/presentation environments.
#
# WARNING: This script is DESTRUCTIVE and will delete all existing data!
#
# Usage: bash ops/operations/reset_demo_database.sh
#
# Prerequisites:
#   - PostgreSQL running and accessible
#   - Qdrant running and accessible
#   - Environment variables set (or defaults will be used)
#   - psql command available
#   - Python 3 with qdrant-client and psycopg installed
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default database configuration (can be overridden by environment variables)
# Note: Default is 'aio-test' for demo. For testing, use 'aio-test'
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5532}
POSTGRES_USER=${POSTGRES_USER:-user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_DB=${POSTGRES_DB:-aio-test}

# Find psql command (prefer psql-17, fallback to psql)
if command -v psql-17 &> /dev/null; then
    PSQL_CMD="psql-17"
elif command -v psql &> /dev/null; then
    PSQL_CMD="psql"
else
    echo -e "${RED}❌ psql command not found. Please install PostgreSQL client tools.${NC}"
    exit 1
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}AI Operations Platform - Demo Database Reset${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will DELETE all existing data!${NC}"
echo -e "${YELLOW}   Database: ${POSTGRES_DB}${NC}"
echo -e "${YELLOW}   Host: ${POSTGRES_HOST}:${POSTGRES_PORT}${NC}"
echo ""

# Confirm before proceeding
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${RED}❌ Reset cancelled by user${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}🔄 Starting Demo Database Reset...${NC}"
echo ""

# ============================================================================
# Step 1: Reset Qdrant Vector Database
# ============================================================================
echo -e "${YELLOW}📦 Step 1: Resetting Qdrant vector database...${NC}"
if [ -f "${SCRIPT_DIR}/reset_datastores.py" ]; then
    cd "${PROJECT_ROOT}"
    if python3 "${SCRIPT_DIR}/reset_datastores.py" 2>/dev/null; then
        echo -e "${GREEN}✅ Qdrant vector database reset complete${NC}"
    else
        echo -e "${YELLOW}⚠️  Qdrant reset had issues (may be expected if Qdrant is not running)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  reset_datastores.py not found, skipping Qdrant reset${NC}"
fi
echo ""

# ============================================================================
# Step 2: Drop and Recreate PostgreSQL Database
# ============================================================================
echo -e "${YELLOW}🗑️  Step 2: Terminating connections and dropping existing database...${NC}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

# First, terminate all connections to the target database (multiple attempts)
echo -e "${CYAN}   Terminating active connections...${NC}"
for attempt in 1 2 3; do
    TERMINATED=$(${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
        -tAc "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" 2>/dev/null || echo "0")

    if [ "${TERMINATED}" = "0" ] || [ -z "${TERMINATED}" ]; then
        break
    fi

    ${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true

    sleep 2
done

# Final check and force termination if needed
REMAINING=$(${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -tAc "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" 2>/dev/null || echo "0")

if [ "${REMAINING}" != "0" ] && [ -n "${REMAINING}" ]; then
    echo -e "${YELLOW}⚠️  Warning: ${REMAINING} connection(s) still active. Attempting force termination...${NC}"
    ${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" > /dev/null 2>&1 || true
    sleep 3
fi

# Connect to postgres database to drop the target database
# Quote database name to handle special characters (e.g., hyphens)
${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";" 2>&1 || {
    echo -e "${RED}❌ Failed to drop database. There may be active connections.${NC}"
    echo -e "${YELLOW}💡 Tip: Stop services (docker-compose down) or manually terminate connections.${NC}"
    exit 1
}
echo -e "${GREEN}✅ Database dropped${NC}"
echo ""

echo -e "${YELLOW}🏗️  Step 3: Creating fresh database...${NC}"
${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -c "CREATE DATABASE \"${POSTGRES_DB}\";" || {
    echo -e "${RED}❌ Failed to create database${NC}"
    exit 1
}
echo -e "${GREEN}✅ Database created${NC}"
echo ""

# ============================================================================
# Step 4: Run Init Script
# ============================================================================
echo -e "${YELLOW}📋 Step 4: Running database initialization script...${NC}"
INIT_SCRIPT="${PROJECT_ROOT}/ops/database/init/000_complete_init.sql"

if [ ! -f "${INIT_SCRIPT}" ]; then
    echo -e "${RED}❌ Init script not found: ${INIT_SCRIPT}${NC}"
    exit 1
fi

${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -f "${INIT_SCRIPT}" || {
    echo -e "${RED}❌ Failed to run init script${NC}"
    exit 1
}
echo -e "${GREEN}✅ Database schema initialized${NC}"
echo ""

# ============================================================================
# Step 5: Run Seed Scripts in Order
# ============================================================================
echo -e "${YELLOW}🌱 Step 5: Running seed scripts...${NC}"
SEED_DIR="${PROJECT_ROOT}/ops/database/seed"

if [ ! -d "${SEED_DIR}" ]; then
    echo -e "${RED}❌ Seed directory not found: ${SEED_DIR}${NC}"
    exit 1
fi

# Run seed scripts in numerical order
for seed_script in "${SEED_DIR}"/[0-9][0-9][0-9]_*.sql; do
    if [ -f "${seed_script}" ]; then
        script_name=$(basename "${seed_script}")
        echo -e "${CYAN}   Running: ${script_name}${NC}"
        ${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
            -f "${seed_script}" || {
            echo -e "${RED}❌ Failed to run seed script: ${script_name}${NC}"
            exit 1
        }
        echo -e "${GREEN}   ✅ ${script_name} completed${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ All seed scripts completed${NC}"
echo ""

# ============================================================================
# Step 6: Verification Summary
# ============================================================================
echo -e "${YELLOW}🔍 Step 6: Verifying setup...${NC}"

# Quick verification queries
USER_COUNT=$(${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

USE_CASE_COUNT=$(${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -tAc "SELECT COUNT(*) FROM use_cases;" 2>/dev/null || echo "0")

TEAM_MEMBERSHIP_COUNT=$(${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -tAc "SELECT COUNT(*) FROM user_roles WHERE role LIKE 'team:%';" 2>/dev/null || echo "0")

echo -e "${CYAN}   Users: ${USER_COUNT}${NC}"
echo -e "${CYAN}   Use Cases: ${USE_CASE_COUNT}${NC}"
echo -e "${CYAN}   Team Memberships: ${TEAM_MEMBERSHIP_COUNT}${NC}"
echo ""

# ============================================================================
# Success Message
# ============================================================================
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}✅ Demo Database Reset Complete!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "${BLUE}📊 Summary:${NC}"
echo -e "   - Database: ${POSTGRES_DB}"
echo -e "   - Users: ${USER_COUNT}"
echo -e "   - Use Cases: ${USE_CASE_COUNT}"
echo -e "   - Team Memberships: ${TEAM_MEMBERSHIP_COUNT}"
echo ""
echo -e "${BLUE}👤 Demo Credentials:${NC}"
echo -e "   - Default password for all users: ${YELLOW}adminpassword${NC}"
echo -e "   - See ${CYAN}docs/demo/DEMO_CREDENTIALS.md${NC} for full user list"
echo ""
echo -e "${BLUE}🔍 Next Steps:${NC}"
echo -e "   - Run verification: ${CYAN}bash ops/operations/verify_demo_setup.sh${NC}"
echo -e "   - Start services: ${CYAN}docker-compose up -d${NC}"
echo ""
