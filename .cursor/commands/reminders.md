# Project reminders

## Load environment variables when using docker

set -Euo pipefail && set -a && source config/env/env.test && set +a

docker-compose -f deploy/docker-compose.test.yml

## To check Backend Endpoint schemas and Contracts

curl -s <http://localhost:8006/openapi.json>

## To Verify database connectivity

docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1;"

## To create an access token

Use credentials from config/env/env.test.template or seed data (see docs). Example (replace with your test credentials):

TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin" -d "password=<admin-password>" | jq -r '.access_token')

## UI accounts (test defaults)

See config/env/env.test.template and ops/database/seed for actual test users. Typical roles: admin, developer, user.

## Services

check deploy/docker-compose.test.yml and config/env/env.test for accounts and ports.

## Key instructions

Use relative import paths for source code.  Use absolute paths for tests
Verify the backend endpoint and their UI counterparts.
Verify that the parameters and response schema match.
Consider testing first, then implementing.
Rebuild containers with --no-cache after you have modified their code, then test.
