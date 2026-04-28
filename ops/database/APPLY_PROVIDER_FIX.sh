#!/bin/bash
# ============================================================================
# Apply Provider Fix to Existing Database
# ============================================================================
# This script applies the provider type fixes without resetting the database
# Date: 2025-12-11
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Applying Provider Type Fix${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check environment variables
if [ -z "$POSTGRES_HOST" ]; then
    export POSTGRES_HOST="localhost"
fi
if [ -z "$POSTGRES_PORT" ]; then
    export POSTGRES_PORT="5432"
fi
if [ -z "$POSTGRES_USER" ]; then
    export POSTGRES_USER="postgres"
fi
if [ -z "$POSTGRES_DB" ]; then
    export POSTGRES_DB="aio"
fi

echo -e "${YELLOW}Database Configuration:${NC}"
echo "  Host: $POSTGRES_HOST"
echo "  Port: $POSTGRES_PORT"
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

    PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
        -h $POSTGRES_HOST \
        -p $POSTGRES_PORT \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        -f "$file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed${NC}"
        exit 1
    fi
}

# Step 1: Create LMStudio gateway provider (if not exists)
echo -e "${GREEN}Step 1: Create LMStudio Gateway Provider${NC}"
run_sql "ops/database/seed/010_seed_gateway_providers.sql" "LMStudio gateway provider"

# Step 2: Apply migration to fix existing models
echo -e "${GREEN}Step 2: Fix Existing Model Provider Types${NC}"
run_sql "ops/database/migrations/033_fix_embedding_model_provider_type.sql" "Migration 033 - Provider type fix"

# Step 3: Verify the changes
echo -e "${GREEN}Step 3: Verify Changes${NC}"
echo -e "${YELLOW}Querying updated models...${NC}"

PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
    -h $POSTGRES_HOST \
    -p $POSTGRES_PORT \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB \
    -c "
    SELECT
        model_id,
        name,
        provider_type::text,
        provider,
        embedding_dimensions
    FROM models
    WHERE model_type = 'embedding'
    ORDER BY provider NULLS FIRST, model_id;
    "

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
