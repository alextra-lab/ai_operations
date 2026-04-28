# ADR-049: Unified Authentication and Security Implementation

**Status:** Accepted
**Date:** 2025-11-02
**Deciders:** Security Team, Backend Team, Frontend Team
**Tags:** security, authentication, jwt, rbac, microservices

---

## Context

AI Operations Platform is a multi-service SOC platform that requires:

- **Secure authentication** across multiple microservices (Backend, Retrieval, Embedding, LLM Guard)
- **Role-based access control** (RBAC) with fine-grained permissions
- **Token-based authentication** suitable for stateless API design
- **Session management** with secure token refresh and revocation
- **Data isolation** ensuring users only access their own data
- **Audit compliance** with comprehensive logging of all access
- **Air-gapped deployment** support without external authentication services
- **Frontend-backend integration** with Angular web application

**Security Requirements:**

- GDPR/CCPA compliance (data isolation)
- SOC 2 Type II (access controls and audit logging)
- Zero-trust architecture
- Defense-in-depth security model
- Secure credential storage and transmission

## Decision

We implement a **Unified Authentication System** using JWT (JSON Web Tokens) with the following architecture:

### Core Components

1. **Shared Authentication Module** (`src/shared/auth/`)
   - Centralized authentication logic used by all services
   - JWT token generation and validation
   - User management and database operations
   - Standardized authentication endpoints

2. **Multi-Layer Security Architecture**
   - JWT authentication (application layer)
   - Row-Level Security/RLS (database layer)
   - Security headers (transport layer)
   - Input sanitization (LLM-Guard integration)
   - Comprehensive audit logging

3. **Role-Based Access Control**
   - Predefined roles: `admin`, `user`, `service`, `corpus_admin`, `use_case_publisher`, `conversations_privileged`
   - FastAPI dependency injection for role enforcement
   - Database-level RLS policies

4. **Token Management**
   - Short-lived access tokens (30 minutes)
   - Long-lived refresh tokens (7 days)
   - Database-stored refresh tokens with revocation support
   - Secure token rotation

---

## Implementation Details

### 1. Shared Authentication Module

#### Base AuthManager (`src/shared/auth/base.py`)

```python
class AuthManager:
    """Base JWT authentication manager."""

    def __init__(self,
                 secret: str,
                 algorithm: str = "HS256",
                 issuer: str = "ai-operations-platform",
                 access_token_expire_minutes: int = 30,
                 refresh_token_expire_days: int = 7):
        # Validates JWT_SECRET on initialization
        if not secret or secret == "mysecretkey":
            raise RuntimeError("JWT_SECRET is missing or insecure!")
        self.secret = secret
        # ... other initialization

    def create_access_token(self, data: Dict) -> str:
        """Create short-lived access token with user claims."""

    def create_refresh_token(self, data: Dict) -> str:
        """Create long-lived refresh token."""

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token."""
```

**Token Structure:**

Access Token Claims:

```json
{
  "sub": "username",
  "user_id": "uuid-string",
  "role": "admin",
  "exp": 1234567890,
  "iat": 1234567890,
  "iss": "ai-operations-platform",
  "token_type": "access"
}
```

Refresh Token Claims:

```json
{
  "sub": "username",
  "user_id": "uuid-string",
  "exp": 1234567890,
  "iat": 1234567890,
  "iss": "ai-operations-platform",
  "token_type": "refresh"
}
```

#### UnifiedAuthManager (`src/shared/auth/manager.py`)

Extends `AuthManager` with database operations and FastAPI integration:

```python
class UnifiedAuthManager(AuthManager):
    """Extended auth manager with database operations."""

    # Password Management
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify password using bcrypt."""

    def get_password_hash(self, password: str) -> str:
        """Hash password with bcrypt and auto-generated salt."""

    # Token Operations
    def verify_token_enhanced(self, token: str) -> TokenPayload | None:
        """Enhanced verification with structured TokenPayload."""

    def get_user_from_request(self, credentials) -> TokenPayload:
        """Extract and validate user from HTTP Authorization header."""

    # FastAPI Dependencies
    def get_current_user(self) -> Callable:
        """Dependency for extracting authenticated user."""

    def admin_required(self) -> Callable:
        """Dependency requiring admin role."""

    def service_required(self) -> Callable:
        """Dependency requiring service or admin role."""

    # Database Operations
    async def authenticate_user(self, db, username, password) -> User | None:
        """Authenticate user with username/password."""

    async def create_user(self, db, username, password, ...) -> User:
        """Create new user with hashed password."""

    async def store_refresh_token(self, db, user_id, token, expires_at):
        """Store refresh token in database for tracking."""

    async def validate_refresh_token(self, db, token) -> User | None:
        """Validate refresh token and return associated user."""

    async def revoke_refresh_token(self, db, token) -> bool:
        """Revoke refresh token (for logout)."""
```

#### Database Models (`src/shared/auth/models.py`)

**User Model:**

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    center_id = Column(String)  # Organization identifier
    user_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    last_login = Column(DateTime(timezone=True))

    refresh_tokens = relationship("RefreshToken", back_populates="user")
```

**RefreshToken Model:**

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="refresh_tokens")
```

**UserRole Enum:**

```python
class UserRole(str, Enum):
    ADMIN = "admin"  # Full system access
    CORPUS_ADMIN = "corpus_admin"  # Document/collection management
    SERVICE = "service"  # Service-to-service communication
    USER = "user"  # Standard user
    USE_CASE_PUBLISHER = "use_case_publisher"  # Use case development
    CONVERSATIONS_PRIVILEGED = "conversations_privileged"  # Conversations UI/API
```

#### Authentication Router (`src/shared/auth/router.py`)

Provides complete authentication API:

**Endpoints:**

- `POST /auth/token` - Login with username/password
- `POST /auth/refresh` - Refresh access token
- `POST /auth/revoke` - Revoke refresh token (logout)
- `GET /auth/validate` - Validate current token
- `POST /auth/users` - Create user (admin only)
- `GET /auth/users` - List users (admin only)
- `GET /auth/users/{id}` - Get user by ID (admin only)
- `PUT /auth/users/{id}` - Update user (admin only)
- `GET /auth/me` - Get current user profile
- `DELETE /auth/users/{id}` - Deactivate user (admin only)
- `POST /auth/users/{id}/reset-password` - Reset password (admin only)
- `GET /auth/users/{id}/sessions` - Get user sessions (admin only)
- `DELETE /auth/users/{id}/sessions/{session_id}` - Force logout (admin only)

### 2. Multi-Service Integration

Each microservice uses the shared authentication module:

#### Backend Service (`src/orchestrator/app/main.py`)

```python
from shared.auth import auth_router, init_database

# Include authentication router
app.include_router(auth_router)

# Initialize database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
```

#### Service-Specific Auth Utilities

Each service has a thin wrapper for backward compatibility:

**Backend** (`src/orchestrator/app/utils/auth.py`):

```python
from shared.auth import (
    auth_manager as jwt_validator,
    admin_required as admin_auth_required,
    get_current_user,
    service_required as service_auth_required,
)
```

**Retrieval** (`src/corpus_svc/app/utils/auth.py`):

```python
from shared.auth import (
    TokenPayload,
    admin_required as admin_auth_required,
    auth_manager as jwt_validator,
    get_current_user,
    service_required as service_auth_required,
)

def extract_user_id_from_token(current_user: TokenPayload) -> uuid.UUID:
    """Extract and validate user UUID from token payload."""
    return uuid.UUID(current_user.user_id)
```

**Embedding** (`src/embedding/app/utils/auth.py`):

```python
from shared.auth import (
    admin_required as admin_auth_required,
    auth_manager as jwt_validator,
    get_current_user,
)
```

**LLM Guard** (`src/llm_guard_svc/app/utils/auth.py`):

```python
from shared.auth import (
    admin_required as admin_auth_required,
    auth_manager as jwt_validator,
    get_current_user,
    service_required as service_auth_required,
)
```

### 3. Security Middleware Layers (Backend Service)

#### Layer 1: Request ID Tracking (`shared.logging_utils.fastapi`)

```python
app.add_middleware(RequestIDLoggerMiddleware)
```

- Generates unique request ID for tracing
- Adds request ID to all logs
- First middleware to ensure ID available for all subsequent layers

#### Layer 2: Row-Level Security (`src/orchestrator/app/middleware/rls.py`)

```python
async def rls_middleware(request, call_next):
    """Set PostgreSQL session variables for RLS policies."""
    # Extract JWT token
    token_payload = jwt_validator.verify_token(token)

    if token_payload:
        # Set RLS session variables
        await db.execute(
            "SET LOCAL aio.user_id = :user_id",
            {"user_id": token_payload["user_id"]}
        )
        await db.execute(
            "SET LOCAL aio.user_roles = :roles",
            {"roles": f"{{{roles_str}}}"}
        )

    return await call_next(request)
```

**Benefits:**

- Database-enforced data isolation
- Cannot be bypassed by SQL injection
- Consistent security across all database operations
- See ADR-039 for full RLS implementation

#### Layer 3: Request Sanitization (`src/orchestrator/app/middleware/sanitization.py`)

```python
async def sanitize_request(request, call_next):
    """Sanitize incoming request data using LLM-Guard."""
    if request.method in ["POST", "PUT", "PATCH"]:
        # Skip file uploads
        if content_type.startswith("multipart/form-data"):
            return await call_next(request)

        # Sanitize request body
        body_text = await request.body()
        sanitized, risk_score, modified = await sanitize_input(body_text)

        # Log sanitization results
        logger.info("Request sanitization", extra={
            "risk_score": risk_score,
            "modified": modified,
            "redaction_enabled": REDACT_LOGS
        })

    return await call_next(request)
```

**Features:**

- LLM-Guard integration for prompt injection detection
- Configurable redaction levels for sensitive data
- Risk scoring for suspicious inputs
- Skips sanitization for file uploads

#### Layer 4: Audit Logging (`src/orchestrator/app/middleware/audit.py`)

```python
async def audit_middleware(request, call_next):
    """Record structured audit information."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Extract user from JWT
    token_payload = jwt_validator.verify_token(token)

    # Persist to audit_logs table
    audit_entry = AuditLog(
        actor_user_id=token_payload.get("user_id"),
        actor_roles=extract_roles(token_payload),
        action=f"{request.method} {request.url.path}",
        resource_type="http_request",
        request_id=request_id,
        client_ip=request.client.host,
        success=(response.status_code < 400),
        details={"duration_ms": duration_ms}
    )
    db.add(audit_entry)
    db.commit()

    return response
```

**Audit Log Schema:**

- `actor_user_id` (UUID)
- `actor_roles` (list of strings)
- `action` (e.g., "POST /auth/token")
- `resource_type` (e.g., "http_request", "user", "document")
- `resource_id` (optional)
- `request_id` (for tracing)
- `client_ip`
- `user_agent`
- `success` (boolean)
- `details` (JSON)
- `timestamp`

#### Layer 5: Security Headers (`src/orchestrator/app/middleware/security_headers.py`)

```python
DEFAULT_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "1; mode=block",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss:; "
        "report-uri /api/security/csp-report"
    ),
}

async def security_headers_middleware(request, call_next):
    """Apply security headers to all responses."""
    response = await call_next(request)

    for header, value in DEFAULT_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value

    return response
```

**CSP Violation Reporting:**

- Endpoint: `POST /api/security/csp-report`
- Logs all CSP violations for security monitoring
- Router: `src/orchestrator/app/routers/security.py`

### 4. Frontend Integration (Angular)

#### AuthService (`src/frontend-angular/src/app/core/auth/auth.service.ts`)

```typescript
@Injectable({ providedIn: 'root' })
export class AuthService {
    private state$ = new BehaviorSubject<AuthState>(AUTH_STATE_INITIAL);

    login(credentials: LoginRequest): Observable<UserProfile> {
        return this.http.post<AuthResponse>('/auth/token', credentials)
            .pipe(
                map(response => {
                    const tokens = this.mapTokens(response);
                    this.persistTokens(tokens);
                    return this.decodeUserProfile(tokens.accessToken);
                }),
                tap(profile => this.setState({
                    isAuthenticated: true,
                    user: profile,
                    tokens: this.state$.value.tokens
                }))
            );
    }

    refreshToken(): Observable<AuthTokens | null> {
        const refreshToken = this.storage.getToken(TokenType.Refresh);
        if (!refreshToken) return of(null);

        return this.http.post<RefreshResponse>('/auth/refresh', {
            refresh_token: refreshToken
        }).pipe(
            map(response => this.mapTokens(response)),
            tap(tokens => this.persistTokens(tokens))
        );
    }

    logout(): Observable<void> {
        const refreshToken = this.storage.getToken(TokenType.Refresh);

        return this.http.post<void>('/auth/revoke', {
            refresh_token: refreshToken
        }).pipe(
            finalize(() => this.clearSession())
        );
    }
}
```

#### Auth Interceptor (`src/frontend-angular/src/app/core/interceptors/auth.interceptor.ts`)

```typescript
export function authInterceptor(request: HttpRequest<unknown>, next: HttpHandlerFn) {
    // Skip if marked to bypass
    if (request.context.get(BYPASS_AUTH_INTERCEPTOR)) {
        return next(request);
    }

    const authService = inject(AuthService);
    const token = authService.getAccessToken();

    if (!token) return next(request);

    // Clone request and add Authorization header
    const authorized = request.clone({
        setHeaders: { Authorization: `Bearer ${token}` }
    });

    return next(authorized);
}
```

#### Secure Storage (`src/frontend-angular/src/app/core/services/secure-storage.service.ts`)

```typescript
@Injectable({ providedIn: 'root' })
export class SecureStorageService {
    setTokens(tokens: AuthTokens): void {
        this.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
        this.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
        this.setItem(`${ACCESS_TOKEN_KEY}:exp`, tokens.accessTokenExpiresAt);
        this.setItem(`${REFRESH_TOKEN_KEY}:exp`, tokens.refreshTokenExpiresAt);
    }

    getToken(type: TokenType): string | null {
        const key = type === TokenType.Access ? ACCESS_TOKEN_KEY : REFRESH_TOKEN_KEY;
        return this.getItem(key);
    }

    clearTokens(): void {
        this.removeItem(ACCESS_TOKEN_KEY);
        this.removeItem(REFRESH_TOKEN_KEY);
        this.removeItem(`${ACCESS_TOKEN_KEY}:exp`);
        this.removeItem(`${REFRESH_TOKEN_KEY}:exp`);
    }
}
```

**Security Considerations:**

- Access tokens stored in memory when possible
- Refresh tokens stored in secure storage
- Automatic token rotation on refresh
- Secure logout with token revocation

### 5. Configuration

#### Environment Variables

**Required:**

```bash
JWT_SECRET=<strong-random-secret>  # REQUIRED - Application fails if missing/weak
```

**Optional (with defaults):**

```bash
JWT_ALGORITHM=HS256  # Default: HS256
JWT_ISSUER=ai-operations-platform  # Default: ai-operations-platform
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Default: 30 minutes
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7  # Default: 7 days
```

**Database:**

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
# OR individual variables:
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aio
```

#### Startup Validation

```python
# src/shared/auth/base.py
def __init__(self, secret: str | None = None, ...):
    _secret = secret or os.environ.get("JWT_SECRET")
    if not _secret or _secret == "mysecretkey":
        raise RuntimeError(
            "JWT_SECRET is missing or insecure! "
            "Set a strong value in your environment."
        )
```

**Benefits:**

- Application fails fast on startup if misconfigured
- Prevents accidental deployment with weak secrets
- Clear error messages for configuration issues

### 6. Testing Strategy

#### Unit Tests (`src/shared/tests/unit/auth/`)

**test_base.py:**

- JWT token creation
- Token validation
- Token expiration
- Invalid token handling

**test_manager.py:**

- Password hashing and verification (bcrypt)
- Token payload validation
- Role-based dependency creation
- User extraction from requests

**test_manager_db.py:**

- User authentication
- User creation
- Refresh token storage
- Refresh token validation
- Token revocation

**test_models.py:**

- User model serialization
- Role validation
- TokenPayload validation

**test_shared_router.py:**

- Login endpoint
- Token refresh
- Token revocation
- User management endpoints (admin)

#### Test Coverage

- **Unit Tests:** 80%+ coverage for authentication logic
- **Integration Tests:** End-to-end auth flows
- **Security Tests:** Token validation, role enforcement, RLS policies

#### Test Fixtures

```python
@pytest.fixture
def manager():
    return UnifiedAuthManager(secret="superstrongtestsecret123!")

@pytest.fixture
def fake_user():
    return User(
        id=uuid.uuid4(),
        username="testuser",
        hashed_password=manager.get_password_hash("password"),
        role=UserRole.USER
    )
```

---

## Alternatives Considered

### 1. OAuth2 with External Provider

**Description:** Use external OAuth2 providers (Auth0, Okta, etc.)

**Pros:**

- Mature, battle-tested solutions
- Built-in features (MFA, SSO, social login)
- Reduced maintenance burden

**Cons:**

- Requires internet connectivity
- Not suitable for air-gapped deployments
- Vendor lock-in
- Additional cost
- External dependency for critical functionality

**Why Rejected:** Air-gapped deployment requirement and zero-trust architecture mandate self-contained authentication.

### 2. Session-Based Authentication (Cookies)

**Description:** Traditional server-side sessions with session cookies

**Pros:**

- Simpler token management
- Native browser security (HttpOnly cookies)
- Easy revocation

**Cons:**

- Not suitable for microservices
- CSRF protection required
- Stateful (requires session store)
- Scaling challenges
- API-first design incompatibility

**Why Rejected:** Microservices architecture and API-first design require stateless authentication.

### 3. API Keys Only

**Description:** Simple API key authentication without JWT

**Pros:**

- Very simple to implement
- No token expiration complexity
- Easy to understand

**Cons:**

- No user context in requests
- No fine-grained permissions
- No built-in expiration
- Difficult to revoke without database lookup on every request
- No standard for claims/metadata

**Why Rejected:** Insufficient for RBAC requirements and audit logging needs.

### 4. Separate Auth Service

**Description:** Dedicated authentication microservice

**Pros:**

- Separation of concerns
- Scalable independently
- Centralized user management

**Cons:**

- Additional service to maintain
- Network overhead on every request
- Single point of failure
- Increased complexity
- Latency impact

**Why Rejected:** Shared module approach provides same benefits with less operational overhead.

---

## Consequences

### Positive Consequences

**Security:**

- ✅ Defense-in-depth with multiple security layers
- ✅ Database-enforced RLS provides failsafe data isolation
- ✅ Comprehensive audit trail for compliance
- ✅ Token revocation prevents compromised token reuse
- ✅ Bcrypt password hashing with auto-generated salts
- ✅ Non-enumerable UUID user identifiers

**Architecture:**

- ✅ Unified authentication across all microservices
- ✅ Stateless JWT authentication suitable for scaling
- ✅ Service-specific auth utilities for flexibility
- ✅ Air-gapped deployment support

**Developer Experience:**

- ✅ Simple FastAPI dependency injection (`Depends(get_current_user)`)
- ✅ Consistent authentication patterns across services
- ✅ Well-tested shared authentication module
- ✅ Clear error messages and validation

**Operations:**

- ✅ Environment-based configuration
- ✅ Startup validation prevents misconfigurations
- ✅ Structured logging with request tracing
- ✅ CSP violation reporting for security monitoring

### Negative Consequences

**Complexity:**

- ❌ Multiple middleware layers increase debugging complexity
- ❌ RLS session variables require careful testing
- ❌ JWT tokens cannot be invalidated without database lookup (refresh tokens only)
- ❌ Token expiration requires client-side refresh logic

**Performance:**

- ❌ JWT validation overhead on every request
- ❌ Database lookup for refresh token validation
- ❌ RLS policies add query planning overhead
- ❌ Multiple middleware layers add latency

**Limitations:**

- ❌ No built-in MFA support (future enhancement)
- ❌ No social login (not required for SOC platform)
- ❌ No password reset via email (would require external dependency)
- ❌ Access tokens cannot be revoked before expiration (design trade-off)

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| JWT_SECRET compromise | **Critical** | - Validate at startup<br>- Use strong secrets (32+ chars)<br>- Rotate periodically<br>- Store in secrets manager |
| Token theft (XSS) | **High** | - CSP headers prevent XSS<br>- Short-lived access tokens<br>- HttpOnly cookies for refresh tokens<br>- Secure token storage in frontend |
| Replay attacks | **Medium** | - Short token expiration<br>- Request ID tracking<br>- Audit logging<br>- HTTPS only in production |
| RLS policy bypass | **Medium** | - FORCE ROW LEVEL SECURITY on all tables<br>- Don't use superuser for app connections<br>- Regular security audits<br>- Unit tests for RLS policies |
| Password brute force | **Medium** | - Bcrypt slow hashing<br>- Rate limiting (future)<br>- Account lockout (future)<br>- Audit logging of failed attempts |
| Session fixation | **Low** | - New tokens on login<br>- Token rotation on refresh<br>- Revoke old tokens<br>- Secure random token generation |

---

## Implementation Notes

### Files Modified/Created

**Shared Module:**

- `src/shared/auth/__init__.py` - Public API exports
- `src/shared/auth/base.py` - Base AuthManager
- `src/shared/auth/manager.py` - UnifiedAuthManager
- `src/shared/auth/models.py` - User, RefreshToken, UserRole models
- `src/shared/auth/router.py` - Authentication endpoints
- `src/shared/auth/database.py` - Database connection management

**Service Integration:**

- `src/orchestrator/app/utils/auth.py` - Backend auth wrapper
- `src/corpus_svc/app/utils/auth.py` - Retrieval auth wrapper
- `src/embedding/app/utils/auth.py` - Embedding auth wrapper
- `src/llm_guard_svc/app/utils/auth.py` - LLM Guard auth wrapper

**Middleware (Backend):**

- `src/orchestrator/app/middleware/rls.py` - Row-level security
- `src/orchestrator/app/middleware/security_headers.py` - Security headers
- `src/orchestrator/app/middleware/sanitization.py` - Input sanitization
- `src/orchestrator/app/middleware/audit.py` - Audit logging

**Frontend:**

- `src/frontend-angular/src/app/core/auth/auth.service.ts`
- `src/frontend-angular/src/app/core/auth/auth.models.ts`
- `src/frontend-angular/src/app/core/interceptors/auth.interceptor.ts`
- `src/frontend-angular/src/app/core/services/secure-storage.service.ts`

**Tests:**

- `src/shared/tests/unit/auth/test_base.py`
- `src/shared/tests/unit/auth/test_manager.py`
- `src/shared/tests/unit/auth/test_manager_db.py`
- `src/shared/tests/unit/auth/test_models.py`
- `src/shared/tests/unit/auth/test_shared_router.py`

### Dependencies

**Python:**

- `python-jose[cryptography]` - JWT token handling
- `bcrypt` - Password hashing
- `passlib[bcrypt]` - Password utilities
- `SQLAlchemy` - Database ORM
- `asyncpg` - Async PostgreSQL driver
- `fastapi` - Web framework
- `pydantic` - Data validation

**TypeScript/Angular:**

- `@angular/common/http` - HTTP client
- `rxjs` - Reactive programming

### Database Migrations

**users table:**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    center_id VARCHAR,
    user_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

**refresh_tokens table:**

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
```

**audit_logs table:**

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id),
    actor_roles VARCHAR[],
    action VARCHAR NOT NULL,
    resource_type VARCHAR NOT NULL,
    resource_id VARCHAR,
    request_id VARCHAR,
    client_ip VARCHAR,
    user_agent VARCHAR,
    success BOOLEAN DEFAULT true,
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_logs_actor_user_id ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
```

### Testing Commands

```bash
# Run authentication tests
pytest src/shared/tests/unit/auth/ -v --cov=src.shared.auth

# Run integration tests
pytest tests/integration/test_auth_integration.py -v

# Run all tests with coverage
python ops/testing/run_all_tests.py --cov=app --cov-report=term-missing
```

---

## Security Checklist

### Pre-Production

- [ ] JWT_SECRET set to strong, random value (32+ characters)
- [ ] JWT_SECRET stored in secrets manager (not in code/env files)
- [ ] All services using shared auth module
- [ ] RLS policies enabled on all sensitive tables
- [ ] FORCE ROW LEVEL SECURITY enabled
- [ ] Security headers middleware enabled
- [ ] Audit logging enabled and tested
- [ ] CORS configured with specific origins (not *)
- [ ] HTTPS enforced in production
- [ ] CSP headers configured and tested
- [ ] Password hashing verified (bcrypt with auto-salt)
- [ ] Token expiration times appropriate for use case
- [ ] Refresh token revocation tested
- [ ] Database connection using non-superuser account
- [ ] Input sanitization tested
- [ ] XSS protection verified
- [ ] SQL injection tests passing

### Post-Production

- [ ] Monitor failed login attempts
- [ ] Review audit logs regularly
- [ ] Track CSP violations
- [ ] Monitor token refresh patterns
- [ ] Review access patterns for anomalies
- [ ] Rotate JWT_SECRET periodically
- [ ] Update dependencies for security patches
- [ ] Conduct regular security audits
- [ ] Test disaster recovery procedures
- [ ] Review and update role permissions

---

## Monitoring

### Key Metrics

**Authentication:**

- Failed login attempts per user/IP
- Token refresh frequency
- Token validation errors
- Average authentication latency

**Security:**

- CSP violations count
- Suspicious activity patterns
- Admin action frequency
- RLS policy violations

**Performance:**

- JWT validation latency (p50, p95, p99)
- Database query performance with RLS
- Middleware overhead
- Token refresh latency

### Alerts

**Critical:**

- Multiple failed login attempts (>5 in 5 minutes)
- JWT_SECRET missing or weak on startup
- RLS policies not applied
- Database connection as superuser

**High:**

- CSP violations (>10 per hour)
- Unusual admin access patterns
- Token validation failure spike
- Audit logging failures

**Medium:**

- Token refresh failures
- Session revocation failures
- Password reset attempts

---

## Future Enhancements

### Planned

1. **Multi-Factor Authentication (MFA)**
   - TOTP support
   - SMS/Email verification
   - Backup codes

2. **Rate Limiting**
   - Login attempt throttling
   - API rate limits per user/role
   - Distributed rate limiting (Redis)

3. **Advanced Audit Features**
   - Real-time security dashboard
   - Anomaly detection
   - Automated threat response

4. **Session Management**
   - Active session listing
   - Device tracking
   - Geographic login alerts

### Under Consideration

- OAuth2/OIDC support for enterprise SSO
- Hardware security key support (WebAuthn)
- Passwordless authentication
- Biometric authentication
- IP allowlisting/denylisting
- Time-based access restrictions

---

## References

### Related ADRs

- **ADR-037:** UUID Primary Keys (provides secure, non-enumerable user IDs)
- **ADR-039:** Row-Level Security Model (database-layer data isolation)
- **ADR-048:** Secure Logging and Redaction (audit logging with PII protection)

### Implementation Plans

- `docs/development/plans/UI_DEVELOPMENT_PLAN.md` - Frontend authentication
- `docs/api/authentication.md` - API documentation

### External Resources

- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [PostgreSQL Row Security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## Status Updates

### 2025-11-02 - Initial Documentation

**Changed By:** Security Team, Backend Team, Frontend Team
**Reason:** Document existing unified authentication and security implementation after system audit. All security layers implemented and tested across microservices.

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
