# Feature Implementation Prompt - Universal Template

**Purpose:** Execute next sequential feature with full context, precision, and security
**Usage:** Copy this prompt into a new chat when ready to implement the next feature
**Last Updated:** October 1, 2025

---

## 🎯 Implementation Request

**Implement the next sequential feature from the active development plan.**

## 📋 Pre-Implementation Analysis

### 1. Identify Active Development Track

Determine which development track to work on:

- **Backend Track**: `@UNIFIED_BACKEND_IMPLEMENTATION_PLAN.md`
  - Current Phase: **COMPLETE**

- **UI Track**: `@UI_DEVELOPMENT_PLAN.md`
  - Current Phase: [TBD - Angular 18 implementation]
  - Next Feature: [Automatically determined from plan status]

- **Tools Track**: `@TOOLS_IMPLEMENTATION_PLAN.md`
  - Current Phase: T1 (Tool Infrastructure Foundation)
  - Architecture: Hybrid (see `@TOOLS_HYBRID_ARCHITECTURE_UPDATE.md`)
  - Next Feature: [Automatically determined from plan status]

**Action Required:**

1. Read the appropriate implementation plan
2. Identify the first feature marked ⏳ **PENDING**
3. Verify all dependencies in that phase are ✅ **COMPLETE**
4. Confirm this is the correct next feature to implement

### 2. Verify System Prerequisites

#### For Backend/Tools Features

```bash
# Check test environment status
export $(grep -v '^#' config/env/env.test | xargs)
docker-compose -f deploy/docker-compose.test.yml ps

# Test API connectivity
curl -s http://localhost:8006/health

# Backend Endpoing and Contracts
curl -s http://localhost:8006/openapi.json

# Verify database connectivity
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1;"

# Create Acess token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin" -d "password=adminpassword" | jq -r '.access_token')
```


# Imports

Use relative import paths

#### For UI Features

```bash
# Check Angular development environment
cd src/frontend
npm --version
ng version

# Verify backend API is accessible
curl -s http://localhost:8000/health
```

- Check for common anti-patterns in similar features
- Verify naming conventions match existing code
- Ensure security patterns are followed
- Validate that the approach aligns with architecture

- Import paths (absolute vs relative)
- Database connection patterns
- Authentication/authorization patterns
- Error handling consistency

**System Status Check:**

- Test environment status (Docker containers)
- API connectivity (health endpoints)
- Database connectivity (test database)
- Service dependencies (if applicable)

### 3. Context-Aware Implementation

**Core Architecture:**

- `@docs/architecture/SYSTEM_ARCHITECTURE.md` - Overall system design
- `@docs/architecture/AUTHENTICATION_FLOW.md` - Auth patterns
- `@docs/api/authentication.md` - Auth API reference

**Backend-Specific:**

- `@docs/architecture/ORCHESTRATOR_ARCHITECTURE.md` - Orchestrator design
- `@docs/architecture/USE_CASE_ARCHITECTURE.md` - Use case system
- `@src/shared/auth/models.py` - Auth models and RBAC

**Tools-Specific:**

- `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md` - Visual diagrams
- `docs/architecture/TOOL_ALLOWLIST_USAGE.md` - Tool configuration
- `docs/development/plans/TOOLS_IMPLEMENTATION_PLAN.md` - Implementation plan

**UI-Specific:**

- `@.cursor/rules/angular-general.mdc` - Angular coding standards
- `@.cursor/rules/angular-template-hints.mdc` - Template best practices
- `@.cursor/rules/accessibility-guidelines.mdc` - WCAG compliance

### 4. Security & Standards Context

**Authentication & Authorization:**

- All endpoints require authentication unless explicitly documented as public
- Use `@src/shared/auth/` models for RBAC
- JWT tokens required for API calls
- Service-to-service auth uses `SERVICE_AUTH_TOKEN` environment variable

**Test Accounts** (from `ops/bootstrap/seed_test_data.py`):

```
Admin:
  - Username: admin
  - Password: adminpassword
  - Role: admin

Developer:
  - Username: analyst
  - Password: analystpassword
  - Role: developer

User:
  - Username: testuser
  - Password: password
  - Role: user
```

**Code Standards:**

- Python: Type hints mandatory, PEP 8, Ruff formatted
- TypeScript: Angular 18 best practices, max 80 chars/line
- Security: Never log secrets, validate all inputs, use parameterized queries
- Testing: 80%+ coverage, unit + integration tests

---

## 🔧 Implementation Workflow

### Phase 1: Deep Planning & Context Gathering

**Before writing any code, complete this analysis:**

1. **Read Feature Specification**
   - Full feature description from implementation plan
   - Acceptance criteria
   - Dependencies and blockers
   - Quality gates

2. **Identify All Affected Components**
   - List all files to create
   - List all files to modify
   - Identify all database changes
   - Identify all API endpoints (new or modified)
   - Identify all test files needed

3. **Map Dependencies**
   - Which existing services/models will be used?
   - Which new services/models must be created?
   - What schemas are needed (Pydantic, TypeScript interfaces)?
   - What database models are involved?

4. **Security Analysis**
   - Which roles can access this feature?
   - What permissions are required?
   - Are there rate limits or quotas?
   - What audit logging is needed?
   - What secrets/credentials are involved?

5. **Testing Strategy**
   - Unit test scenarios
   - Integration test scenarios
   - Verification script requirements
   - Manual testing steps

**Deliverable:** Provide a comprehensive implementation plan summary before proceeding.

### Phase 2: Incremental Implementation

**Follow this exact order:**

#### Step 1: Database Schema (if needed)

- Create migration file: `ops/migrations/sql/XXX_feature_name.sql`
- Include tables, indexes, constraints, RLS policies
- Add rollback section
- Document all columns with comments

#### Step 2: Pydantic Schemas / TypeScript Interfaces

- Create schemas: `src/orchestrator/app/schemas/<feature>.py` or `src/frontend/app/models/<feature>.ts`
- Include all validators and constraints
- Add docstrings/comments
- Define request/response models

#### Step 3: Database Models (if needed)

- Update: `src/orchestrator/app/db/models.py` or service-specific models
- Add SQLAlchemy models
- Include relationships
- Add indexes

#### Step 4: Business Logic / Services

- Create service: `src/orchestrator/app/services/<feature>_service.py` or Angular service
- Implement core business logic
- Add comprehensive logging
- Handle error cases
- Include type hints

#### Step 5: API Routers / Components

- Create router: `src/orchestrator/app/routers/<feature>.py` or Angular component
- Define all endpoints / UI interactions
- Add authentication/authorization
- Include OpenAPI documentation / Angular docs
- Validate inputs

#### Step 6: Integration Points

- Update orchestrator if needed: `src/orchestrator/app/orchestrator/controller.py`
- Update main app: `src/orchestrator/app/main.py` (router registration)
- Update Angular routing if needed
- Add to dependency injection

#### Step 7: Unit Tests

- Create tests: `src/orchestrator/tests/unit/<module>/test_<feature>.py` or `src/frontend/src/app/<feature>/<feature>.component.spec.ts`
- Test all business logic paths
- Test validation and error cases
- Achieve 90%+ coverage

#### Step 8: Integration Tests

- Create tests: `tests/integration/test_<feature>.py` or Angular e2e tests
- Test end-to-end workflows
- Test authentication/authorization
- Test database operations
- Use real test database

#### Step 9: Verification Script

- Create script: `ops/testing/verify_<feature>.py`
- Test all API endpoints
- Verify all acceptance criteria
- Include clear pass/fail output

#### Step 10: Documentation Updates

- Update implementation plan status
- Update API documentation if needed
- Add inline code documentation
- Update architecture diagrams if needed

### Phase 3: Quality Assurance

**Run all quality gates in this order:**

```bash
# 1. Linting
python -m ruff check src/orchestrator/
python -m ruff format --check src/orchestrator/
# OR for frontend:
cd src/frontend && npm run lint

# 2. Type Checking (Python)
python -m mypy src/orchestrator/app/

# 3. Unit Tests
python -m pytest src/orchestrator/tests/unit/ -v --cov=src/orchestrator/app
# OR for frontend:
cd src/frontend && npm run test

# 4. Integration Tests
python -m pytest tests/integration/test_<feature>.py -v
# OR for frontend:
cd src/frontend && npm run e2e

# 5. Verification Script
python ops/testing/verify_<feature>.py

# 6. Manual API Testing
curl -X POST http://localhost:8006/api/v1/<endpoint> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

**All gates must pass before marking feature complete.**

### Phase 4: Completion

**Before marking the feature complete:**

1. ✅ All code written and tested
2. ✅ All quality gates passed
3. ✅ All acceptance criteria met
4. ✅ Implementation plan updated with ✅ **COMPLETE** status
5. ✅ No linting errors
6. ✅ No security vulnerabilities introduced
7. ✅ All tests passing
8. ✅ Documentation updated

**Update the implementation plan:**

```markdown
## Feature-ID: Feature Name ✅ COMPLETE

**Implemented:** October 1, 2025
**Files Created:** [list]
**Files Modified:** [list]
**Tests Added:** [list]

### Acceptance Criteria
- [x] Criterion 1
- [x] Criterion 2
...
```

---

## 📚 Context References

### Implementation Plans

- Backend: `docs/development/plans/UNIFIED_BACKEND_IMPLEMENTATION_PLAN.md`
- Tools: `docs/development/plans/TOOLS_IMPLEMENTATION_PLAN.md`
- UI: `docs/development/plans/UI_DEVELOPMENT_PLAN.md`

### Architecture Documentation

- Auth: `docs/api/authentication.md`
- Tools: `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`
- Collections: `docs/development/adrs/ADR-021-Collection-Based-Document-Management.md`
- Use Cases: `docs/development/adrs/ADR-018-Use-Case-Owned-Architecture.md`

### Code Standards

- General Reasoning: `.cursor/rules/general-reasoning.mdc`
- Angular General: `.cursor/rules/angular-general.mdc`
- Angular Templates: `.cursor/rules/angular-template-hints.mdc`
- Accessibility: `.cursor/rules/accessibility-guidelines.mdc`
- Performance: `.cursor/rules/performance-optimization.mdc`
- Testing: `.cursor/rules/angular-testing-guidelines.mdc`

### Testing Resources

- Testing Guide: `docs/testing/TESTING_GUIDE.md`
- Troubleshooting: `docs/testing/TROUBLESHOOTING.md`
- Script Index: `docs/testing/SCRIPT_INDEX.md`

### Example Code

- Schema Example: `src/orchestrator/app/schemas/use_case_config.py`
- Service Example: `src/orchestrator/app/services/use_case_service.py`
- Router Example: `src/orchestrator/app/routers/use_cases.py`
- Test Example: `src/orchestrator/tests/unit/schemas/test_use_case_config.py`
- Verification Example: `ops/testing/verify_use_case_config.py`

### Key Source Files

- Auth Models: `src/shared/auth/models.py`
- Database Models: `src/orchestrator/app/db/models.py`
- Orchestrator: `src/orchestrator/app/orchestrator/controller.py`
- Main App: `src/orchestrator/app/main.py`

---

## 🚨 Common Issues & Solutions

### Import Errors

- **Issue**: Module not found errors
- **Solution**: Use absolute imports `from src.backend.app.X import Y` in tests
- **Solution**: Use relative imports `from ..schemas.X import Y` in application code

### Database Connection Issues

- **Issue**: Can't connect to test database
- **Solution**: Verify postgres-test container is running
- **Solution**: Check `DATABASE_URL` environment variable
- **Solution**: Use correct hostname (`postgres-test` in Docker, `localhost` locally)

### Authentication Failures

- **Issue**: 401 Unauthorized errors
- **Solution**: Verify `JWT_SECRET` is set in environment
- **Solution**: Check token hasn't expired
- **Solution**: Verify user has correct role/permissions

### Service Communication (Tools Track)

- **Issue**: Can't reach Retrieval Service from Orchestrator
- **Solution**: Verify `RETRIEVAL_SERVICE_URL` environment variable
- **Solution**: Check `SERVICE_AUTH_TOKEN` is configured
- **Solution**: Ensure both services are running

### Angular Build Issues

- **Issue**: Compilation errors
- **Solution**: Clear node_modules: `rm -rf node_modules && npm install`
- **Solution**: Check Angular version matches requirement (18.x)
- **Solution**: Verify TypeScript version compatibility

---

## 🎯 Feature Implementation Checklist

Use this checklist for each feature:

### Planning Phase

- [ ] Feature identified from implementation plan
- [ ] All dependencies verified as complete
- [ ] Architecture context reviewed
- [ ] Security requirements understood
- [ ] Affected components identified
- [ ] Testing strategy defined

### Implementation Phase

- [ ] Database schema created/updated (if needed)
- [ ] Pydantic schemas / TypeScript interfaces created
- [ ] Database models created/updated (if needed)
- [ ] Business logic / services implemented
- [ ] API routers / components created
- [ ] Integration points updated
- [ ] Unit tests written (90%+ coverage)
- [ ] Integration tests written
- [ ] Verification script created

### Quality Assurance Phase

- [ ] Linting passes
- [ ] Type checking passes (Python)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Verification script passes
- [ ] Manual testing complete
- [ ] Security review complete
- [ ] No secrets in code/logs

### Completion Phase

- [ ] Implementation plan updated
- [ ] Documentation updated
- [ ] All acceptance criteria met
- [ ] Code reviewed (self-review)
- [ ] Ready for next feature

---

## 🔐 Security Checklist

For every feature, verify:

- [ ] **Authentication**: All endpoints require auth unless explicitly public
- [ ] **Authorization**: RBAC enforced based on user role
- [ ] **Input Validation**: All inputs validated (Pydantic/Angular validators)
- [ ] **SQL Injection**: Only parameterized queries used
- [ ] **XSS Prevention**: All user input sanitized (Angular built-in)
- [ ] **CSRF Protection**: Enabled for state-changing operations
- [ ] **Secrets Management**: No secrets in code, logs, or error messages
- [ ] **Audit Logging**: All sensitive operations logged
- [ ] **Rate Limiting**: Implemented for public endpoints
- [ ] **Error Handling**: No sensitive data in error responses

---

## 📝 Implementation Output Format

After completing the feature, provide:

### 1. Summary

```
Feature: [Feature ID and Name]
Status: ✅ COMPLETE
Implementation Date: [Date]
Development Track: [Backend/Tools/UI]
```

### 2. Changes Made

```
Files Created:
- src/orchestrator/app/schemas/feature.py
- src/orchestrator/app/services/feature_service.py
- ...

Files Modified:
- src/orchestrator/app/main.py (added router)
- src/orchestrator/app/db/models.py (added model)
- ...

Tests Added:
- src/orchestrator/tests/unit/test_feature.py (15 tests)
- tests/integration/test_feature.py (8 tests)
- ops/testing/verify_feature.py
```

### 3. Test Results

```
✅ Linting: PASSED
✅ Unit Tests: PASSED (95% coverage)
✅ Integration Tests: PASSED (8/8)
✅ Verification Script: PASSED
✅ Manual Testing: PASSED
```

### 4. Next Steps

```
- Next Feature: [Next feature ID from plan]
- Blockers: [None or list blockers]
- Notes: [Any important notes]
```
