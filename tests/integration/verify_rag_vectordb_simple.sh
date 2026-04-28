#!/bin/bash
# Simple curl-based verification that RAG-enabled use cases query vectordb
#
# Usage:
#   ./verify_rag_vectordb_simple.sh
#   ./verify_rag_vectordb_simple.sh <use_case_id>
#   ./verify_rag_vectordb_simple.sh <use_case_id> "query text"
#   ORCHESTRATOR_URL=http://localhost:8006 ./verify_rag_vectordb_simple.sh

set -euo pipefail

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8006}"

echo "🔐 Getting auth token..."
TOKEN=$(curl -s -X POST "${ORCHESTRATOR_URL}/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
  echo "❌ Auth failed"
  exit 1
fi

echo "✅ Got token"
echo ""

# Allow use case ID to be passed as first argument, or find one automatically
if [ -n "${1:-}" ]; then
  USE_CASE_ID="$1"
  echo "📋 Using provided use case ID: ${USE_CASE_ID}"
  USE_CASE_NAME=$(curl -s -X GET "${ORCHESTRATOR_URL}/api/v1/use-cases/${USE_CASE_ID}" \
    -H "Authorization: Bearer ${TOKEN}" | jq -r '.name')
else
  echo "📋 Finding use case with RAG enabled..."
  # Try to get RAG config from individual use case endpoints since /available might not include full config
  USE_CASE_ID=$(curl -s -X GET "${ORCHESTRATOR_URL}/api/v1/use-cases/available" \
    -H "Authorization: Bearer ${TOKEN}" | \
    jq -r '.use_cases[].id' | head -1)

  if [ -z "$USE_CASE_ID" ] || [ "$USE_CASE_ID" == "null" ]; then
    echo "❌ No use cases found"
    exit 1
  fi

  # Verify this use case has RAG enabled by checking the full endpoint
  RAG_ENABLED=$(curl -s -X GET "${ORCHESTRATOR_URL}/api/v1/use-cases/${USE_CASE_ID}" \
    -H "Authorization: Bearer ${TOKEN}" | \
    jq -r '.config_json.rag.enabled // false')

  if [ "$RAG_ENABLED" != "true" ]; then
    echo "❌ Use case ${USE_CASE_ID} does not have RAG enabled"
    exit 1
  fi

  USE_CASE_NAME=$(curl -s -X GET "${ORCHESTRATOR_URL}/api/v1/use-cases/${USE_CASE_ID}" \
    -H "Authorization: Bearer ${TOKEN}" | jq -r '.name')
fi

echo "✅ Found: $USE_CASE_NAME"
echo ""

# Allow query to be passed as second argument, or use default
QUERY="${2:-What is threat intelligence?}"

echo "🚀 Executing use case with query: '${QUERY}'..."
RESPONSE=$(curl -s -X POST "${ORCHESTRATOR_URL}/api/v1/use-cases/${USE_CASE_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"inputs\": {
      \"query\": \"${QUERY}\"
    }
  }")

echo "📊 Results:"
echo "$RESPONSE" | jq '{
  sources_count: (.sources | length),
  top_k: .metrics.retrieval.top_k,
  hits: .metrics.retrieval.hits,
  retrieval_active: .metrics.service_status.retrieval_active
}'

echo ""
HITS=$(echo "$RESPONSE" | jq -r '.metrics.retrieval.hits // 0')
TOP_K=$(echo "$RESPONSE" | jq -r '.metrics.retrieval.top_k // 0')
RETRIEVAL_ACTIVE=$(echo "$RESPONSE" | jq -r '.metrics.service_status.retrieval_active // false')

if [ "$RETRIEVAL_ACTIVE" == "true" ] && [ "$TOP_K" -gt 0 ]; then
  echo "✅ VERIFIED: Vectordb query attempted (top_k=${TOP_K}, hits=${HITS})"
  if [ "$HITS" -gt 0 ]; then
    echo "✅ Sources found: ${HITS}"
  else
    echo "⚠️  No sources found (collections may be empty or have name mapping issue)"
  fi
else
  echo "❌ FAILED: Vectordb may not have been queried"
  exit 1
fi
