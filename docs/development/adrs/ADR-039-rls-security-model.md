# ADR-003: Row-Level Security (RLS) Model

**Status:** Accepted
**Date:** 2025-10-24
**Deciders:** Security Team, Database Team, Backend Team

## Context

AI Operations Platform is a multi-tenant enterprise platform that requires:
- **Data isolation** - Users see only their own data
- **Role-based access** - Different permissions for admin/developer/user
- **Use case permissions** - Granular access to specific use cases
- **Audit compliance** - All data access must be logged and controllable

**Security Requirements:**
- GDPR/CCPA compliance (data isolation)
- SOC 2 Type II (access controls)
- Zero-trust architecture
- Air-gapped deployment (no external auth)

## Decision

We will use **PostgreSQL Row-Level Security (RLS)** as the primary mechanism for data isolation and access control.

**Key Components:**
1. Session context functions
2. RLS policies on all sensitive tables
3. Role-based permissions
4. Use case-based access control

## Rationale

### Why RLS Over Alternatives

**Advantages of RLS:**

1. **Database-Enforced Security**
   - Cannot bypass via SQL injection
   - Protects against application bugs
   - Defense in depth (even if app compromised)

2. **Performance**
   - Database applies filters at query planning time
   - Index-optimized filtering
   - No application-layer overhead

3. **Simplicity**
   - Single source of truth (database)
   - No complex application ACL logic
   - Easier to audit and verify

4. **Multi-Service Architecture**
   - Multiple services can query database safely
   - Consistent security across all API endpoints
   - No need to duplicate authorization logic

5. **Compliance**
   - Auditable access controls
   - Database logs show RLS enforcement
   - Meets regulatory requirements

### Trade-Offs

1. **Session Context Required**
   - Must set `aio.user_id` and `aio.user_roles` before queries
   - **Mitigation:** Middleware sets context automatically

2. **Testing Complexity**
   - Must set session context in tests
   - **Mitigation:** Test fixtures handle context setup

3. **Performance for Complex Policies**
   - EXISTS subqueries can be slow
   - **Mitigation:** Proper indexing on FK columns

4. **Migration Complexity**
   - Policies must be updated when schema changes
   - **Mitigation:** Policy changes tested in staging first

## Alternatives Considered

### 1. Application-Layer ACL

**Example:**
```python
# Application checks permissions
def get_queries(user_id):
    if user.role == "admin":
        return db.query("SELECT * FROM query_history")
    else:
        return db.query("SELECT * FROM query_history WHERE user_id = %s", user_id)
```

**Rejected because:**
- Must duplicate logic in every service
- SQL injection could bypass checks
- Complex to maintain as requirements evolve
- Hard to audit (authorization in code, not DB)

### 2. View-Based Security

**Example:**
```sql
CREATE VIEW user_query_history AS
SELECT * FROM query_history
WHERE user_id = current_user;
```

**Rejected because:**
- Only protects SELECT, not INSERT/UPDATE/DELETE
- Must maintain separate views for each role
- Doesn't support dynamic session context
- Harder to compose (view of view complexity)

### 3. Query Rewriting Middleware

**Example:**
```python
# Middleware rewrites queries to add WHERE clauses
original_query = "SELECT * FROM query_history"
rewritten_query = f"{original_query} WHERE user_id = '{user_id}'"
```

**Rejected because:**
- Extremely error-prone
- Can't handle complex queries (joins, subqueries)
- Brittle (breaks with SQL syntax changes)
- Security risk (bypassing middleware)

## Implementation

### Session Context Functions

```sql
-- Get current user UUID
CREATE FUNCTION aio.current_user_uuid()
RETURNS uuid AS $$
    SELECT NULLIF(current_setting('aio.user_id', true), '')::uuid;
$$ LANGUAGE SQL STABLE;

-- Get current user roles
CREATE FUNCTION aio.current_user_roles()
RETURNS text[] AS $$
    SELECT regexp_split_to_array(
        trim(both '{}' FROM current_setting('aio.user_roles', true)),
        '\s*,\s*'
    );
$$ LANGUAGE SQL STABLE;

-- Check if user has role
CREATE FUNCTION aio.user_has_role(target_role text)
RETURNS boolean AS $$
    SELECT target_role = ANY(aio.current_user_roles());
$$ LANGUAGE SQL STABLE;
```

### Policy Patterns

**Pattern 1: User Isolation**
```sql
-- Users see only their own data
CREATE POLICY user_isolation ON query_history
FOR SELECT
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);
```

**Pattern 2: Role-Based Access**
```sql
-- Admins can manage all
CREATE POLICY admin_manage ON use_cases
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));
```

**Pattern 3: Use Case Permissions**
```sql
-- Users see use cases they're assigned to
CREATE POLICY use_case_access ON use_cases
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_use_case_assignments
        WHERE use_case_id = use_cases.id
          AND user_id = aio.current_user_uuid()
          AND status = 'active'
    )
);
```

### Application Integration

```python
# FastAPI middleware sets session context
@app.middleware("http")
async def set_rls_context(request: Request, call_next):
    async with db.pool.connection() as conn:
        user_id = request.state.user.id
        user_roles = request.state.user.roles

        await conn.execute("SET LOCAL aio.user_id = $1", user_id)
        await conn.execute("SET LOCAL aio.user_roles = $1",
                          '{' + ','.join(user_roles) + '}')

        response = await call_next(request)
        return response
```

## Security Considerations

### 1. Bypass Protection

**RLS cannot be bypassed except by:**
- Superusers
- Table owners (if not using FORCE ROW LEVEL SECURITY)

**Mitigation:**
```sql
-- FORCE prevents table owners from bypassing
ALTER TABLE query_history FORCE ROW LEVEL SECURITY;

-- Don't use superuser for application connections
-- Create dedicated app user with minimal privileges
```

### 2. Service Accounts

**Service/background processes need special handling:**

```sql
-- Dedicated service role
CREATE POLICY service_access ON audit_logs
FOR INSERT
WITH CHECK (aio.user_has_role('service'));

-- Service can insert, but not read sensitive data
CREATE POLICY service_token_insert ON token_usage
FOR INSERT
WITH CHECK (aio.user_has_role('service'));
```

### 3. Admin Escape Hatch

**Admins can see all data, but it's logged:**

```sql
-- Admin access always allowed
CREATE POLICY admin_all ON query_history
FOR ALL
USING (aio.user_has_role('admin'));

-- But admin actions are audited
INSERT INTO audit_logs (actor_user_id, action, resource_type, ...)
VALUES (...);
```

## Performance Optimization

### 1. Index FK Columns Used in Policies

```sql
-- RLS policy uses user_id
CREATE POLICY user_isolation ON query_history
USING (user_id = aio.current_user_uuid());

-- Ensure user_id is indexed
CREATE INDEX idx_query_history_user_id ON query_history(user_id);
```

### 2. Avoid Complex Subqueries in Hot Paths

**Slow:**
```sql
CREATE POLICY slow_policy ON table
USING (
    id IN (
        SELECT id FROM other_table
        WHERE complex_condition
          AND another_complex_join
    )
);
```

**Fast:**
```sql
CREATE POLICY fast_policy ON table
USING (user_id = aio.current_user_uuid());
```

### 3. Use STABLE Functions

```sql
-- STABLE allows PostgreSQL to cache result during query
CREATE FUNCTION aio.current_user_uuid()
RETURNS uuid
LANGUAGE SQL STABLE;  -- Not VOLATILE!
```

## Testing Strategy

### Unit Tests

```python
async def test_rls_user_isolation():
    # Set session as user1
    await conn.execute("SET LOCAL aio.user_id = $1", user1_id)
    await conn.execute("SET LOCAL aio.user_roles = $1", '{user}')

    # Query should only return user1's data
    result = await conn.fetch("SELECT * FROM query_history")
    assert all(row['user_id'] == user1_id for row in result)

    # Reset session
    await conn.execute("RESET aio.user_id")
    await conn.execute("RESET aio.user_roles")
```

### Integration Tests

```python
async def test_rls_admin_access():
    # Admin sees all data
    await conn.execute("SET LOCAL aio.user_id = $1", admin_id)
    await conn.execute("SET LOCAL aio.user_roles = $1", '{admin}')

    result = await conn.fetch("SELECT * FROM query_history")
    assert len(result) > 0  # Admin sees all queries
```

### Debugging

```sql
-- Check current RLS context
SELECT
    aio.current_user_uuid() AS user_id,
    aio.current_user_roles() AS roles;

-- Temporarily disable RLS (superuser only, for debugging)
ALTER TABLE query_history DISABLE ROW LEVEL SECURITY;
SELECT * FROM query_history;  -- See all data
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;
```

## Monitoring

**Key Metrics:**
- RLS policy hit rate (query plans should use policies)
- Session context set errors
- Admin access frequency (audit unusual patterns)

**Alerts:**
- Session context not set (queries return 0 rows unexpectedly)
- Performance degradation (RLS subqueries not using indexes)
- Excessive admin access (potential abuse)

## Migration Path

If RLS becomes a performance bottleneck:

1. **Identify slow policy** (EXPLAIN ANALYZE shows RLS filter cost)
2. **Optimize indexes** on columns used in policy
3. **Simplify policy logic** (avoid complex subqueries)
4. **Consider materialized permissions** (cache assignments in memory)

**Last resort:** Move to application-layer ACL for specific hot tables

## References

### Related ADRs
- **[ADR-037: UUID Primary Keys](ADR-037-uuid-primary-keys.md)** - UUIDs used in RLS session variables and policies
- **[ADR-049: Unified Authentication and Security Implementation](ADR-049-Unified-Authentication-Security-Implementation.md)** - JWT authentication provides user context for RLS middleware

### External Resources
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [RLS Performance Tuning](https://wiki.postgresql.org/wiki/Row_Security)
- OWASP: Defense in Depth

## Revision History

- 2025-11-02: Added cross-reference to ADR-049 (authentication)
- 2025-10-24: Initial decision (RLS for all sensitive tables)
