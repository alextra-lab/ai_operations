# Execute: [TASK_ID from find-next-task output]

Test with: [test command, e.g., "npm test", "run_tests.sh", python script]
Rebuild: [container name if needed]
Verify: [1-2 sentence description of manual check]

## Environment Setup

source <(grep -Ev '^(#|$)' config/env/env.test | sed 's/^/export /')
docker-compose -f deploy/docker-compose.test.yml ps

## Backend Verification

curl -s <http://localhost:8006/openapi.json>
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1;"

## Access Token

Use credentials from config/env or seed (see docs). Example:
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin" -d "password=<admin-password>" | jq -r '.access_token')

## UI accounts (test)

See config/env/env.test.template and ops/database/seed. Roles: admin, developer, user.

## Services

Check deploy/docker-compose.test.yml and config/env/env.test for accounts and ports.

## ADR Compliance (Auto-Check)

BEFORE implementing, determine which ADRs apply to this task:

**If task involves frontend UI/styling:**

- ✅ Follow ADR-012 (Hybrid CSS Strategy)
  - Use Material for UI primitives (buttons, forms, dialogs)
  - Use Tailwind for layout/spacing utilities
  - Use component SCSS only for complex states/animations
  - Verify stylesheet order: Material → Tailwind → app overrides
  - Check: No inline styles, use CSS variables for theming
  - Check: Accessibility preserved (Material defaults)

**If task involves use cases/templates:**

- ✅ Follow ADR-018 (Use Case Owned Architecture)
  - Use Cases own all configuration (prompts + config_json)
  - Prompts: system, developer, fewshots (multi-role)
  - Patterns are read-only (copy to UC, don't reference)
  - No shared templates - reuse via cloning UCs
  - Check: UC has complete config_json
  - Check: Prompts stored in UC, not external

**Determine other relevant ADRs:**

- Read docs/development/adrs/ directory
- List ADRs that apply to files being modified
- Verify compliance before completing task

## Key Instructions

- Verify backend endpoint schemas match UI expectations
- Verify parameters and response schemas match
- Consider test-first approach
- Rebuild containers with --no-cache after code changes
- Test after rebuild

## Create Tests

- Unit tests for new components/services/functions
- Integration tests if crossing service boundaries
- Test coverage target: >90% for new code
- Update existing tests if behavior changed
- **ADR compliance tests** (e.g., CSS class patterns, UC config structure)

## Report Format

Files changed:

- [list with line counts]

Tests:

- X/Y passing
- Coverage: Z%

ADR Compliance:

- ADR-012: [✅ Compliant / ❌ Issues found]
- ADR-018: [✅ Compliant / ❌ Issues found]
- [Other ADRs checked]

Issues/Blockers:

- [list]

DO NOT update plans or commit.
