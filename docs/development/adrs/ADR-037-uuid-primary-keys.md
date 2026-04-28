# ADR-001: UUID Primary Keys for All Tables

**Status:** Accepted
**Date:** 2025-10-24
**Deciders:** Database Team, Security Team

## Context

AI Operations Platform requires a primary key strategy that supports:
- Distributed systems (multiple services, potential future sharding)
- Security (non-enumerable identifiers)
- Multi-tenant isolation
- Air-gapped deployments (no central ID authority)

## Decision

We will use **UUID (Universally Unique Identifiers)** as primary keys for all tables.

**Implementation:**
```sql
CREATE TABLE example (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

## Rationale

### Advantages

1. **Distributed-Friendly**
   - IDs generated client-side or in multiple database instances
   - No coordination required for ID generation
   - Supports future horizontal scaling

2. **Security**
   - Non-sequential - cannot enumerate all records
   - Unpredictable - protects against timing attacks
   - Harder to guess valid IDs

3. **Global Uniqueness**
   - Collision probability negligible (2^122 possible UUIDs)
   - Safe to merge data from multiple environments
   - Supports air-gapped deployments with offline ID generation

4. **Cross-System References**
   - Same ID can reference entity across services
   - Qdrant uses UUIDs for chunks - consistency with vector DB
   - API responses can expose IDs without security concern

5. **Audit Trail**
   - IDs immutable across environments
   - Development → Staging → Production migrations preserve IDs
   - Easier debugging and log correlation

### Trade-Offs

1. **Storage Size**
   - 16 bytes vs 4 bytes (integer) or 8 bytes (bigint)
   - **Impact:** ~12 bytes per row overhead
   - **Mitigation:** Modern SSDs handle this efficiently; compression helps

2. **Index Size**
   - Larger B-tree indexes
   - **Impact:** ~3x larger than integer indexes
   - **Mitigation:** PostgreSQL handles UUID indexes well; use partial indexes

3. **Random Insertion**
   - Non-sequential UUIDs cause index page splits
   - **Impact:** Slightly slower inserts vs sequential IDs
   - **Mitigation:**
     - PostgreSQL TOAST reduces fragmentation
     - Regular VACUUM and REINDEX maintenance
     - Consider UUIDv7 (time-ordered) for high-write tables if needed

4. **Human Readability**
   - Harder to type/remember than integers
   - **Mitigation:** Use application-level friendly IDs (e.g., `use_case_id`) where appropriate

## Alternatives Considered

### 1. Auto-Incrementing Integers

**Rejected because:**
- Distributed systems require coordination
- Sequential IDs expose enumeration attacks
- Row count visible to users
- Merge conflicts during data migrations

### 2. Composite Keys

**Rejected because:**
- Complex foreign key relationships
- Larger join overhead
- Application complexity

### 3. ULID (Universally Unique Lexicographically Sortable Identifier)

**Considered but deferred:**
- Time-ordered insertions benefit indexes
- Better clustering
- **Decision:** Use standard UUIDs now, migrate high-write tables to UUIDv7 (RFC 9562) if needed

## Consequences

### Positive

- ✅ Secure, non-enumerable identifiers
- ✅ Distributed system ready
- ✅ Consistent with Qdrant chunk IDs
- ✅ Simplified multi-environment workflows

### Negative

- ❌ Larger database size (~15% overhead)
- ❌ Slightly slower inserts
- ❌ Less human-readable

### Neutral

- ID generation can happen anywhere (database, application, client)
- Foreign keys still enforce referential integrity
- Queries by ID still use indexes efficiently

## Implementation Notes

### Standard Pattern

```sql
CREATE TABLE table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

### Human-Readable Identifiers

Where appropriate, add application-level unique identifiers:

```sql
CREATE TABLE use_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "threat-analysis-basic"
    ...
);
```

### Index Optimization

For high-frequency UUID lookups, consider BRIN indexes for time-ordered data:

```sql
-- For time-series data with UUID clustering
CREATE INDEX idx_created_at_brin ON table_name USING BRIN(created_at);
```

## Monitoring

**Key Metrics:**
- Table sizes: Monitor growth relative to row count
- Index efficiency: Check index bloat quarterly
- Insert performance: Benchmark against integer PK baseline

**Acceptable Performance:**
- UUID table: 10,000 inserts/sec (single connection)
- UUID index: 99%+ hit ratio
- Index bloat: < 30% after 6 months

## References

### Related ADRs
- **[ADR-039: RLS Security Model](ADR-039-rls-security-model.md)** - Uses UUIDs in RLS session variables and policies
- **[ADR-049: Unified Authentication and Security Implementation](ADR-049-Unified-Authentication-Security-Implementation.md)** - UUIDs for secure, non-enumerable user identification

### External Resources
- [PostgreSQL UUID Documentation](https://www.postgresql.org/docs/17/datatype-uuid.html)
- [UUID RFC 4122](https://www.rfc-editor.org/rfc/rfc4122)
- [UUIDv7 RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html)
- [PostgreSQL Index Bloat Analysis](https://wiki.postgresql.org/wiki/Index_Maintenance)

## Revision History

- 2025-11-02: Added cross-reference to ADR-049 (authentication)
- 2025-10-24: Initial decision (all tables use UUID)
