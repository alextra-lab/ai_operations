# Row-Level Security (RLS) Policies

**Version:** 1.1.0
**Last Updated:** 2025-10-27

## Overview

AI Operations Platform implements **comprehensive Row-Level Security (RLS)** on all sensitive tables to enforce:

- **Multi-tenant isolation** - Users see only their own data
- **Role-based access** - admins, developers, corpus_admin, users, service accounts
- **Use case permissions** - Granular access to specific use cases
- **Audit compliance** - Security-sensitive operations logged

**Tables with RLS:** 17 of 32 tables
**Session-Based:** Uses `aio.current_user_uuid()` and `aio.current_user_roles()`

---

## RLS Architecture

### Session Context Functions

All RLS policies use three core functions:

```sql
-- Get current user's UUID from session variable
CREATE OR REPLACE FUNCTION aio.current_user_uuid()
RETURNS uuid AS $$
    SELECT NULLIF(current_setting('aio.user_id', true), '')::uuid;
$$ LANGUAGE SQL STABLE;

-- Get current user's roles as array
CREATE OR REPLACE FUNCTION aio.current_user_roles()
RETURNS text[] AS $$
    SELECT regexp_split_to_array(
        trim(both '{}' FROM current_setting('aio.user_roles', true)),
        '\s*,\s*'
    );
$$ LANGUAGE SQL STABLE;

-- Check if user has specific role
CREATE OR REPLACE FUNCTION aio.user_has_role(target_role text)
RETURNS boolean AS $$
    SELECT target_role = ANY(aio.current_user_roles());
$$ LANGUAGE SQL STABLE;
```

### Setting Session Variables

Applications must set these before queries:

```sql
-- Set user context
SET LOCAL aio.user_id = 'uuid-here';
SET LOCAL aio.user_roles = '{admin,developer}';

-- Or using PostgreSQL's application_name (for tools)
SET LOCAL app.user_id = 'uuid-here';
```

---

## Policy Patterns

### Pattern 1: User Isolation (Most Common)

**Users see only their own data, admins see all**

```sql
-- Example: query_history
CREATE POLICY query_history_user_isolation_policy
ON query_history
FOR SELECT
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);
```

**Applied to:**
- `query_history` - Users see own queries
- `context_threads` - Users see own threads
- `thread_messages` - Users see messages from own threads
- `token_usage` - Users see own token consumption
- `tool_invocations` - Users see own tool calls

---

### Pattern 2: Role-Based Full Access

**Specific roles get full access**

```sql
-- Example: use_cases (admin manage)
CREATE POLICY use_cases_admin_manage
ON use_cases
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));
```

**Applied to:**
- `use_cases` - admin can manage all
- `prompt_templates` - admin can manage all
- `user_use_case_assignments` - admin/corpus_admin can manage
- `encryption_keys` - admin/corpus_admin can manage
- `tools` - admin can manage all
- `tool_secrets` - admin-only access

---

### Pattern 3: Use Case-Based Access

**Users see resources for use cases they're assigned to**

```sql
-- Example: use_cases (user read)
CREATE POLICY use_cases_user_read
ON use_cases
FOR SELECT
USING (
    aio.user_has_role('user')
    AND EXISTS (
        SELECT 1
        FROM user_use_case_assignments a
        WHERE a.use_case_id = use_cases.id
          AND a.user_id = aio.current_user_uuid()
          AND a.status = 'active'
    )
);
```

**Applied to:**
- `use_cases` - users see assigned use cases
- `run_manifests` - users see manifests for their use cases

---

### Pattern 4: Lifecycle-Based Permissions

**Different access based on resource state**

```sql
-- Example: use_cases (developer can modify drafts, not published)
CREATE POLICY use_cases_developer_rw
ON use_cases
FOR ALL
USING (
    aio.user_has_role('developer')
    OR aio.user_has_role('corpus_admin')
    OR aio.user_has_role('service')
)
WITH CHECK (
    aio.user_has_role('admin')
    OR (
        aio.user_has_role('developer')
        AND lifecycle_state <> 'published'
    )
);
```

**Applied to:**
- `use_cases` - developers can modify drafts only
- `prompt_templates` - developers can modify non-deployed templates

---

### Pattern 5: Service Account Access

**Service/background processes need special permissions**

```sql
-- Example: audit_logs (service can insert, admins can read)
CREATE POLICY audit_logs_service_insert
ON audit_logs
FOR INSERT
WITH CHECK (
    aio.user_has_role('service')
    OR aio.user_has_role('admin')
);

CREATE POLICY audit_logs_admin_read
ON audit_logs
FOR SELECT
USING (aio.user_has_role('admin'));
```

**Applied to:**
- `audit_logs` - service inserts, admins/developers/corpus_admins read
- `token_usage` - service inserts, users read own, admins read all

---

## Complete Policy Reference

### authentication Tables

#### `use`rs

**No RLS** - Access controlled by application layer
**Reason:** Authentication requires user lookup before RLS context is established

#### `refresh_tokens`

**No RLS** - Access controlled by application layer
**Reason:** Token validation happens before RLS context

#### `user_roles`

**No RLS** - Access controlled by application layer
**Reason:** Role determination needed for RLS setup

---

### Use Case System

#### `use_cases`

**RLS Enabled:** YES (FORCE ROW LEVEL SECURITY)

```sql
-- Policy 1: Admins manage all
CREATE POLICY use_cases_admin_manage ON use_cases
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));

-- Policy 2: Developers/corpus_admin can view all, edit drafts only
CREATE POLICY use_cases_developer_rw ON use_cases
FOR ALL
USING (
    aio.user_has_role('developer')
    OR aio.user_has_role('corpus_admin')
    OR aio.user_has_role('service')
)
WITH CHECK (
    aio.user_has_role('admin')
    OR (
        aio.user_has_role('developer')
        AND lifecycle_state <> 'published'
    )
);

-- Policy 3: Users can read assigned use cases
CREATE POLICY use_cases_user_read ON use_cases
FOR SELECT
USING (
    aio.user_has_role('user')
    AND EXISTS (
        SELECT 1 FROM user_use_case_assignments a
        WHERE a.use_case_id = use_cases.id
          AND a.user_id = aio.current_user_uuid()
          AND a.status = 'active'
    )
);
```

#### `prompt_templates`

**RLS Enabled:** YES (FORCE ROW LEVEL SECURITY)

```sql
-- Policy 1: Admins manage all
CREATE POLICY prompt_templates_admin_manage ON prompt_templates
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));

-- Policy 2: Developers can manage, service can read
CREATE POLICY prompt_templates_developer_rw ON prompt_templates
FOR ALL
USING (aio.user_has_role('developer') OR aio.user_has_role('service'))
WITH CHECK (aio.user_has_role('admin') OR aio.user_has_role('developer'));

-- Policy 3: Corpus admins can view
CREATE POLICY prompt_templates_corpus_view ON prompt_templates
FOR SELECT
USING (aio.user_has_role('corpus_admin'));
```

#### `user_use_case_assignments`

**RLS Enabled:** YES (FORCE ROW LEVEL SECURITY)

```sql
-- Policy 1: Admins manage all
CREATE POLICY assignments_admin_manage ON user_use_case_assignments
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));

-- Policy 2: Corpus admins manage assignments
CREATE POLICY assignments_corpus_manage ON user_use_case_assignments
FOR ALL
USING (aio.user_has_role('corpus_admin'))
WITH CHECK (aio.user_has_role('corpus_admin') OR aio.user_has_role('admin'));

-- Policy 3: Users can view their own assignments
CREATE POLICY assignments_user_read ON user_use_case_assignments
FOR SELECT
USING (user_id = aio.current_user_uuid());

-- Policy 4: Service accounts can read all assignments
CREATE POLICY assignments_service_read ON user_use_case_assignments
FOR SELECT
USING (aio.user_has_role('service'));
```

---

### Query History & Threading

#### `query_history`

**RLS Enabled:** YES

```sql
-- SELECT: Users see own, admins see all
CREATE POLICY query_history_user_isolation_policy ON query_history
FOR SELECT
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);

-- INSERT: Users can insert their own
CREATE POLICY query_history_insert_policy ON query_history
FOR INSERT
WITH CHECK (user_id = aio.current_user_uuid());

-- UPDATE: Users update own, admins update all
CREATE POLICY query_history_update_policy ON query_history
FOR UPDATE
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);

-- DELETE: Admins only
CREATE POLICY query_history_delete_policy ON query_history
FOR DELETE
USING (aio.user_has_role('admin'));
```

#### `context_threads`

**RLS Enabled:** YES

```sql
-- SELECT: Users see own threads, admins see all
CREATE POLICY context_threads_user_isolation_policy ON context_threads
FOR SELECT
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);

-- INSERT: Users can create threads
CREATE POLICY context_threads_insert_policy ON context_threads
FOR INSERT
WITH CHECK (user_id = aio.current_user_uuid());

-- UPDATE: Users update own, admins update all
CREATE POLICY context_threads_update_policy ON context_threads
FOR UPDATE
USING (
    user_id = aio.current_user_uuid()
    OR aio.user_has_role('admin')
);
```

#### `thread_messages`

**RLS Enabled:** YES

```sql
-- SELECT: Users see messages from own threads
CREATE POLICY thread_messages_user_isolation_policy ON thread_messages
FOR SELECT
USING (
    thread_id IN (
        SELECT id FROM context_threads
        WHERE user_id = aio.current_user_uuid()
    )
    OR aio.user_has_role('admin')
);

-- INSERT: Users can add messages to own threads
CREATE POLICY thread_messages_insert_policy ON thread_messages
FOR INSERT
WITH CHECK (
    thread_id IN (
        SELECT id FROM context_threads
        WHERE user_id = aio.current_user_uuid()
    )
);
```

---

### Token Tracking

#### `token_usage`

**RLS Enabled:** YES

```sql
-- Admins can do anything
CREATE POLICY token_usage_admin_all_policy ON token_usage
FOR ALL
USING (aio.user_has_role('admin'));

-- Users can read own usage
CREATE POLICY token_usage_user_read_policy ON token_usage
FOR SELECT
USING (user_id = aio.current_user_uuid());

-- Service can insert usage records
CREATE POLICY token_usage_service_insert_policy ON token_usage
FOR INSERT
WITH CHECK (
    aio.user_has_role('service')
    OR aio.user_has_role('admin')
);
```

---

### Tools Platform

#### `tools`

**RLS Enabled:** YES

```sql
-- Admins manage all tools
CREATE POLICY admin_all_tools ON tools
FOR ALL
USING (EXISTS (
    SELECT 1 FROM users u
    WHERE u.id = current_setting('app.user_id')::UUID
    AND u.role = 'admin'
));

-- Users can view enabled tools they have permission for
CREATE POLICY users_view_enabled_tools ON tools
FOR SELECT
USING (
    is_enabled = true
    AND EXISTS (
        SELECT 1 FROM tool_permissions tp, users u
        WHERE tp.tool_id = tools.id
        AND u.id = current_setting('app.user_id')::UUID
        AND tp.role = u.role
        AND tp.can_view = true
    )
);
```

#### `tool_secrets`

**RLS Enabled:** YES

```sql
-- Admins only (application-level access)
CREATE POLICY secrets_admin_only ON tool_secrets
FOR ALL
USING (EXISTS (
    SELECT 1 FROM users u
    WHERE u.id = current_setting('app.user_id')::UUID
    AND u.role = 'admin'
));
```

#### `tool_invocations`

**RLS Enabled:** YES

```sql
-- Users view own invocations
CREATE POLICY users_view_own_invocations ON tool_invocations
FOR SELECT
USING (user_id = current_setting('app.user_id')::UUID);

-- Admins view all invocations
CREATE POLICY admin_view_all_invocations ON tool_invocations
FOR SELECT
USING (EXISTS (
    SELECT 1 FROM users u
    WHERE u.id = current_setting('app.user_id')::UUID
    AND u.role = 'admin'
));
```

---

### Telemetry

#### `run_manifests`

**RLS Enabled:** YES

```sql
-- Users see manifests for use cases they can access
CREATE POLICY run_manifests_access_policy ON run_manifests
FOR ALL
USING (
    use_case_id IN (
        SELECT use_case_id FROM use_cases
        WHERE created_by_user_id = aio.current_user_uuid()
    )
);
```

---

### Security & Audit

#### `encryption_keys`

**RLS Enabled:** YES (FORCE ROW LEVEL SECURITY)

```sql
-- Admins manage all
CREATE POLICY encryption_keys_admin_manage ON encryption_keys
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));

-- Corpus admins manage
CREATE POLICY encryption_keys_corpus_manage ON encryption_keys
FOR ALL
USING (aio.user_has_role('corpus_admin'))
WITH CHECK (aio.user_has_role('corpus_admin') OR aio.user_has_role('admin'));

-- Developers can read
CREATE POLICY encryption_keys_developer_read ON encryption_keys
FOR SELECT
USING (aio.user_has_role('developer'));

-- Service can read
CREATE POLICY encryption_keys_service_read ON encryption_keys
FOR SELECT
USING (aio.user_has_role('service'));
```

#### `system_config`

**RLS Enabled:** YES

**Purpose:** Admin-only access to system-wide configuration

```sql
-- Admins only - all operations
CREATE POLICY admin_only_system_config ON system_config
FOR ALL
USING (aio.user_has_role('admin'))
WITH CHECK (aio.user_has_role('admin'));
```

**Access Control:**
- ✅ **admins** - Full access (SELECT, INSERT, UPDATE, DELETE)
- ❌ **developers** - No access
- ❌ **corpus_admin** - No access
- ❌ **users** - No access
- ❌ **service** - No access

**Rationale:**
- System configuration affects all users and operations
- Only administrators should modify system-wide settings
- Configuration changes can impact security, performance, and functionality
- Follows principle of least privilege (ADR-039)

**Related API:** `/api/v1/admin/config` enforces admin role via `Depends(admin_required)`

#### `audit_logs`

**RLS Enabled:** YES (FORCE ROW LEVEL SECURITY)

```sql
-- Service can insert
CREATE POLICY audit_logs_service_insert ON audit_logs
FOR INSERT
WITH CHECK (aio.user_has_role('service') OR aio.user_has_role('admin'));

-- Admins can read all
CREATE POLICY audit_logs_admin_read ON audit_logs
FOR SELECT
USING (aio.user_has_role('admin'));

-- Developers can read all
CREATE POLICY audit_logs_developer_read ON audit_logs
FOR SELECT
USING (aio.user_has_role('developer'));

-- Corpus admins can read use case-specific logs
CREATE POLICY audit_logs_corpus_read ON audit_logs
FOR SELECT
USING (
    aio.user_has_role('corpus_admin')
    AND (
        use_case_id IS NULL
        OR EXISTS (
            SELECT 1 FROM user_use_case_assignments a
            WHERE a.use_case_id = audit_logs.use_case_id
              AND a.user_id = aio.current_user_uuid()
              AND a.assigned_role = 'corpus_admin'
              AND a.status = 'active'
        )
    )
);
```

---

## Testing RLS Policies

### Setup Test Session

```sql
-- Set session as regular user
SET LOCAL aio.user_id = 'user-uuid-here';
SET LOCAL aio.user_roles = '{user}';

-- Test query
SELECT * FROM query_history;  -- Should only see own queries

-- Reset session
RESET aio.user_id;
RESET aio.user_roles;
```

### Test Admin Access

```sql
-- Set session as admin
SET LOCAL aio.user_id = 'admin-uuid-here';
SET LOCAL aio.user_roles = '{admin}';

-- Test query
SELECT * FROM query_history;  -- Should see all queries
```

### Bypass RLS (Superuser Only)

```sql
-- Disable RLS for troubleshooting (superuser only!)
ALTER TABLE query_history DISABLE ROW LEVEL SECURITY;

-- Re-enable after debugging
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;
```

---

## Performance Considerations

### RLS Performance Impact

- **Negligible** for indexed columns (user_id, role checks)
- **Moderate** for EXISTS subqueries (use_case assignments)
- **Mitigated** by proper indexing on FK columns

### Optimization Tips

1. **Index FK columns** used in RLS policies
2. **Use STABLE functions** (already done)
3. **Avoid complex subqueries** in hot paths
4. **Consider materialized views** for complex permissions

### Query Plan Analysis

```sql
-- Check RLS policy performance
EXPLAIN ANALYZE
SELECT * FROM query_history
WHERE user_id = aio.current_user_uuid();

-- Look for:
-- - "Filter: (user_id = current_setting(...))"
-- - Index usage on user_id column
```

---

## Security Best Practices

### 1. Always Set Session Variables

```python
# Python example
async with pool.connection() as conn:
    await conn.execute("SET LOCAL aio.user_id = $1", user_id)
    await conn.execute("SET LOCAL aio.user_roles = $1",
                       '{' + ','.join(user_roles) + '}')
    # Now execute queries - RLS active
    result = await conn.fetch("SELECT * FROM query_history")
```

### 2. Validate Session Context

```sql
-- Check current RLS context
SELECT
    aio.current_user_uuid() AS user_id,
    aio.current_user_roles() AS roles;
```

### 3. Service Account Best Practices

- **Dedicated service account** - Don't use admin for services
- **Minimal permissions** - Only what's needed
- **Audit service actions** - Log all service operations

### 4. Never Disable RLS in Production

```sql
-- NEVER do this in production!
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
```

---

## Troubleshooting

### Issue: Query returns no rows

**Cause:** RLS policies filtering all rows

**Solution:**
```sql
-- Check session context
SELECT
    aio.current_user_uuid() AS user_id,
    aio.current_user_roles() AS roles;

-- Temporarily disable RLS (superuser only)
ALTER TABLE tablename DISABLE ROW LEVEL SECURITY;
-- Run query to see unfiltered data
SELECT * FROM tablename;
-- Re-enable RLS
ALTER TABLE tablename ENABLE ROW LEVEL SECURITY;
```

### Issue: Performance degradation

**Cause:** Complex RLS policies with subqueries

**Solution:**
```sql
-- Check query plan
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM tablename;

-- Look for sequential scans in RLS filter
-- Add indexes on columns used in policies
```

### Issue: Policy not applying

**Cause:** Session variables not set

**Solution:**
```sql
-- Verify session is set
SHOW aio.user_id;
SHOW aio.user_roles;

-- If empty, set before querying
SET LOCAL aio.user_id = 'uuid-here';
SET LOCAL aio.user_roles = '{admin}';
```

---

**Last Updated:** 2025-10-24
**Maintainer:** AI Operations Platform Team
