# ADR-051: Provider Secrets and Service-to-Service Authentication

**Status:** Approved
**Date:** 2025-11-02
**Deciders:** Security Team, Backend Team
**Tags:** security, authentication, secrets, jwt

---

## Context

The Inference Gateway consolidates access to external inference providers (OpenAI, Mistral, LMStudio, VLLM) and must securely manage provider credentials while authenticating internal callers. The security posture is defined in **ADR-049 (Unified Authentication & Security)** which is production-deployed across all services.

### Current State (ADR-049 Compliance)

**Existing Infrastructure (`src/shared/auth/`):**
- ✅ `UnifiedAuthManager` - JWT creation, validation, RBAC
- ✅ `TokenPayload` - Standard claims (`sub`, `user_id`, `role`, `exp`, `iat`, `iss`, `token_type`)
- ✅ `HTTPBearer` security - FastAPI dependency injection
- ✅ Role-based dependencies - `admin_required()`, `service_required()`, `requires_roles()`
- ✅ Password hashing - bcrypt with auto-salts
- ✅ Token storage - `refresh_tokens` table with revocation support

**Problem:** `TokenPayload` doesn't support **scopes** (fine-grained permissions beyond roles).

**Example Need:**
```python
# Service account can call inference endpoints but not admin endpoints
{
    "sub": "service_account:cortex-prod",
    "role": "service",
    "scopes": ["inference:chat"],  # ← NOT in current TokenPayload
    # Should NOT have "gateway:admin" scope
}
```

### Goals

1. **Eliminate Secret Sprawl:** Provider API keys only in Gateway (not in orchestrator, embedding service)
2. **S2S Authentication:** Enforce JWT validation for all Gateway access
3. **Scope-Based Authorization:** Fine-grained permissions (inference vs admin)
4. **Simple Secret Management:** Manual updates via API/UI (no complex rotation)
5. **ADR-049 Alignment:** Reuse existing auth infrastructure, minimal extensions

---

## Decision

### 1. Extend TokenPayload with Optional Scopes

**Modification to `src/shared/auth/models.py`:**

```python
class TokenPayload(BaseModel):
    """Standard JWT token payload across all services."""

    sub: str          # username or service-id
    user_id: str      # UUID as string
    role: str         # Single role (admin, service, user, etc.)
    scopes: list[str] = []  # NEW: Optional fine-grained permissions
    exp: int
    iat: int
    iss: str
    token_type: str   # "access" or "refresh"

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    def is_service(self) -> bool:
        """Check if user has service or admin role."""
        return self.role in UserRole.privileged_roles()

    def has_role(self, required_roles: list[str]) -> bool:
        """Check if user has any of the required roles."""
        return self.role in required_roles

    # NEW METHOD
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has specific scope."""
        return required_scope in self.scopes

    # NEW METHOD
    def has_any_scope(self, required_scopes: list[str]) -> bool:
        """Check if token has any of the required scopes."""
        return any(scope in self.scopes for scope in required_scopes)
```

**Backward Compatibility:**
- `scopes` defaults to empty list (existing tokens still valid)
- All existing `has_role()` checks continue to work
- New `has_scope()` method for fine-grained checks

### 2. Gateway Scope Definitions

**Scope Taxonomy:**

| Scope | Purpose | Who Gets It |
|-------|---------|-------------|
| `inference:chat` | Call `/v1/chat/completions` | Orchestrator, agents, authorized users |
| `inference:embed` | Call `/v1/embeddings` | Embedding service, corpus service |
| `gateway:admin` | Access control plane (`/admin/gateway/*`) | Admin users only |
| `gateway:metrics` | Read-only metrics access | Monitoring services, dashboards |

**Token Examples:**

```python
# Orchestrator service account
{
    "sub": "service:orchestrator-api",
    "user_id": "<orchestrator-service-uuid>",
    "role": "service",
    "scopes": ["inference:chat"],  # Can call chat but not embeddings
    "iss": "ai-operations-platform",
    "token_type": "access"
}

# Embedding service account
{
    "sub": "service:embedding-service",
    "user_id": "<embedding-service-uuid>",
    "role": "service",
    "scopes": ["inference:embed"],  # Can call embeddings but not chat
    "iss": "ai-operations-platform",
    "token_type": "access"
}

# Admin user
{
    "sub": "admin_user",
    "user_id": "<user-uuid>",
    "role": "admin",
    "scopes": ["inference:chat", "inference:embed", "gateway:admin"],
    "iss": "ai-operations-platform",
    "token_type": "access"
}

# SOAR integration (limited)
{
    "sub": "service:cortex-prod",
    "user_id": "<cortex-service-uuid>",
    "role": "service",
    "scopes": ["inference:chat"],  # Can call chat only
    "iss": "ai-operations-platform",
    "token_type": "access"
}
```

### 3. Gateway Authorization Logic

**FastAPI Dependency (similar to `admin_required`):**

```python
# src/inference-gateway/app/auth/dependencies.py
from shared.auth import auth_manager, TokenPayload
from fastapi import Depends, HTTPException, status

def requires_scope(required_scope: str):
    """Dependency that requires specific scope."""
    def scope_checker(
        token: TokenPayload = Depends(auth_manager.get_current_user)
    ) -> TokenPayload:
        if not token.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}"
            )
        return token
    return scope_checker

# Usage in Gateway endpoints
@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    token: TokenPayload = Depends(requires_scope("inference:chat"))
):
    # Token has inference:chat scope, proceed
    pass

@router.post("/admin/gateway/providers")
async def create_provider(
    provider: ProviderConfig,
    token: TokenPayload = Depends(requires_scope("gateway:admin"))
):
    # Token has gateway:admin scope, proceed
    pass
```

### 4. Provider Secret Management

**Storage: PostgreSQL Table**

```sql
-- Database schema (Gateway-specific)
CREATE TABLE gateway_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,  -- 'openai', 'mistral', 'lmstudio'
    type TEXT NOT NULL,          -- 'openai', 'openai_compatible', 'vllm'
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT,      -- Encrypted with PostgreSQL pgcrypto
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,
    config JSONB DEFAULT '{}'::jsonb,  -- Provider-specific settings

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Encryption at rest using PostgreSQL pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Insert with encryption
INSERT INTO gateway_providers (name, type, base_url, api_key_encrypted)
VALUES (
    'openai',
    'openai',
    'https://api.openai.com/v1',
    pgp_sym_encrypt('sk-actual-key-here', current_setting('app.encryption_key'))
);

-- Read with decryption
SELECT
    name,
    type,
    base_url,
    pgp_sym_decrypt(api_key_encrypted::bytea, current_setting('app.encryption_key')) as api_key
FROM gateway_providers
WHERE enabled = true;
```

**Encryption Key Management:**
```bash
# Environment variable (PostgreSQL session)
export GATEWAY_ENCRYPTION_KEY="<64-char-random-string>"

# PostgreSQL session config
ALTER DATABASE aio SET app.encryption_key TO '<key-from-env>';
```

**Alternative (Simpler for v1):**
- Store API keys in environment variables (dev/test)
- Store in database unencrypted with PostgreSQL's native encryption at rest
- Add `pgcrypto` encryption in v2 when moving to production

### 5. Secret Update Workflow

**Admin UI Flow:**
```
1. Admin navigates to Gateway > Providers
2. Clicks "Edit" on provider (e.g., OpenAI)
3. Updates API key in secure form field (type="password")
4. Clicks "Save"
5. Frontend calls: PUT /admin/gateway/providers/openai
   {
       "api_key": "sk-new-key-123",
       "base_url": "https://api.openai.com/v1"
   }
6. Gateway validates admin token + gateway:admin scope
7. Gateway encrypts new key, updates database
8. Gateway reloads provider config (in-memory cache)
9. Next request uses new key
```

**API Endpoint:**
```python
@router.put("/admin/gateway/providers/{name}")
async def update_provider(
    name: str,
    update: ProviderUpdate,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(requires_scope("gateway:admin"))
):
    """Update provider configuration (admin only)."""

    # Fetch provider
    provider = db.query(GatewayProvider).filter_by(name=name).first()
    if not provider:
        raise HTTPException(404, f"Provider '{name}' not found")

    # Update fields
    if update.api_key:
        provider.api_key_encrypted = encrypt_key(update.api_key)
    if update.base_url:
        provider.base_url = update.base_url
    if update.enabled is not None:
        provider.enabled = update.enabled

    provider.updated_by = token.user_id
    provider.updated_at = datetime.now(UTC)

    db.commit()

    # Reload Gateway config (in-memory cache)
    await provider_manager.reload()

    # Audit log
    logger.info(
        "Provider updated",
        extra={
            "provider": name,
            "updated_by": token.sub,
            "user_id": token.user_id,
            "fields": ["api_key", "base_url"] if update.api_key else ["base_url"]
        }
    )

    return {"message": f"Provider '{name}' updated successfully"}
```

**Reload Endpoint (No Restart Needed):**
```python
@router.post("/admin/gateway/reload")
async def reload_config(
    token: TokenPayload = Depends(requires_scope("gateway:admin"))
):
    """Reload provider configuration without restart."""

    # Re-read from database
    await provider_manager.reload_from_db()

    logger.info(
        "Gateway config reloaded",
        extra={"reloaded_by": token.sub}
    )

    return {
        "message": "Configuration reloaded",
        "providers": provider_manager.list_providers()
    }
```

### 6. Request Context Propagation

**Standard Headers (ADR-049 Pattern):**
```python
# Orchestrator → Gateway
headers = {
    "Authorization": f"Bearer {service_token}",
    "X-Request-ID": request_id,  # Propagate from user request
    "X-User-ID": user_id,         # Original user (if applicable)
}

response = await gateway_client.chat_completion(
    model="gpt-4o-mini",
    messages=messages,
    headers=headers
)
```

**Gateway Logging:**
```python
# Gateway logs with full context
logger.info(
    "Chat completion request",
    extra={
        "request_id": headers["X-Request-ID"],
        "service": token.sub,  # "service:orchestrator-api"
        "user_id": headers.get("X-User-ID"),  # Original user
        "provider": "openai",
        "model": "gpt-4o-mini",
        "tokens_in": 120,
        "tokens_out": 80,
        "cost_eur": 0.00015,
        "latency_ms": 245
    }
)
```

---

## Rationale

### Why Extend TokenPayload with Scopes?

**Roles vs Scopes:**
- **Role** = Authority level (admin, user, service)
- **Scope** = Capability (can call chat, can call embeddings, can admin gateway)

**Example:**
```python
# User with "service" role can have different scopes
Service A: role=service, scopes=[inference:chat]           # Orchestrator
Service B: role=service, scopes=[inference:embed]          # Embedding
Service C: role=service, scopes=[inference:chat, inference:embed]  # Corpus

# Scope prevents Service A from calling embeddings endpoint
```

**Why Not Separate Roles?**
- ❌ `inference_chat_service`, `inference_embed_service`, `gateway_admin_service` = role explosion
- ❌ Hard to combine permissions (service needs both chat AND embeddings)
- ✅ Scopes = composable, flexible, standard pattern (OAuth2 scopes)

### Why Manual Secret Management?

**Complex Rotation (Rejected):**
```python
# NOT IMPLEMENTING THIS COMPLEXITY
provider_secrets = {
    "openai": {
        "current": "sk-new-key",
        "previous": "sk-old-key",  # Grace period
        "rotated_at": "2025-11-02T10:30:00Z"
    }
}
# Try current, fallback to previous on auth error
```

**Problems:**
- Adds 200+ lines of code
- Requires Redis or database for state
- Complex testing (simulate rotation failures)
- Not needed for department scale (manual rotation once per quarter)

**Simple Approach (Implementing):**
```python
# Store one key per provider
provider.api_key = "sk-current-key"

# Admin updates via UI
# Gateway reloads config
# Next request uses new key

# Downtime: 0 seconds (in-memory reload)
```

**Rotation Procedure:**
1. Generate new API key on provider dashboard (OpenAI/Mistral)
2. Update in AI Operations Platform (AIOP) Admin UI
3. Click "Save" (Gateway reloads immediately)
4. Verify requests work with new key
5. Revoke old key on provider dashboard

**Frequency:** Quarterly or on security incident (not daily/weekly)

### Why PostgreSQL for Secrets (Not Vault)?

**For Department Scale:**
- PostgreSQL with `pgcrypto` encryption = sufficient
- Vault/KMS = overkill (adds complexity, another service to manage)
- Air-gapped environments prefer fewer dependencies
- Can upgrade to Vault in Phase 6 (enterprise hardening) if needed

**Security Layers:**
1. PostgreSQL encryption at rest (disk encryption)
2. `pgcrypto` symmetric encryption (application layer)
3. Network isolation (Gateway only service that reads keys)
4. Audit logging (who accessed what when)
5. RBAC (only admin role can update keys)

---

## Consequences

### Positive

✅ **Single Source of Secrets:** Provider keys only in Gateway database
✅ **Fine-Grained Authorization:** Scopes prevent unauthorized endpoint access
✅ **Zero Downtime Updates:** Reload config without restart
✅ **Audit Trail:** All key updates logged with user attribution
✅ **ADR-049 Alignment:** Reuses existing `shared.auth` infrastructure
✅ **Simple Operations:** Manual updates via familiar Admin UI

### Negative

❌ **TokenPayload Change:** Minor breaking change (backward compatible with default)
❌ **No Automatic Rotation:** Manual process (acceptable for department scale)
❌ **Database Dependency:** Keys in PostgreSQL (not external secret manager)

### Mitigation

**TokenPayload Migration:**
```python
# Existing tokens without scopes still valid
token = {
    "sub": "user123",
    "role": "admin",
    # No scopes field
}
# TokenPayload.scopes defaults to [] (empty list)
# Existing code continues to work
```

**Future Vault Integration:**
```python
# v2: Add Vault provider (Strategy Pattern)
class SecretProvider(Protocol):
    def get_secret(self, key: str) -> str: ...

class PostgresSecretProvider(SecretProvider):
    def get_secret(self, key: str) -> str:
        # Current implementation
        pass

class VaultSecretProvider(SecretProvider):
    def get_secret(self, key: str) -> str:
        # Future implementation
        pass

# Config-driven selection
SECRET_PROVIDER = os.getenv("SECRET_PROVIDER", "postgres")  # or "vault"
```

---

## Security Considerations

### Token Security (ADR-049 Compliance)

- JWT signed with HS256 (existing pattern)
- Short-lived access tokens (30 minutes)
- Long-lived refresh tokens (7 days, revocable)
- Tokens validated on every request
- Invalid tokens = HTTP 401

### Secret Protection

- Provider API keys **never logged** (ADR-045 redaction)
- API keys **never in error messages**
- Database encryption at rest (PostgreSQL native + `pgcrypto`)
- Admin UI shows masked keys (`sk-...***...xyz`)
- Key updates require `gateway:admin` scope + `admin` role

### Logging & Redaction

**Safe to Log:**
```json
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "enabled": true
}
```

**NEVER Log:**
```json
{
    "api_key": "sk-actual-secret-key"  // ← REDACTED
}
```

**Implementation:**
```python
# src/inference-gateway/app/models/provider.py
class ProviderConfig(BaseModel):
    name: str
    type: str
    base_url: str
    api_key: str  # Not included in __repr__ or logs

    def __repr__(self):
        return f"Provider(name={self.name}, type={self.type}, base_url={self.base_url})"

    def to_log_dict(self):
        """Safe dictionary for logging (no secrets)."""
        return {
            "name": self.name,
            "type": self.type,
            "base_url": self.base_url,
            "enabled": self.enabled
        }
```

---

## Implementation Notes

### Token Generation for Services

**Create Service Account:**
```python
# Backend script: create_service_accounts.py
from shared.auth import auth_manager

# Create orchestrator service account
service_token = auth_manager.create_access_token(
    data={
        "sub": "service:orchestrator-api",
        "user_id": str(orchestrator_service_uuid),
        "role": "service",
        "scopes": ["inference:chat"]  # NEW
    },
    expires_delta=timedelta(days=365)  # Long-lived service token
)

# Store in orchestrator's environment
GATEWAY_SERVICE_TOKEN=<token>
```

**Orchestrator Configuration:**
```python
# src/orchestrator/app/config.py
GATEWAY_SERVICE_TOKEN = os.getenv("GATEWAY_SERVICE_TOKEN")

# src/orchestrator/app/clients/gateway_client.py
class GatewayClient:
    def __init__(self):
        self.base_url = os.getenv("INFERENCE_GATEWAY_URL")
        self.token = os.getenv("GATEWAY_SERVICE_TOKEN")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

### Admin UI Integration

**Provider Management Page:**
- List all providers (name, type, status, last updated)
- Add/Edit/Delete providers
- Test connection button (sends test request to verify key)
- Enable/Disable toggle
- Reload config button (no restart needed)

**Form Fields:**
- Provider Name (readonly for edit, text for create)
- Provider Type (dropdown: OpenAI, OpenAI-Compatible, VLLM)
- Base URL (text input)
- API Key (password input, show masked on edit)
- Enabled (checkbox)

---

## Acceptance Criteria

✅ **TokenPayload Extended:**
- `scopes` field added with default empty list
- Backward compatible with existing tokens
- `has_scope()` and `has_any_scope()` methods implemented
- Tests pass for scope validation

✅ **Gateway Authorization:**
- Requests without JWT return HTTP 401
- Requests without required scope return HTTP 403
- Data plane requires `inference:*` scope
- Control plane requires `gateway:admin` scope

✅ **Secret Management:**
- Provider keys stored encrypted in database
- Admin can update keys via UI/API
- Reload endpoint refreshes config without restart
- Keys never appear in logs or error messages

✅ **Audit Trail:**
- Key updates logged with admin user ID
- Provider config changes tracked in `audit_logs` table
- All Gateway requests logged with service/user context

---

## References

### Related ADRs

- **ADR-049:** Unified Authentication & Security (base infrastructure)
- **ADR-045:** Secure Logging with Redaction (secret protection)
- **ADR-050:** Inference Gateway and Responsibility Split (this track)
- **ADR-052:** Model Routing and Provider Fallback (this track)
- **ADR-053:** Rate Limiting and Usage Tracking (this track)

### Existing Code

- `src/shared/auth/models.py` - TokenPayload definition
- `src/shared/auth/manager.py` - UnifiedAuthManager
- `src/shared/auth/router.py` - Authentication endpoints
- `src/orchestrator/app/middleware/audit.py` - Audit logging pattern

### External References

- OAuth2 Scopes: https://oauth.net/2/scope/
- PostgreSQL pgcrypto: https://www.postgresql.org/docs/current/pgcrypto.html
- JWT Best Practices: https://datatracker.ietf.org/doc/html/rfc8725

---

**Document Owner:** Security Team
**Last Updated:** 2025-11-02
**Status:** Approved for Implementation
