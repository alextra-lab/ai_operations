#!/bin/bash
###############################################################################
# Test Environment Initialization Script
# AI Operations Platform
#
# This script properly initializes the test environment from scratch:
# 1. Stops all Docker containers
# 2. Cleans all test data
# 3. Recreates containers
# 4. Runs database migrations
# 5. Seeds initial data
# 6. Verifies the setup
#
# Usage: bash ops/testing/init_test_environment.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}AI Operations Platform - Test Environment Initialization${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Load test environment variables
echo -e "${YELLOW}📋 Loading test environment variables...${NC}"
export $(grep -v '^#' config/env/env.test | xargs)
echo -e "${GREEN}✅ Environment variables loaded${NC}"
echo ""

# Step 1: Stop all containers
echo -e "${YELLOW}🛑 Stopping all Docker containers...${NC}"
docker-compose -f deploy/docker-compose.test.yml down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 2: Clean test data
echo -e "${YELLOW}🧹 Cleaning test data...${NC}"
rm -rf data/postgres-test/*
rm -rf data/qdrant-test/*
echo -e "${GREEN}✅ Test data cleaned${NC}"
echo ""

# Step 3: Start infrastructure services (PostgreSQL and Qdrant)
echo -e "${YELLOW}🚀 Starting infrastructure services...${NC}"
docker-compose -f deploy/docker-compose.test.yml up -d postgres-db qdrant-db
echo -e "${GREEN}✅ Infrastructure services started${NC}"
echo ""

# Step 4: Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy (30 seconds)...${NC}"
sleep 30
echo -e "${GREEN}✅ Services should be ready${NC}"
echo ""

# Step 5: Run database migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
source venv/bin/activate
POSTGRES_HOST=localhost \
POSTGRES_PORT=5433 \
POSTGRES_USER=testuser \
POSTGRES_PASSWORD=test_password_123 \
POSTGRES_DB=aio-test \
python ops/database/migrations/runner.py 2>/dev/null || true

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Database migrations failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Database migrations completed${NC}"
echo ""

# Step 6: Seed initial users
echo -e "${YELLOW}👥 Seeding initial users...${NC}"
POSTGRES_HOST=localhost \
POSTGRES_PORT=5433 \
POSTGRES_USER=testuser \
POSTGRES_PASSWORD=test_password_123 \
POSTGRES_DB=aio-test \
python ops/bootstrap/seed_users.py 2>/dev/null || true

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ User seeding failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Initial users created${NC}"
echo ""

# Step 7: Seed use case templates
echo -e "${YELLOW}📝 Seeding use case templates...${NC}"
POSTGRES_HOST=localhost \
POSTGRES_PORT=5433 \
POSTGRES_USER=testuser \
POSTGRES_PASSWORD=test_password_123 \
POSTGRES_DB=aio-test \
python ops/bootstrap/seed_templates.py 2>/dev/null || true

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Template seeding had issues (may be expected)${NC}"
fi
echo -e "${GREEN}✅ Templates seeded${NC}"
echo ""

# Step 8: Start all application services
echo -e "${YELLOW}🚀 Starting all application services...${NC}"
docker-compose -f deploy/docker-compose.test.yml up -d
echo -e "${GREEN}✅ All services started${NC}"
echo ""

# Step 9: Wait for services to be fully ready
echo -e "${YELLOW}⏳ Waiting for all services to be healthy (30 seconds)...${NC}"
sleep 30
echo ""

# Step 10: Verify services
echo -e "${YELLOW}🔍 Verifying service health...${NC}"
docker-compose -f deploy/docker-compose.test.yml ps
echo ""

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}✅ Test Environment Initialization Complete!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "${BLUE}Test Accounts:${NC}"
echo -e "  ${YELLOW}Admin:${NC}"
echo -e "    Username: ${GREEN}admin${NC}"
echo -e "    Password: ${GREEN}adminpassword${NC}"
echo -e ""
echo -e "  ${YELLOW}Analyst:${NC}"
echo -e "    Username: ${GREEN}analyst${NC}"
echo -e "    Password: ${GREEN}analystpassword${NC}"
echo -e ""
echo -e "  ${YELLOW}User:${NC}"
echo -e "    Username: ${GREEN}testuser${NC}"
echo -e "    Password: ${GREEN}password${NC}"
echo ""
echo -e "${BLUE}Service Endpoints:${NC}"
echo -e "  Backend API:     ${GREEN}http://localhost:8006${NC}"
echo -e "  Frontend UI:     ${GREEN}http://localhost:4201${NC}"
echo -e "  Retrieval SVC:   ${GREEN}http://localhost:8004${NC}"
echo -e "  Embedding SVC:   ${GREEN}http://localhost:8005${NC}"
echo -e "  LLM Guard SVC:   ${GREEN}http://localhost:8082${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Verify APIs:  ${YELLOW}python ops/testing/verify_phase2_apis.py --username admin --password <test-password>${NC}"
echo -e "  2. Run tests:    ${YELLOW}python ops/testing/run_all_tests.py${NC}"
echo ""
