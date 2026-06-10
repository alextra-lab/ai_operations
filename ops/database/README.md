# AI Operations Platform - Database Administration Guide

**Version:** 1.0.0
**PostgreSQL Version:** 17+
**Last Updated:** 2025-10-24

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Directory Structure](#directory-structure)
4. [Database Initialization](#database-initialization)
5. [Seed Data](#seed-data)
6. [Backup and Restore](#backup-and-restore)
7. [Maintenance](#maintenance)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)
10. [Reference Documentation](#reference-documentation)

---

## Overview

AI Operations Platform uses PostgreSQL 17+ as its primary data store. The database is designed for:

- **Security**: Row-level security (RLS) policies enforce multi-tenant isolation
- **Performance**: Comprehensive indexing strategy for sub-second query response
- **Audit**: Complete audit trail of all security-sensitive operations
- **Scalability**: Partitioning-ready design for high-volume deployments

### Key Features

- **29 Tables**: Authentication, documents, use cases, query history, tools, models, intents
- **12 Functions**: Analytics, token tracking, query forking
- **3 Views**: Hot documents/chunks analytics
- **Complete RLS**: Row-level security on all sensitive tables
- **Full Text Search**: GIN indexes for document and query text search
- **JSONB Configuration**: Flexible use case and model configuration

---

## Quick Start

> **Containerized stack? You don't need any of this.** The `db-init` compose
> service (`ops/database/init_db.py`, pure Python/psycopg — no psql required)
> applies init → seeds → migrations → intent defaults automatically on
> `make up`. The commands below are the manual host-side equivalent.

### Prerequisites

- PostgreSQL 17+ installed
- `psql-17` command-line tool (for the manual commands below)
- Database created (default: `aio` or `aio-test`)
- Environment variables configured in `.env` or `env.test`

### Initialize Database (Development/Production)

```bash
# Load environment variables
export $(grep -v '^#' config/env/.env | xargs)

# Initialize database schema
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f ops/database/init/000_complete_init.sql

# Seed default data
for seed_file in ops/database/seed/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
    -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB \
    -f "$seed_file"
done

# (No post-init migrations are needed for a fresh build — see note below.)
```

### Post-init migrations

As of **AIO-65 (2026-05-31)**, migrations **027–039 have been consolidated into
`000_complete_init.sql`** and their files deleted. A fresh `init + seed` now
produces the complete, final schema (including intent capability profile columns,
the `intent_model_defaults` table, and the `output_templates` table) with **no
migration step required**.

`./ops/database/run_migrations.sh` and the `ops/database/migrations/` directory
remain in place as the mechanism for **future** migrations (numbered > 039). The
runner is a thin wrapper around `init_db.py --migrations-only` (host prerequisite:
`pip install -r requirements-ops.txt` — psql is not needed). It records applied
files in `schema_migrations` so re-runs skip already-applied files. Data operations that previously lived in migrations 033/034/036/037 now live
in numbered `ops/database/seed/` files (012–014) and run during the seed phase.

### Initialize Test Database

```bash
# Load test environment variables
export $(grep -v '^#' config/env/env.test | xargs)

# Use the same initialization commands as above
```

### Verify Installation

```bash
# Check table count (should be 39)
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# Check seed data
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT username, role FROM users ORDER BY username;"
```

---

## Recent Changes

### 2026-05-31: AIO-65 — Migrations 027–039 Consolidated Into Init

✅ **Folded into init:** DDL from migrations 036–039 — intent_types capability
   columns (`default_sampling_preset`, `default_output_format`,
   `recommended_capabilities`), the `intent_model_defaults` table (+ `temperature`
   column), and the `output_templates` table.
✅ **Moved to seeds:** data operations from migrations 033/034/036/037 →
   `seed/012_intent_capability_profiles_data.sql`, `seed/013_rename_template_ids.sql`,
   `seed/014_set_documents_as_default_collection.sql`.
✅ **Deleted:** all 16 migration files 027–039. Migrations 027–035 were already
   no-ops against init; 036–039 DDL is now authoritative in init. Migration
   033_fix was fully redundant with `seed/006` and `seed/010`.
✅ **Verified:** schema-equivalence between the old (init+seed+migrations) and new
   (init+seed) flows confirmed via Postgres 17 schema dump diff — structurally
   identical.

**Authorized:** Alex 2026-05-31 (app not in production).

### 2025-10-26: Database Consolidation Complete

✅ **Consolidated:** All schema and seed data into `ops/database/`
✅ **Updated:** `003_seed_use_cases.sql` with complete input_fields
✅ **Archived:** Legacy Python seed scripts (now use SQL only)
✅ **Removed:** Old migration system (replaced with single init script)

**What changed:**

- Single comprehensive init script (`000_complete_init.sql`)
- 5 sequential SQL seed files with all required data
- Python seed scripts archived (use SQL files instead)
- Old incremental migration system removed

### 2025-10-24: ADR-041 Role-Based Permissions

✅ **Removed:** `role_intent_permissions` table (incorrect architecture)
✅ **Added:** `role_use_case_assignments` table (correct architecture)
✅ **Updated:** Support for dynamic custom roles (no hardcoded CHECK constraints)

**Impact:** Use Cases are now correctly recognized as the permission boundary (NOT Intent Types). Supports unlimited custom roles for multi-department deployments.

See: `docs/development/adrs/ADR-041-Role-Based-Use-Case-Permissions.md`

---

## Directory Structure

```text
ops/database/
├── init/
│   └── 000_complete_init.sql       # Complete schema initialization
├── seed/
│   ├── 001_seed_users.sql          # Default users (admin, analyst, testuser)
│   ├── 002_seed_intents.sql        # Intent categories and system intents
│   ├── 003_seed_use_cases.sql      # Default SOC use cases
│   ├── 004_seed_pricing.sql        # LLMaaS pricing tiers
│   ├── 005_seed_models.sql         # LLM models registry
│   ├── 006_seed_embedding_models.sql # Embedding models registry
│   ├── 007_seed_prompt_patterns.sql  # Prompt pattern library
│   ├── 008_seed_rbac_v2_assignments.sql # RBAC V2 assignments
│   ├── 009_seed_draft_use_cases.sql  # Draft use cases
│   ├── 010_seed_gateway_providers.sql # Gateway providers
│   ├── 011_seed_gateway_rate_limits_defaults.sql # Gateway rate limits
│   ├── 012_intent_capability_profiles_data.sql # Intent capability data (ex-migration 036)
│   ├── 013_rename_template_ids.sql   # Template ID rename (ex-migration 037)
│   └── 014_set_documents_as_default_collection.sql # Default collection (ex-migration 034)
├── migrations/
│   └── rbac_v2/                    # RBAC V2 upgrade migrations (untouched)
├── rollback/
│   └── 000_drop_all.sql            # Emergency rollback (development only)
├── docs/
│   ├── SCHEMA.md                   # Complete schema documentation
│   ├── ERD.md                      # Entity-relationship diagrams
│   ├── INDEXES.md                  # Index strategy and performance
│   └── RLS_POLICIES.md             # Row-level security documentation
├── init_db.py                      # db-init container entrypoint (init → seeds → migrations)
├── run_migrations.sh               # Host wrapper: init_db.py --migrations-only (FUTURE migrations > 039)
├── Dockerfile                      # db-init image (pure Python, no psql/apt)
└── README.md                       # This file

**Note:** Architecture Decision Records (ADRs) related to the database are located in:
- `docs/development/adrs/ADR-037-uuid-primary-keys.md`
- `docs/development/adrs/ADR-038-jsonb-for-config.md`
- `docs/development/adrs/ADR-039-rls-security-model.md`
- `docs/development/adrs/ADR-040-telemetry-vs-transcripts.md`
- `docs/development/adrs/ADR-021-Collection-Based-Document-Management.md`
```

---

## Database Initialization

### Complete Initialization Script

The `000_complete_init.sql` script creates the entire database schema in one transaction:

**What it creates:**

- 39 tables (auth, documents, use cases, tools, models, gateway, telemetry, intents, etc.)
- 12 analytics and utility functions
- 3 materialized views for hot documents/chunks
- 100+ indexes for performance
- Complete RLS policies for security
- All triggers for automatic timestamp updates

**Execution time:** ~2-5 seconds on modern hardware

**Idempotent:** Can be safely re-run (uses `IF NOT EXISTS`)

### Manual Step-by-Step (Alternative)

If you prefer to understand each component:

1. **Extensions and Schemas**

   ```sql
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE SCHEMA IF NOT EXISTS aio;
   ```

2. **Helper Functions** - RLS and timestamp management

3. **Tables** - In dependency order (no foreign key violations)

4. **Indexes** - Performance optimization

5. **RLS Policies** - Security enforcement

6. **Triggers** - Automatic updated_at timestamps

---

## Seed Data

### Execution Order (Important!)

Seeds must be run in order due to foreign key dependencies:

| Order | File | Description | Dependencies |
|-------|------|-------------|--------------|
| 1 | `001_seed_users.sql` | Admin, analyst, testuser | init script |
| 2 | `002_seed_intents.sql` | Intent categories + system intents | users |
| 3 | `003_seed_use_cases.sql` | 5 default SOC use cases | users, intents |
| 4 | `004_seed_pricing.sql` | 15 pricing tiers (XS-XL) | users |
| 5 | `005_seed_models.sql` | LLM model registry | users, pricing |
| 6 | `006_seed_embedding_models.sql` | Embedding model registry | users |

### Seed Data Contents

#### 001_seed_users.sql

- **admin** (role: admin) - Full system access
- **analyst** (role: developer) - Development privileges
- **testuser** (role: user) - Standard user

⚠️ **Default password for all users:** `admin123` (change in production!)

#### 002_seed_intents.sql

- **Categories:** GENERAL, SECURITY, LEGAL, HR, FINANCE, COMPLIANCE
- **System Intents:** QUERY, RULE_GENERATION, SUMMARIZATION, ENRICHMENT
- **Role Permissions:** admin, analyst, developer, user

#### 003_seed_use_cases.sql

- Threat Analysis (QUERY)
- Log Investigation (QUERY)
- IOC Lookup (ENRICHMENT)
- Policy Review (QUERY)
- Incident Summary (SUMMARIZATION)

#### 004_seed_pricing.sql

- 15 pricing tiers (5 plan sizes × 3 model classes)
- Rate limits: 2,000 - 275,700 TPM
- Pricing: 1.10 - 148.90 KEUR per 1M input tokens

#### 005_seed_models.sql

- **OpenAI:** gpt-4o-mini, gpt-4o, gpt-4-turbo
- **Anthropic:** claude-3-sonnet, claude-3-opus
- **Model Configs:** foundation-sec, phi-4-mini, mistral-large, mistral-small, gpt-oss, llama-3.3

#### 006_seed_embedding_models.sql

- **Nomic Embed v1.5:** q4_k_m (768D), f16 (768D)
- **BGE-M3:** 1024D multilingual
- **E5 Mistral 7B:** 4096D instruction-tuned
- **Multi-QA MiniLM L6:** 384D compact

💡 **Note:** System currently uses single embedding model via `DEFAULT_EMBEDDING_MODEL` env var. Multi-model support planned for Phase 5.

---

## Backup and Restore

### Full Database Backup

```bash
# Production backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --format=custom \
  --file=backup_$(date +%Y%m%d_%H%M%S).dump

# Compressed backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --format=custom --compress=9 \
  --file=backup_$(date +%Y%m%d_%H%M%S).dump.gz
```

### Schema-Only Backup

```bash
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --schema-only \
  --file=schema_$(date +%Y%m%d_%H%M%S).sql
```

### Data-Only Backup

```bash
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --data-only \
  --file=data_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

```bash
# From custom format
PGPASSWORD=$POSTGRES_PASSWORD pg_restore \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --clean --if-exists \
  backup_YYYYMMDD_HHMMSS.dump

# From SQL format
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -f backup_YYYYMMDD_HHMMSS.sql
```

### Automated Backup Strategy (Recommended)

```bash
#!/bin/bash
# Add to crontab: 0 2 * * * /path/to/backup.sh

BACKUP_DIR="/path/to/backups"
RETENTION_DAYS=30

# Daily backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  --format=custom --compress=9 \
  --file="$BACKUP_DIR/daily_$(date +%Y%m%d).dump"

# Delete old backups
find "$BACKUP_DIR" -name "daily_*.dump" -mtime +$RETENTION_DAYS -delete
```

---

## Maintenance

### Vacuum and Analyze

```sql
-- Vacuum all tables
VACUUM ANALYZE;

-- Vacuum specific table
VACUUM ANALYZE users;

-- Full vacuum (requires more locks)
VACUUM FULL ANALYZE documents;
```

### Reindex

```sql
-- Reindex all tables
REINDEX DATABASE aio;

-- Reindex specific table
REINDEX TABLE use_cases;

-- Reindex specific index
REINDEX INDEX idx_documents_title_search;
```

### Statistics Update

```sql
-- Update all table statistics
ANALYZE;

-- Update specific table statistics
ANALYZE usage_stats;
```

### Check Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
```

### Find Slow Queries

```sql
-- Enable pg_stat_statements extension first
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 slowest queries
SELECT
    substring(query, 1, 100) AS short_query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Security

### Row-Level Security (RLS)

All sensitive tables have RLS enabled. See [RLS_POLICIES.md](../../docs/architecture/database/RLS_POLICIES.md) for complete documentation.

**Key policies:**

- Users can only see their own data
- Admins can see all data
- Service accounts have special permissions for background tasks

### Encryption at Rest

- Use PostgreSQL's transparent data encryption (TDE) for production
- Store sensitive values in `tool_secrets.encrypted_value` using pgcrypto
- Never store plain-text API keys or passwords

### Connection Security

```bash
# Always use SSL in production
export PGSSLMODE=require

# Verify server certificate
export PGSSLMODE=verify-full
export PGSSLROOTCERT=/path/to/root.crt
```

### User Management

```sql
-- Create read-only user
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE aio TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Create application user
CREATE USER app_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE aio TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT version();"

# Check if database exists
PGPASSWORD=$POSTGRES_PASSWORD psql-17 \
  -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER -d postgres \
  -c "SELECT datname FROM pg_database WHERE datname = 'aio';"
```

### Missing Tables

```sql
-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Check for missing tables
SELECT 'users' AS expected_table WHERE NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'users');
```

### Foreign Key Violations

```sql
-- Find missing foreign key references
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE contype = 'f'
  AND connamespace = 'public'::regnamespace;
```

### RLS Policy Debugging

```sql
-- Disable RLS for troubleshooting (superuser only)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Re-enable after debugging
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Check which policies are active
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

### Performance Issues

```sql
-- Check for missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    null_frac
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND null_frac < 0.5
ORDER BY tablename, attname;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;
```

---

## Reference Documentation

### Detailed Documentation

- **[SCHEMA.md](../../docs/architecture/database/SCHEMA.md)** - Complete schema documentation with all tables, columns, and relationships
- **[ERD.md](../../docs/architecture/database/ERD.md)** - Entity-Relationship Diagrams
- **[INDEXES.md](../../docs/architecture/database/INDEXES.md)** - Index strategy and performance tuning
- **[RLS_POLICIES.md](../../docs/architecture/database/RLS_POLICIES.md)** - Row-level security policies
- **[ADRs](../../docs/development/adrs/)** - Architecture Decision Records (database-related: ADR-021, ADR-037-040)

### External Resources

- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [PostgreSQL Row-Level Security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

## Support and Contributions

### Reporting Issues

- Database schema issues: Create an issue with `[DATABASE]` prefix
- Performance problems: Include `EXPLAIN ANALYZE` output
- Data integrity issues: Include steps to reproduce

### Best Practices

1. **Always backup before schema changes**
2. **Test migrations in development first**
3. **Use transactions for manual data changes**
4. **Monitor database performance regularly**
5. **Keep PostgreSQL updated to latest patch version**

---

**Last Updated:** 2025-10-24
**Maintainer:** AI Operations Platform Team
**PostgreSQL Version:** 17+
