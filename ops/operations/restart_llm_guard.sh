#!/bin/bash
# Script to restart the LLM-Guard service with the fixed implementation
# This applies the fix for the "too many values to unpack" error

set -e  # Exit on error

echo "Restarting LLM-Guard service with bug fixes..."

# Determine if this is running in Docker Compose environment
if command -v docker-compose &> /dev/null; then
    echo "Detected Docker Compose environment"

    # Get the current directory of the script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

    # Navigate to the project root where docker-compose.yml should be located
    cd "$PROJECT_ROOT/deploy"

    # Restart only the LLM-Guard service
    echo "Restarting LLM-Guard container"
    docker-compose restart llm-guard

    echo "LLM-Guard service restarted successfully"
else
    # Check for systemd
    if command -v systemctl &> /dev/null; then
        echo "Detected systemd environment"
        sudo systemctl restart llm-guard
    # Check for supervisor
    elif command -v supervisorctl &> /dev/null; then
        echo "Detected supervisor environment"
        supervisorctl restart llm-guard
    # Fall back to a simple process restart by PID
    else
        echo "No service manager detected, attempting direct restart"

        # Try to find the LLM-Guard process and restart it
        LLM_PID=$(pgrep -f "uvicorn.*app:app" || true)

        if [ -n "$LLM_PID" ]; then
            echo "Found LLM-Guard process with PID $LLM_PID"
            echo "Stopping LLM-Guard process"
            kill $LLM_PID

            # Wait for process to terminate
            sleep 2

            # Start the service again
            echo "Starting LLM-Guard service"
            cd /workspace/src/llm-guard
            nohup uvicorn app:app --host 0.0.0.0 --port 8081 > /tmp/llm-guard.log 2>&1 &

            echo "LLM-Guard service restarted with PID $!"
        else
            echo "No running LLM-Guard process found, starting new instance"
            cd /workspace/src/llm-guard
            nohup uvicorn app:app --host 0.0.0.0 --port 8081 > /tmp/llm-guard.log 2>&1 &

            echo "LLM-Guard service started with PID $!"
        fi
    fi
fi

echo "Restart completed."
echo "You can now test the service with: ./scripts/cli/test_llm_guard.py --url http://localhost:8081"
