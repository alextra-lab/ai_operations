#!/bin/bash
# ============================================================================
# Apply Provider Fix to Existing Database (Docker Version)
# ============================================================================
# This script applies the provider type fixes using docker exec
# Date: 2025-12-11
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Applying Provider Type Fix (Docker)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Load environment
set -a && source config/env/env.test && set +a

echo -e "${YELLOW}Database Configuration:${NC}"
echo "  Container: postgres-test"
echo "  User: $POSTGRES_USER"
echo "  Database: $POSTGRES_DB"
echo ""

# Function to run SQL file
run_sql() {
    local file=$1
    local description=$2

    echo -e "${YELLOW}Running: ${description}${NC}"

    if [ ! -f "$file" ]; then
        echo -e "${RED}ERROR: File not found: $file${NC}"
        exit 1
    fi

    docker exec -i postgres-test psql -U $POSTGRES_USER -d $POSTGRES_DB < "$file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed${NC}"
        exit 1
    fi
}

# Step 1: Create LMStudio gateway provider (already done, but idempotent)
echo -e "${GREEN}Step 1: Create LMStudio Gateway Provider${NC}"
run_sql "ops/database/seed/010_seed_gateway_providers.sql" "LMStudio gateway provider"

# Step 2: Apply migration to fix existing models
echo -e "${GREEN}Step 2: Fix Existing Model Provider Types${NC}"
run_sql "ops/database/migrations/033_fix_embedding_model_provider_type.sql" "Migration 033 - Provider type fix"

# Step 3: Verify the changes
echo -e "${GREEN}Step 3: Verify Changes${NC}"
echo -e "${YELLOW}Querying updated models...${NC}"

docker exec -i postgres-test psql -U $POSTGRES_USER -d $POSTGRES_DB <<SQL
SELECT
    model_id,
    name,
    provider_type::text,
    provider,
    embedding_dimensions
FROM models
WHERE model_type = 'embedding'
ORDER BY provider NULLS FIRST, model_id;
SQL

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Provider Fix Applied Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  - LMStudio gateway provider created"
echo "  - Models updated with correct provider_type and provider"
echo "  - OpenAI-compatible models: provider_type='openai', provider='LMStudio'"
echo "  - Python in-process models: provider_type='local', provider=NULL"
echo ""
echo -e "${GREEN}You can now create collections without errors!${NC}"
