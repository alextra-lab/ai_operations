#!/usr/bin/env bash
#
# Pre-Test Checklist for Load Testing with LMStudio
#
# Run this before executing load tests to verify everything is ready.

set -euo pipefail

echo "=============================================================================="
echo "LOAD TEST PRE-FLIGHT CHECKLIST"
echo "=============================================================================="
echo ""

FAILED=0

# 1. Check LMStudio is running
echo "1. Checking LMStudio server..."
if curl -sf http://localhost:1234/v1/models > /dev/null 2>&1; then
    MODEL_COUNT=$(curl -s http://localhost:1234/v1/models | jq '.data | length')
    echo "   ✅ LMStudio responding (${MODEL_COUNT} model(s) loaded)"
else
    echo "   ❌ LMStudio not responding at http://localhost:1234"
    echo "      → Open LMStudio, load model, start server"
    FAILED=1
fi
echo ""

# 2. Check which model is loaded
if [ $FAILED -eq 0 ]; then
    echo "2. Checking loaded model..."
    MODEL_ID=$(curl -s http://localhost:1234/v1/models | jq -r '.data[0].id' 2>/dev/null || echo "unknown")
    if [ "$MODEL_ID" != "unknown" ] && [ "$MODEL_ID" != "null" ]; then
        echo "   ✅ Model loaded: $MODEL_ID"

        # Recommend fast models
        if [[ "$MODEL_ID" == *"3b"* ]] || [[ "$MODEL_ID" == *"7b"* ]]; then
            echo "   ✅ Good choice for load testing (3B-7B model)"
        else
            echo "   ⚠️  Large model detected - may be slow for load testing"
            echo "      → Consider using llama-3.2-3b or mistral-7b for faster tests"
        fi
    else
        echo "   ❌ No model loaded in LMStudio"
        echo "      → Load llama-3.2-3b-instruct or mistral-7b"
        FAILED=1
    fi
    echo ""
fi

# 3. Warm up model with test request
if [ $FAILED -eq 0 ]; then
    echo "3. Warming up model (sending test request)..."
    START_TIME=$(date +%s%3N)

    RESPONSE=$(curl -s http://localhost:1234/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{
        "model": "'"$MODEL_ID"'",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
      }' 2>/dev/null)

    END_TIME=$(date +%s%3N)
    LATENCY=$((END_TIME - START_TIME))

    if echo "$RESPONSE" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
        echo "   ✅ Model responding (latency: ${LATENCY}ms)"

        if [ $LATENCY -lt 500 ]; then
            echo "   ✅ Good latency for load testing"
        elif [ $LATENCY -lt 1000 ]; then
            echo "   ⚠️  Moderate latency - load test may be slower"
        else
            echo "   ⚠️  High latency - consider smaller model or lower RPS"
        fi
    else
        echo "   ❌ Model not responding correctly"
        echo "      Response: $RESPONSE"
        FAILED=1
    fi
    echo ""
fi

# 4. Check Gateway container
echo "4. Checking Gateway container..."
if docker ps | grep -q inference-gateway-test; then
    if docker exec inference-gateway-test curl -sf http://localhost:8002/health > /dev/null 2>&1; then
        echo "   ✅ Gateway container healthy"
    else
        echo "   ❌ Gateway container running but not healthy"
        FAILED=1
    fi
else
    echo "   ❌ Gateway container not running"
    echo "      → cd deploy && docker-compose -f docker-compose.test.yml up -d inference-gateway"
    FAILED=1
fi
echo ""

# 5. Check Gateway can reach LMStudio
if [ $FAILED -eq 0 ]; then
    echo "5. Checking Gateway → LMStudio connectivity..."
    if docker exec inference-gateway-test curl -sf http://host.docker.internal:1234/v1/models > /dev/null 2>&1; then
        echo "   ✅ Gateway can reach LMStudio on host"
    else
        echo "   ❌ Gateway cannot reach LMStudio"
        echo "      → Check docker.for.mac.host.internal or use host IP"
        FAILED=1
    fi
    echo ""
fi

# 6. Check Redis (for rate limiting)
echo "6. Checking Redis..."
if docker exec redis-test redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis healthy"
else
    echo "   ⚠️  Redis not responding (rate limiting may not work)"
    echo "      → cd deploy && docker-compose -f docker-compose.test.yml up -d redis-cache"
fi
echo ""

# 7. Check system resources
echo "7. Checking system resources..."
echo "   CPU usage: $(top -l 1 | grep "CPU usage" | awk '{print $3}' || echo "unknown")"
echo "   Memory pressure: $(memory_pressure 2>/dev/null | grep "System-wide" || echo "Run 'memory_pressure' for details")"
echo "   ℹ️  Recommendation: Close other applications for accurate test results"
echo ""

# Summary
echo "=============================================================================="
if [ $FAILED -eq 0 ]; then
    echo "✅ PRE-FLIGHT CHECK PASSED"
    echo ""
    echo "You can now run load tests:"
    echo "  python tests/load/load_test.py --model $MODEL_ID --rps 2 --duration 30"
    echo ""
    echo "Recommended test sequence:"
    echo "  1. Baseline:     --rps 1  --duration 30  (establish baseline)"
    echo "  2. Conservative: --rps 2  --duration 60  (sustainable load)"
    echo "  3. Stress:       --rps 5  --duration 30  (find breaking point)"
else
    echo "❌ PRE-FLIGHT CHECK FAILED"
    echo ""
    echo "Please fix the issues above before running load tests."
fi
echo "=============================================================================="

exit $FAILED
