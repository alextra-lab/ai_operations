#!/bin/bash
###############################################################################
# Verify Demo Setup Script
# AI Operations Platform
#
# This script verifies that the demo database setup is correct and complete.
# It checks all RBAC V2 requirements, team memberships, and use case isolation.
#
# Usage: bash ops/operations/verify_demo_setup.sh
#
# Prerequisites:
#   - PostgreSQL running and accessible
#   - Database initialized and seeded
#   - Environment variables set (or defaults will be used)
#   - psql command available
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

# Expected values
EXPECTED_USER_COUNT=17
EXPECTED_TEAM_MEMBERSHIPS=7
EXPECTED_PUBLISHED_USE_CASES=5
EXPECTED_DRAFT_USE_CASES=5

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}AI Operations Platform - Demo Setup Verification${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "${CYAN}Database: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}${NC}"
echo ""

export PGPASSWORD="${POSTGRES_PASSWORD}"

# Track pass/fail counts
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Function to run SQL query and get result
run_query() {
    local query="$1"
    ${PSQL_CMD} -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
        -tAc "${query}" 2>/dev/null || echo "0"
}

# Function to check and report
check_result() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    local description="${4:-}"

    if [ "${actual}" = "${expected}" ]; then
        echo -e "${GREEN}✅ PASS: ${name} (expected: ${expected}, actual: ${actual})${NC}"
        if [ -n "${description}" ]; then
            echo -e "   ${description}"
        fi
        ((PASS_COUNT++))
        return 0
    else
        echo -e "${RED}❌ FAIL: ${name} (expected: ${expected}, actual: ${actual})${NC}"
        if [ -n "${description}" ]; then
            echo -e "   ${description}"
        fi
        ((FAIL_COUNT++))
        return 1
    fi
}

# Function to warn
warn_result() {
    local name="$1"
    local message="$2"
    echo -e "${YELLOW}⚠️  WARN: ${name}${NC}"
    echo -e "   ${message}"
    ((WARN_COUNT++))
}

echo -e "${CYAN}🔍 Running verification checks...${NC}"
echo ""

# ============================================================================
# Check 1: User Count
# ============================================================================
echo -e "${BLUE}1. User Count${NC}"
USER_COUNT=$(run_query "SELECT COUNT(*) FROM users;")
check_result "User count" "${EXPECTED_USER_COUNT}" "${USER_COUNT}" \
    "Total users in database"
echo ""

# ============================================================================
# Check 2: System Roles Coverage
# ============================================================================
echo -e "${BLUE}2. System Roles Coverage${NC}"
SYSTEM_ROLES_COUNT=$(run_query "
    SELECT COUNT(DISTINCT role)
    FROM users
    WHERE role IN (
        'admin', 'corpus_admin', 'developer', 'use_case_admin',
        'tools_admin', 'role_admin', 'use_case_publisher',
        'conversations_privileged', 'user', 'service'
    );
")
EXPECTED_SYSTEM_ROLES=10
check_result "System roles covered" "${EXPECTED_SYSTEM_ROLES}" "${SYSTEM_ROLES_COUNT}" \
    "Number of distinct system roles in users table"
echo ""

# ============================================================================
# Check 3: Team Memberships
# ============================================================================
echo -e "${BLUE}3. Team Memberships${NC}"
TEAM_MEMBERSHIP_COUNT=$(run_query "SELECT COUNT(*) FROM user_roles WHERE role LIKE 'team:%';")
check_result "Team memberships" "${EXPECTED_TEAM_MEMBERSHIPS}" "${TEAM_MEMBERSHIP_COUNT}" \
    "Total team role assignments"

# Check individual teams
CSIRT_COUNT=$(run_query "SELECT COUNT(*) FROM user_roles WHERE role = 'team:csirt_security';")
GOVERNANCE_COUNT=$(run_query "SELECT COUNT(*) FROM user_roles WHERE role = 'team:soc_governance';")
DEVELOPMENT_COUNT=$(run_query "SELECT COUNT(*) FROM user_roles WHERE role = 'team:development';")

echo -e "${CYAN}   Team breakdown:${NC}"
echo -e "   - team:csirt_security: ${CSIRT_COUNT} members (expected: 3)"
echo -e "   - team:soc_governance: ${GOVERNANCE_COUNT} members (expected: 2)"
echo -e "   - team:development: ${DEVELOPMENT_COUNT} members (expected: 2)"
echo ""

# ============================================================================
# Check 4: Use Case Inventory
# ============================================================================
echo -e "${BLUE}4. Use Case Inventory${NC}"
PUBLISHED_COUNT=$(run_query "SELECT COUNT(*) FROM use_cases WHERE lifecycle_state = 'published';")
DRAFT_COUNT=$(run_query "SELECT COUNT(*) FROM use_cases WHERE lifecycle_state = 'draft';")
TOTAL_USE_CASES=$((PUBLISHED_COUNT + DRAFT_COUNT))

check_result "Published use cases" "${EXPECTED_PUBLISHED_USE_CASES}" "${PUBLISHED_COUNT}" \
    "Published use cases (should be globally visible)"
check_result "Draft use cases" "${EXPECTED_DRAFT_USE_CASES}" "${DRAFT_COUNT}" \
    "Draft use cases (should be team-isolated)"
echo ""

# ============================================================================
# Check 5: Draft Team Isolation
# ============================================================================
echo -e "${BLUE}5. Draft Team Isolation${NC}"
DRAFTS_WITHOUT_TEAM=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'draft' AND team_id IS NULL;
")
check_result "Draft team isolation" "0" "${DRAFTS_WITHOUT_TEAM}" \
    "Draft use cases without team_id (should be 0 - all drafts must have team_id)"

# Check drafts by team
CSIRT_DRAFTS=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'draft' AND team_id = 'team:csirt_security';
")
GOVERNANCE_DRAFTS=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'draft' AND team_id = 'team:soc_governance';
")
DEVELOPMENT_DRAFTS=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'draft' AND team_id = 'team:development';
")

echo -e "${CYAN}   Draft use cases by team:${NC}"
echo -e "   - team:csirt_security: ${CSIRT_DRAFTS} drafts (expected: 2)"
echo -e "   - team:soc_governance: ${GOVERNANCE_DRAFTS} drafts (expected: 1)"
echo -e "   - team:development: ${DEVELOPMENT_DRAFTS} drafts (expected: 2)"
echo ""

# ============================================================================
# Check 6: Published Visibility
# ============================================================================
echo -e "${BLUE}6. Published Visibility${NC}"
PUBLISHED_WITH_TEAM=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'published' AND team_id IS NOT NULL;
")
check_result "Published visibility" "0" "${PUBLISHED_WITH_TEAM}" \
    "Published use cases with team_id (should be 0 - published must have team_id = NULL)"
echo ""

# ============================================================================
# Check 7: RBAC V2 Tables
# ============================================================================
echo -e "${BLUE}7. RBAC V2 Schema${NC}"

# Check team_id column exists
TEAM_ID_COLUMN_EXISTS=$(run_query "
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_name = 'use_cases' AND column_name = 'team_id';
")
check_result "use_cases.team_id column" "1" "${TEAM_ID_COLUMN_EXISTS}" \
    "team_id column exists in use_cases table"

# Check role_collection_assignments table exists
RCA_TABLE_EXISTS=$(run_query "
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_name = 'role_collection_assignments';
")
check_result "role_collection_assignments table" "1" "${RCA_TABLE_EXISTS}" \
    "role_collection_assignments table exists"
echo ""

# ============================================================================
# Check 8: Seed Script Metadata
# ============================================================================
echo -e "${BLUE}8. Seed Script Metadata${NC}"
SEEDED_USERS=$(run_query "
    SELECT COUNT(*)
    FROM users
    WHERE username IN (
        'admin', 'admin2', 'corpus_manager', 'corpus_dev', 'developer1', 'developer2',
        'uc_admin', 'tools_manager', 'role_manager', 'uc_publisher', 'publisher2',
        'conv_analyst', 'analyst_conv', 'service_account', 'testuser', 'analyst1', 'analyst2'
    );
")
check_result "Seeded users" "${EXPECTED_USER_COUNT}" "${SEEDED_USERS}" \
    "Users from seed scripts exist"

SEEDED_DRAFT_UCS=$(run_query "
    SELECT COUNT(*)
    FROM use_cases
    WHERE lifecycle_state = 'draft'
      AND metadata->>'seed_script' = '009_seed_draft_use_cases';
")
check_result "Seeded draft use cases" "${EXPECTED_DRAFT_USE_CASES}" "${SEEDED_DRAFT_UCS}" \
    "Draft use cases from seed script 009"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "${GREEN}✅ Passed: ${PASS_COUNT}${NC}"
if [ ${FAIL_COUNT} -gt 0 ]; then
    echo -e "${RED}❌ Failed: ${FAIL_COUNT}${NC}"
fi
if [ ${WARN_COUNT} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warnings: ${WARN_COUNT}${NC}"
fi
echo ""

if [ ${FAIL_COUNT} -eq 0 ]; then
    echo -e "${GREEN}🎉 All verification checks passed!${NC}"
    echo ""
    echo -e "${BLUE}📋 Demo Setup Status:${NC}"
    echo -e "   ✅ Database schema initialized with RBAC V2"
    echo -e "   ✅ All ${EXPECTED_USER_COUNT} users created"
    echo -e "   ✅ ${EXPECTED_TEAM_MEMBERSHIPS} team memberships assigned"
    echo -e "   ✅ ${EXPECTED_PUBLISHED_USE_CASES} published use cases (globally visible)"
    echo -e "   ✅ ${EXPECTED_DRAFT_USE_CASES} draft use cases (team-isolated)"
    echo -e "   ✅ Team isolation verified"
    echo -e "   ✅ Published visibility verified"
    echo ""
    echo -e "${BLUE}👤 Next Steps:${NC}"
    echo -e "   - Review demo credentials: ${CYAN}docs/demo/DEMO_CREDENTIALS.md${NC}"
    echo -e "   - Test scenarios: ${CYAN}docs/demo/DEMO_TEST_SCENARIOS.md${NC}"
    echo -e "   - Start services: ${CYAN}docker-compose up -d${NC}"
    exit 0
else
    echo -e "${RED}❌ Verification failed! Please review the errors above.${NC}"
    echo ""
    echo -e "${YELLOW}💡 Troubleshooting:${NC}"
    echo -e "   - Run reset script: ${CYAN}bash ops/operations/reset_demo_database.sh${NC}"
    echo -e "   - Check database connection settings"
    echo -e "   - Verify all seed scripts ran successfully"
    exit 1
fi
