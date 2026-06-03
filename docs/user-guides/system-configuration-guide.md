# System Configuration User Guide

**Version:** 1.0
**Audience:** Administrators
**Date:** October 27, 2025
**Status:** Implemented

---

## Overview

System Configuration provides admin-only access to system-wide settings that affect all users and operations. This guide explains how to safely configure and maintain your AI Operations Platform deployment.

**What You'll Learn:**
- How to navigate the configuration interface
- Understanding configuration sections and settings
- Handling configuration health issues
- Safe update practices and rollback procedures

---

## Quick Start

### Access System Configuration

1. Navigate to **Admin** → **System Configuration** from main menu
2. **Requirements:** Admin role (corpus_admin has no access)
3. Four configuration sections displayed as expandable panels:
   - Corpus Settings (document processing)
   - Authentication (session and password policies)
   - Feature Flags (enable/disable features)
   - System Settings (logging, workers, timeouts)

### Make Your First Configuration Change

1. Expand **"Corpus Settings"** panel
2. Click **"Default Embedding Model"** dropdown
3. Select `all-MiniLM-L6-v2` (recommended)
4. Click **"Save All"** button (top toolbar)
5. Wait for success notification
6. **Note:** Some changes require service restart (indicated in response)

---

## Configuration Sections

### 1. Corpus Settings

**Purpose:** Document processing and embedding configuration

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| **Chunk Size** | 512 | 128-8192 | Document chunk size in tokens (must not exceed embedding model context window) |
| **Chunk Overlap** | 50 | 0-512 | Character overlap between chunks |
| **Default Embedding Model** | (varies) | - | Default model for new collections |
| **Max Document Size (MB)** | 50 | 1-500 | Maximum file upload size |
| **Allowed File Types** | pdf,txt,docx,md | - | Accepted file extensions |

**Important: Default Embedding Model**

⚠️ **This is NOT a global enforcement setting**

**What it does:**
- Pre-selects embedding model in Collection Create Dialog
- Provides convenience default for consistent collection creation
- Shows health warning if model becomes unavailable

**What it does NOT do:**
- Enforce model on existing collections
- Force all collections to use this model
- Affect Use Case execution

**Architecture:** Each collection chooses its own embedding model at creation (immutable thereafter). See [ADR-021 Addendum 3](../development/adrs/ADR-021-Collection-Based-Document-Management.md) for details.

**Best Practice:** Set to `all-MiniLM-L6-v2` for guaranteed availability (built-in, local, no API costs).

### 2. Authentication Settings

**Purpose:** Session timeout and password policies

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| **Session Timeout (minutes)** | 60 | 5-1440 | Idle timeout for user sessions |
| **Refresh Token TTL (days)** | 30 | 1-90 | Refresh token expiration |

**Password Policy:**
| Setting | Default | Description |
|---------|---------|-------------|
| **Min Length** | 8 | Minimum password length (6-32) |
| **Require Uppercase** | true | Require uppercase letters |
| **Require Lowercase** | true | Require lowercase letters |
| **Require Numbers** | true | Require numbers |
| **Require Special** | false | Require special characters |

**Impact:**
- Session timeout applies to all users
- Password policy enforced on password changes and new users
- Existing sessions not affected (apply on next login)

### 3. Feature Flags

**Purpose:** Enable/disable system-wide features

| Flag | Default | Description |
|------|---------|-------------|
| **Multi-Collection Search** | false | Enable multi-collection RAG queries |
| **Export Functionality** | true | Enable export features (Markdown/JSON) |
| **Conversation Cache** | true | Enable conversation caching |
| **Telemetry Enabled** | true | Enable telemetry collection |

**When to Change:**
- Enable multi-collection search after verifying same-model collections
- Disable exports for high-security environments
- Disable telemetry if not needed
- Adjust based on operational requirements

### 4. System Settings

**Purpose:** System-level operational configuration

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| **Log Level** | INFO | DEBUG/INFO/WARNING/ERROR/CRITICAL | System logging verbosity |
| **Max Workers** | 4 | 1-32 | Maximum worker threads |
| **Request Timeout (seconds)** | 30 | 5-300 | Request timeout |
| **Enable Debug Endpoints** | false | - | Expose debug API endpoints |

**Production Recommendations:**
- Log Level: INFO (DEBUG for troubleshooting only)
- Max Workers: Match CPU cores (4-8 typical)
- Request Timeout: 30s (increase for slow LLM models)
- Debug Endpoints: false (security risk if enabled)

---

## Configuration Health

### Health Indicator Banner

**When Shown:**
- Red banner at top of System Configuration page
- Indicates critical configuration issues
- Prevents certain operations until resolved

**Example:**

```
⚠️ Configuration Health Issue

• Default embedding model 'text-embedding-3-small' is not available. New collections cannot be created.
```

**Common Issues:**

| Issue | Severity | Impact | Resolution |
|-------|----------|--------|------------|
| **Default model unavailable** | Critical | Cannot create collections | Select available model from dropdown |
| **Corpus config missing** | Critical | System may be corrupted | Run database initialization |
| **Health check failed** | Warning | Cannot validate config | Check database connectivity |

### Resolving Health Issues

**Step 1: Identify the Issue**
- Read health banner message
- Note the recommendation
- Understand the impact

**Step 2: Fix the Root Cause**

For "Default model unavailable":
1. Expand "Corpus Settings" panel
2. Click "Default Embedding Model" dropdown
3. Look for models with green checkmark (available)
4. Select `all-MiniLM-L6-v2` (always available)
5. Click "Save All"

**Step 3: Verify Resolution**
- Health banner should disappear
- If persists, hard refresh page (Cmd+Shift+R)
- Check backend logs if error continues

---

## Safe Configuration Updates

### Before Making Changes

1. **Export Current Configuration** (backup)
   - Click "Export" button in toolbar
   - Save YAML file with timestamp
   - Example: `config_backup_20251027.yaml`

2. **Review Impact**
   - Corpus/System changes: Service restart required
   - Auth changes: Next login applies
   - Feature flags: Immediate effect

3. **Verify Permissions**
   - Ensure you have admin role
   - Other roles will see 403 Forbidden

### Making Changes

1. **Expand Section Panel**
   - Click section to expand (Corpus, Auth, Features, System)
   - All fields shown with current values

2. **Edit Fields**
   - Text inputs: Type new value
   - Dropdowns: Select from available options
   - Checkboxes: Toggle on/off
   - Arrays: Edit comma-separated list (future: chip input)

3. **Save Changes**
   - Click "Save All" button (saves ALL sections)
   - Or use future "Save Section" per-section save
   - Wait for success notification
   - Check for restart_required flag

4. **Restart Services (if required)**
   ```bash
   docker restart orchestrator-api-test
   docker restart corpus-service-test
   ```

### Rollback if Needed

**Option 1: Import Backup**
1. Click "Import" button
2. Paste backup YAML content
3. Enable "Validate Only" to check first
4. Click "Import" to apply

**Option 2: Manual Revert**
1. Expand affected section
2. Change values back to previous state
3. Click "Save All"

**Option 3: Database Restore**
```sql
-- View previous config
SELECT config, updated_at, updated_by
FROM system_config
WHERE section = 'corpus'
ORDER BY updated_at DESC
LIMIT 5;

-- Restore from known-good timestamp
UPDATE system_config
SET config = '<previous_json_value>'
WHERE section = 'corpus';
```

---

## Common Workflows

### Workflow 1: Change Default Embedding Model

**Scenario:** Update default model from unavailable remote model to built-in

**Steps:**
1. Navigate to Admin → System Configuration
2. Observe red health banner (if model unavailable)
3. Expand "Corpus Settings"
4. Click "Default Embedding Model" dropdown
5. Select `all-MiniLM-L6-v2` (BUILT-IN badge)
6. Review selected model card below
7. Click "Save All"
8. Verify health banner disappears
9. Test: Create new collection, verify model pre-selected

**Expected Result:** Health indicator clear, new collections default to built-in model

### Workflow 2: Tighten Security Settings

**Scenario:** Reduce session timeout and enforce stricter passwords

**Steps:**
1. Export current config (backup)
2. Expand "Authentication" section
3. Change "Session Timeout" from 60 to 30 minutes
4. Change "Password Policy" settings:
   - Min Length: 8 → 12
   - Require Special: false → true
5. Click "Save All"
6. Notify users of new password requirements
7. Existing sessions expire in 30 minutes

**Expected Result:** Shorter sessions, stronger password enforcement

### Workflow 3: Enable Multi-Collection Search

**Scenario:** Allow Use Cases to search multiple collections

**Prerequisites:**
- ✅ All collections use same embedding model
- ✅ Tested with single collection successfully

**Steps:**
1. Verify collections: Admin → Collections → Check embedding_model column
2. Navigate to Admin → System Configuration
3. Expand "Feature Flags" section
4. Toggle "Multi-Collection Search" to enabled
5. Click "Save All"
6. Test: Create Use Case with 2+ collections (same model)
7. Verify search results merge correctly

**Expected Result:** Use Case Wizard allows multiple collection selection, searches work

---

## Security Considerations

### Admin-Only Access

**RLS Policy:** `admin_only_system_config`
**Enforcement:** PostgreSQL Row-Level Security

**Who Can Access:**
- ✅ Admin role

**Who CANNOT Access:**
- ❌ Corpus Admin
- ❌ Developer
- ❌ Analyst
- ❌ User

**Audit Trail:**
- Every configuration change logged
- `updated_by` field tracks admin user ID
- `updated_at` timestamp recorded
- Full audit in audit_logs table (future: UI in Admin → Audit Logs)

### Sensitive Settings

**High-Impact Settings:**
- `enable_debug_endpoints` - Exposes internal state (security risk)
- `session_timeout_minutes` - Affects all user sessions
- `default_embedding_model` - Affects new collection creation
- `allowed_file_types` - Affects upload security

**Recommendations:**
- Review changes carefully before saving
- Export backup before major changes
- Test in test environment first
- Document reasons for changes

### Configuration Validation

**Backend Validation:**
- All changes validated against Pydantic schemas
- Type checking (string, int, boolean, array)
- Range validation (min/max for numbers)
- Enum validation (log levels, file types)
- Custom validators (password policy, file types)

**Frontend Validation:**
- Required fields marked with asterisk
- Min/max constraints enforced
- Invalid inputs show error messages
- Save button disabled until valid

---

## Troubleshooting

### "Access denied. Required role: admin" Error

**Cause:** User does not have admin role

**Solution:**
1. Verify your role: Check user profile or ask admin
2. Request admin elevation if needed
3. Use admin account for system configuration

### Configuration Save Fails with 500 Error

**Potential Causes:**
1. RLS session variables not set (middleware issue)
2. SQL syntax error in query
3. Database connection issue
4. Foreign key constraint violation

**Resolution:**
1. Check backend logs: `docker logs orchestrator-api-test --tail 50`
2. Verify RLS middleware extracts `role` correctly from JWT
3. Verify SQL query uses proper CAST syntax
4. Check database connectivity
5. Contact system administrator if persists

**Known Fix (Oct 27, 2025):**
- RLS middleware role extraction bug fixed
- SQL CAST syntax corrected
- Configuration saves now working

### JSON Schema Not Loading

**Symptom:** Configuration form shows loading spinner indefinitely

**Cause:** Schema endpoint returning error

**Solution:**
1. Check browser console for 403/500 errors
2. Verify admin authentication token valid
3. Hard refresh page
4. Check backend health: `curl http://localhost:8006/health`

---

## Best Practices

### 1. Regular Backups

**Weekly Exports:**
```bash
# Automated backup script
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -d "username=admin&password=adminpassword" | jq -r '.access_token')

curl -X POST "http://localhost:8006/api/v1/admin/config/export" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.config_yaml' > config_backup_$(date +%Y%m%d).yaml
```

### 2. Test in Test Environment

**Process:**
1. Make changes in test environment first
2. Verify application behavior
3. Document any restart requirements
4. Apply to production during maintenance window

### 3. Document Changes

**Change Log Template:**
```
Date: 2025-10-27
Section: corpus
Setting: default_embedding_model
Old Value: text-embedding-3-small
New Value: all-MiniLM-L6-v2
Reason: Remote model unavailable, switching to built-in for reliability
Impact: New collections default to built-in model
Restart: Yes (orchestrator + corpus services)
Tested: Yes (collection creation verified)
```

### 4. Monitor Configuration Health

**Daily Check:**
```bash
TOKEN=<your_token>
curl -X GET "http://localhost:8006/health/config" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Setup Alerts:**
- Monitor `healthy` field
- Alert if `healthy: false`
- Review `issues` array for details
- Act on critical severity issues immediately

---

## Advanced Topics

### Programmatic Configuration Management

**Get Current Config:**
```bash
curl -X GET "http://localhost:8006/api/v1/admin/config/" \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Update Single Section:**
```bash
curl -X PUT "http://localhost:8006/api/v1/admin/config/corpus" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @corpus_config.json
```

**Validate Without Applying:**
```bash
curl -X POST "http://localhost:8006/api/v1/admin/config/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config_yaml": "...",
    "validate_only": true
  }'
```

### Configuration as Code

**Version Control:**
```bash
# Export and commit to git (export via admin config API or script under ops/cli/)
./ops/cli/export_config.sh > config/system_config_prod.yaml
git add config/system_config_prod.yaml
git commit -m "docs: update system config for Oct 2025 deployment"
```

**Deployment Automation:**
```bash
# Import from version control
cat config/system_config_prod.yaml | \
  jq -Rs '{config_yaml: ., validate_only: false}' | \
  curl -X POST "http://localhost:8006/api/v1/admin/config/import" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d @-
```

### Embedding Model Availability

**Check Available Models:**
```bash
curl -X GET "http://localhost:8006/api/v1/models?model_type=embedding&is_available=true" \
  -H "Authorization: Bearer $TOKEN" | jq '.models[] | {model_id, name, provider, dimensions, is_available}'
```

**Expected Output:**
```json
{
  "model_id": "all-MiniLM-L6-v2",
  "name": "all-MiniLM-L6-v2",
  "provider": "local",
  "dimensions": 384,
  "is_available": true
}
```

**Verify Health:**
```bash
curl -X GET "http://localhost:8006/health/config" \
  -H "Authorization: Bearer $TOKEN" | jq '.healthy, .issues'
```

---

## Troubleshooting

### Health Banner Won't Clear

**Symptom:** Red banner persists after selecting available model

**Diagnostics:**
1. Check backend logs for save errors
2. Verify model in Model Registry: GET `/api/v1/models`
3. Check browser console for 500 errors
4. Verify RLS session variables set correctly

**Solutions:**
1. Hard refresh: Cmd+Shift+R (Mac) / Ctrl+Shift+F5 (Windows)
2. Logout and login again (refresh JWT token)
3. Restart backend container: `docker restart orchestrator-api-test`
4. Check database: `SELECT * FROM models WHERE model_type='embedding'`

### Configuration Save Returns 500 Error

**Known Issues (Fixed Oct 27, 2025):**

**Issue 1: RLS Middleware Bug**
- **Symptom:** 500 Internal Server Error on PUT `/admin/config/corpus`
- **Cause:** Middleware extracted `roles` (plural) but TokenPayload has `role` (singular)
- **Fix:** Updated middleware to extract `role` first, fallback to `roles`
- **Status:** ✅ Fixed

**Issue 2: SQL Syntax Error**
- **Symptom:** `syntax error at or near ":"`
- **Cause:** Mixed parameter styles (`:param::type` with named params)
- **Fix:** Changed to `CAST(:param AS type)` syntax
- **Status:** ✅ Fixed

**Current Solution:**
- Restart container if errors persist: `docker restart orchestrator-api-test`
- Verify fix applied: Check middleware code for `role` extraction
- Test save: Should succeed with 200 response

### Schema Load Fails

**Symptom:** Form shows "Loading..." indefinitely

**Cause:** Schema endpoint returning error or timeout

**Solution:**
1. Check network tab for `/admin/config/schema/{section}` errors
2. Verify backend running: `docker ps | grep orchestrator`
3. Check backend health: `curl http://localhost:8006/health`
4. Verify admin role in JWT token

---

## Reference

### API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/admin/config/` | Get all configuration |
| GET | `/api/v1/admin/config/{section}` | Get specific section |
| PUT | `/api/v1/admin/config/{section}` | Update section |
| GET | `/api/v1/admin/config/schema/{section}` | Get JSON schema |
| POST | `/api/v1/admin/config/export` | Export as YAML |
| POST | `/api/v1/admin/config/import` | Import from YAML |
| GET | `/health/config` | Configuration health check |

### Related Documentation

- **API Reference:** [System Configuration API](../api/admin/system-configuration.md)
- **Database Schema:** [SCHEMA.md](../architecture/database/SCHEMA.md#system_config)
- **RLS Policies:** [RLS_POLICIES.md](../architecture/database/RLS_POLICIES.md#system_config)
- **ADR-038:** JSONB Configuration Storage
- **ADR-039:** Row-Level Security
- **Collection Guide:** [Collection Management](collection-management-guide.md)

---

## FAQ

**Q: Why can't corpus_admin access System Configuration?**
A: System-wide settings affect all users and operations. Only admins can modify to prevent accidental misconfigurations.

**Q: Does changing default_embedding_model affect existing collections?**
A: No. Each collection's embedding model is set at creation and is immutable. The default only affects NEW collections.

**Q: What if I set an invalid default_embedding_model?**
A: The health banner will show a warning, but the system continues working. Existing collections are unaffected. New collection creation will fail until you select an available model.

**Q: Can I have different defaults for different user groups?**
A: No. The default_embedding_model is system-wide. However, users can always override by selecting a different model in the Collection Create Dialog.

**Q: How do I know if a configuration change requires restart?**
A: The API response includes `restart_required: true/false`. Corpus and system sections typically require restart.

**Q: Can I revert a configuration change?**
A: Yes, use the Import feature with a backup YAML, or manually change values back and save.

---

**Document Owner:** Alex
**Last Updated:** October 27, 2025
**Related:** [System Configuration API](../api/admin/system-configuration.md), [ADR-038](../development/adrs/ADR-038-JSONB-Configuration-Storage.md), [ADR-039](../development/adrs/ADR-039-Row-Level-Security-Admin-Access.md)
