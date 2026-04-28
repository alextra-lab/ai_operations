# Database Initialization Guide

**AI Operations Platform**

This guide documents the complete database initialization process for the AI Operations Platform application.

## Quick Start

### Demo Database Setup

For a complete demo database setup with RBAC V2:

```bash
# Reset and initialize demo database
bash ops/operations/reset_demo_database.sh

# Verify setup
bash ops/operations/verify_demo_setup.sh
```

This creates a fresh database with:
- RBAC V2 schema (team isolation, role-based access)
- 17 demo users (all 10 system roles)
- 5 published use cases (globally visible)
- 5 draft use cases (team-isolated)
- 7 team memberships across 3 teams

See `docs/demo/DEMO_CREDENTIALS.md` for user credentials and `docs/demo/DEMO_TEST_SCENARIOS.md` for test scenarios.

### Test Environment Setup

For a complete test environment initialization from scratch:

```bash
bash ops/testing/init_test_environment.sh
```

This single script handles everything:

- Cleans test data (PostgreSQL + Qdrant)
- Starts infrastructure services
- Runs all database migrations
- Seeds initial users and templates
- Starts all application services
- Verifies the setup

## Test Accounts

After initialization, the following test accounts are available:

| Role     | Username   | Password         | Access Level |
|----------|-----------|------------------|--------------|
| Admin    | admin     | adminpassword    | Full access  |
| Analyst  | analyst   | analystpassword  | Developer    |
| User     | testuser  | password         | Basic user   |

## Service Endpoints

| Service          | URL                        | Port |
|------------------|-<http://localhost:8006>------|------|
| Backend API      | <http://localhost:4201>6>      | 8006 |
| Frontend UI      | <http://localhost:8004>1>      | 4201 |
| Retrieval SVC    | <http://localhost:8005>4>      | 8004 |
| Embedding SVC    | <http://localhost:8082>5>      | 8005 |
| LLM Guard SVC    | <http://localhost:8082>      | 8082 |
| PostgreSQL       | localhost:5433             | 5433 |
| Qdrant           | localhost:6335 (REST)      | 6335 |

## Manual Initialization Steps

If you need to run the initialization steps manually:

### 1. Load Environment Variables

```bash
export $(grep -v '^#' config/env/env.test | xargs)
```

### 2. Stop and Clean

```bash
# Stop all containers
docker-compose -f deploy/docker-compose.test.yml down

# Clean data
rm -rf data/postgres-test/*
rm -rf data/qdrant-test/*
```

### 3. Start Infrastructure

```bash
# Start PostgreSQL and Qdrant
docker-compose -f deploy/docker-compose.test.yml up -d postgres-db qdrant-db

# Wait for services to be healthy
sleep 30
```

### 4. Initialize Database

**For Fresh Installations (Recommended):**

```bash
# Load environment variables
source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')

# Run initialization script (includes RBAC V2 schema)
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f ops/database/init/000_complete_init.sql
```

**For Upgrading Existing Databases:**

If you have an existing database, use migrations instead:

```bash
# Run RBAC V2 migrations
for migration in ops/database/migrations/rbac_v2/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
    -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB \
    -f "$migration"
done
```

**Note:** The init script includes RBAC V2 schema, so fresh installations don't need separate migrations.

### 5. Seed Data

```bash
# Run seed scripts in order
for seed_file in ops/database/seed/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
    -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB \
    -f "$seed_file"
done
```

### 6. Start All Services

```bash
docker-compose -f deploy/docker-compose.test.yml up -d

# Wait for services
sleep 30
```

## Database Initialization

The database is initialized using a single comprehensive script that creates all tables, indexes, views, and policies:

**Location:** `ops/database/init/000_complete_init.sql`

**What it creates:**
- 31 tables (auth, documents, use cases, tools, models, telemetry, etc.)
- 12 analytics and utility functions
- 3 materialized views for hot documents/chunks
- 100+ indexes for performance
- Complete RLS policies for security
- All triggers for automatic timestamp updates
- **RBAC V2 schema** (ADR-060): `team_id` column in `use_cases`, `role_collection_assignments` table

**Execution time:** ~2-5 seconds

### RBAC V2 Schema (ADR-060)

The init script includes the complete RBAC V2 schema for fresh installations:

- **`use_cases.team_id`**: Column for team-based draft isolation
- **`role_collection_assignments`**: Table for role-based collection access control
- **Indexes**: Team lifecycle indexes for performance
- **Triggers**: Automatic timestamp updates

**Note:** For fresh installations, use the init script directly. For upgrading existing databases, use migrations in `ops/database/migrations/rbac_v2/`.

### Seed Data

Seed data is provided in SQL files that must be run in order:

| File | Description | Dependencies |
|------|-------------|--------------|
| `001_seed_users.sql` | 17 demo users (all 10 system roles) | init script |
| `002_seed_intents.sql` | Intent categories + system intents | users |
| `003_seed_use_cases.sql` | 5 published SOC use cases | users, intents |
| `004_seed_pricing.sql` | 15 pricing tiers (XS-XL) | users |
| `005_seed_models.sql` | LLM model registry | users, pricing |
| `006_seed_embedding_models.sql` | Embedding model registry | users, pricing |
| `007_seed_prompt_patterns.sql` | Prompt engineering patterns | users |
| `008_seed_rbac_v2_assignments.sql` | Team memberships (RBAC V2) | users |
| `009_seed_draft_use_cases.sql` | 5 draft use cases (team-isolated) | users, teams |

**RBAC V2 Seed Data:**
- `001_seed_users.sql`: Creates 17 users covering all 10 system roles
- `008_seed_rbac_v2_assignments.sql`: Assigns users to 3 teams (7 memberships)
- `009_seed_draft_use_cases.sql`: Creates 5 draft use cases demonstrating team isolation

**Fix Applied:** Removed `TO authenticated` clauses from all RLS policies in `006_tools_platform.sql`. RLS policies now apply to all users by default, with user filtering handled in the USING clauses.

## Verification

### Verify Services are Running

```bash
docker-compose -f deploy/docker-compose.test.yml ps
```

All services should show as "healthy".

### Verify Database

```bash
PGPASSWORD=test_password_123 psql -h localhost -p 5433 -U testuser -d aio-test -c "\dt"
```

Should list all database tables.

### Verify APIs

```bash
source venv/bin/activate
python ops/testing/verify_phase2_apis.py \
  --username admin \
  --password adminpassword \
  --api-url http://localhost:8006 \
  --full-test
```

## Troubleshooting

### Qdrant Issues

Qdrant can become corrupted if the container is stopped improperly. If you see errors like:

```
Failed to load local shard: Bad file descriptor
```

**Solution:** Clean and recreate Qdrant:

```bash
docker-compose -f deploy/docker-compose.test.yml stop qdrant-db
rm -rf data/qdrant-test/*
docker-compose -f deploy/docker-compose.test.yml up -d qdrant-db
```

**Important:** This desynchronizes Qdrant from PostgreSQL. You must:

2. Run full initialization

### Migration Failures

If migrations fail midway:

**Solution:** Drop and recreate the database:

```bash
PGPASSWORD=test_password_123 psql -h localhost -p 5433 -U testuser -d postgres \
  -c "DROP DATABASE IF EXISTS aio-test;"

PGPASSWORD=test_password_123 psql -h localhost -p 5433 -U testuser -d postgres \
  -c "CREATE DATABASE aio-test;"

# Then run migrations/seed again (see ops/database/README.md; or use ./ops/testing/reset_test_database.sh for test DB)
```

### Service Unhealthy

Check logs for specific services:

```bash
docker logs orchestrator-api-test --tail 50
docker logs corpus-service-test --tail 50
```

## Best Practices

1. **Always use the initialization script** (`init_test_environment.sh`) for clean setups
2. **Never manually delete Qdrant data** without also cleaning PostgreSQL
3. **Run migrations in order** - they have dependencies
4. **Check service health** before running tests
5. **Use absolute imports** in test files

## Production Initialization

For production environments, follow a similar process but:

1. Use production environment variables (`config/env/env.prod`)
2. Use different ports (8000, 4200, etc.)
3. Ensure proper secrets management
4. Run with proper user permissions
5. Configure SSL/TLS for all services
6. Set up proper backup procedures

## Related Documentation

- **Testing Guide:** `docs/testing/TESTING_GUIDE.md`
- **Database Schema:** `docs/architecture/DATABASE_SCHEMA.md`
- **Deployment Guide:** `docs/architecture/DEPLOYMENT.md`
- **API Documentation:** `docs/api/`

## Change Log

| Date       | Change                                      | Author |
|------------|---------------------------------------------|--------|
| 2025-12-10 | Added RBAC V2 schema documentation          | AI     |
| 2025-12-10 | Updated seed data list (17 users, RBAC V2)  | AI     |
| 2025-12-10 | Added demo database setup scripts reference  | AI     |
| 2025-12-10 | Clarified fresh install vs upgrade paths    | AI     |
| 2025-10-08 | Fixed migration 006 authenticated role issue| AI     |
| 2025-10-08 | Created init_test_environment.sh script     | AI     |
| 2025-10-08 | Initial documentation                       | AI     |
