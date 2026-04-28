# Database Documentation Index

**AI Operations Platform - Database Reference**

---

## 🚀 Quick Start

**New deployment?** Start here:
1. [README.md](README.md) - Administration guide
2. [init/000_complete_init.sql](init/000_complete_init.sql) - Run this first
3. [seed/*.sql](seed/) - Run these in order (001-011)

---

## 📋 Reference Documentation

### Essential Reading

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [README.md](README.md) | Database administration guide | Setup, backup, maintenance |
| [SCHEMA.md](../../docs/architecture/database/SCHEMA.md) | Complete schema reference | Understanding tables/columns |
| [ERD.md](../../docs/architecture/database/ERD.md) | Entity-relationship diagrams | Understanding relationships |
| [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) | Pre-release consolidation summary | Understanding migration history |

### Advanced Topics

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [INDEXES.md](../../docs/architecture/database/INDEXES.md) | Index strategy and performance | Performance tuning |
| [RLS_POLICIES.md](../../docs/architecture/database/RLS_POLICIES.md) | Row-level security | Security configuration |

### Architecture Decisions

| ADR | Title | Topic |
|-----|-------|-------|
| [ADR-001](docs/ADRs/ADR-001-uuid-primary-keys.md) | UUID Primary Keys | Why UUIDs vs integers |
| [ADR-002](docs/ADRs/ADR-002-jsonb-for-config.md) | JSONB for Configuration | Why JSONB vs normalized tables |
| [ADR-003](docs/ADRs/ADR-003-rls-security-model.md) | RLS Security Model | Why RLS vs application ACL |
| [ADR-004](docs/ADRs/ADR-004-telemetry-vs-transcripts.md) | Telemetry Without Transcripts | Why run_manifests is PII-free |

---

## 📁 File Structure

```
ops/database/
├── init/
│   └── 000_complete_init.sql         # Single comprehensive init (31 tables)
│
├── seed/
│   ├── 001_seed_users.sql            # Default users (RBAC V2)
│   ├── 002_seed_intents.sql          # Intent system (6 categories, 4 intents)
│   ├── 003_seed_use_cases.sql        # SOC use cases
│   ├── 004_seed_pricing.sql          # Pricing tiers
│   ├── 005_seed_models.sql           # Model registry
│   ├── 006_seed_embedding_models.sql # Embedding models
│   ├── 007_seed_prompt_patterns.sql  # Prompt patterns
│   ├── 008_seed_rbac_v2_assignments.sql # RBAC V2 team assignments
│   ├── 009_seed_draft_use_cases.sql  # Draft use cases
│   ├── 010_seed_gateway_providers.sql   # Gateway providers
│   └── 011_seed_gateway_rate_limits_defaults.sql # Gateway rate limits (P2-T5)
│
├── rollback/
│   └── 000_drop_all.sql              # Emergency rollback (requires unlock)
│
├── docs/
│   ├── SCHEMA.md                     # Tables, columns, relationships
│   ├── ERD.md                        # Entity-relationship diagrams
│   ├── INDEXES.md                    # 100+ indexes documented
│   ├── RLS_POLICIES.md               # 40+ security policies
│   └── ADRs/                         # Architecture decisions
│       ├── ADR-001-uuid-primary-keys.md
│       ├── ADR-002-jsonb-for-config.md
│       ├── ADR-003-rls-security-model.md
│       └── ADR-004-telemetry-vs-transcripts.md
│
├── README.md                         # Main admin guide (START HERE)
├── INDEX.md                          # This file
└── MIGRATION_SUMMARY.md              # Pre-release consolidation summary
```

---

## 🔍 Find Information By Topic

### I want to...

**Initialize a new database**
→ [README.md](README.md#quick-start)

**Understand the schema**
→ [SCHEMA.md](../../docs/architecture/database/SCHEMA.md)

**See table relationships**
→ [ERD.md](../../docs/architecture/database/ERD.md)

**Optimize query performance**
→ [INDEXES.md](../../docs/architecture/database/INDEXES.md)

**Configure security policies**
→ [RLS_POLICIES.md](../../docs/architecture/database/RLS_POLICIES.md)

**Understand design decisions**
→ [docs/ADRs/](docs/ADRs/)

**Backup the database**
→ [README.md](README.md#backup-and-restore)

**Troubleshoot issues**
→ [README.md](README.md#troubleshooting)

**Rollback everything**
→ [rollback/000_drop_all.sql](rollback/000_drop_all.sql)

---

## 📊 Schema At-A-Glance

| Domain | Tables | Key Features |
|--------|--------|--------------|
| **Authentication** | 3 | Multi-role, JWT sessions |
| **Documents** | 2 | Metadata only, Qdrant integration |
| **Use Cases** | 3 | JSONB config, versioned templates |
| **Query History** | 3 | Threading, forking |
| **Token Tracking** | 1 | Usage analytics, cost tracking |
| **Tools** | 5 | MCP integration, encrypted secrets |
| **Models** | 3 | Registry, cache, pricing |
| **Telemetry** | 1 | PII-free metrics |
| **Pricing** | 2 | 15 tiers, audit trail |
| **Intents** | 4 | Dynamic types, RBAC |
| **Security** | 2 | Encryption keys, audit logs |

**Total:** 31 tables, 12 functions, 3 views, 100+ indexes

---

## 🔐 Security Summary

- **RLS Enabled:** 16 of 31 tables
- **Encryption:** tool_secrets uses pgcrypto
- **Audit:** All sensitive operations logged
- **Isolation:** Multi-tenant with center_id
- **Compliance:** GDPR, CCPA, SOC 2 ready

---

## 📞 Getting Help

- **General questions:** See [README.md](README.md)
- **Schema questions:** See [SCHEMA.md](../../docs/architecture/database/SCHEMA.md)
- **Performance issues:** See [INDEXES.md](../../docs/architecture/database/INDEXES.md)
- **Security questions:** See [RLS_POLICIES.md](../../docs/architecture/database/RLS_POLICIES.md)
- **Architecture questions:** See [docs/ADRs/](docs/ADRs/)

---

**Last Updated:** 2025-10-24
**Version:** 1.0.0
