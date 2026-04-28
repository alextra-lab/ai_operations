#!/bin/bash
set -eo pipefail

# Script to rebuild the LLM-Guard container with fixed dependencies
# Includes sequential startup and health checks for more reliable deployment

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MODEL_CACHE_DIR="${PROJECT_ROOT}/data/llm-guard-models"
COMPOSE_FILE="${PROJECT_ROOT}/deploy/docker-compose.yml"
MAX_RETRIES=10
RETRY_INTERVAL=5

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print a step header
print_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to check if a container is healthy
check_container_health() {
    local container_name="$1"
    local max_attempts="$2"
    local wait_seconds="$3"

    echo -e "${YELLOW}Waiting for ${container_name} to become healthy (max ${max_attempts} attempts, ${wait_seconds}s each)...${NC}"

    for ((i=1; i<=max_attempts; i++)); do
        # Check if container is running
        if ! docker ps -q -f name=^/${container_name}$ > /dev/null 2>&1; then
            # Container not running, check if it exists but stopped
            if docker ps -a -q -f name=^/${container_name}$ > /dev/null 2>&1; then
                echo -e "${RED}Container ${container_name} exists but is not running. Checking logs:${NC}"
                docker logs ${container_name} | tail -n 50
                return 1
            else
                echo -e "${RED}Container ${container_name} does not exist.${NC}"
                return 1
            fi
        fi

        # Check health status
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' ${container_name} 2>/dev/null || echo "unknown")

        if [ "$health_status" = "healthy" ]; then
            echo -e "${GREEN}Container ${container_name} is healthy!${NC}"
            return 0
        elif [ "$health_status" = "unhealthy" ]; then
            echo -e "${RED}Container ${container_name} is unhealthy. Checking logs:${NC}"
            docker logs ${container_name} | tail -n 50
            return 1
        fi

        echo -e "Attempt $i/$max_attempts: Container ${container_name} health status: ${health_status}"
        sleep ${wait_seconds}
    done

    echo -e "${RED}Timed out waiting for ${container_name} to become healthy.${NC}"
    echo -e "${RED}Final container logs:${NC}"
    docker logs ${container_name} | tail -n 50
    return 1
}

print_step "Starting LLM-Guard Rebuild"
echo -e "Rebuilding LLM-Guard container with updated dependencies"

# Verify model cache directory
mkdir -p "$MODEL_CACHE_DIR"
if [ -z "$(ls -A "$MODEL_CACHE_DIR" 2>/dev/null)" ]; then
    echo -e "${RED}Warning: Model cache directory is empty. Required models should be present in:${NC}"
    echo -e "${RED}${MODEL_CACHE_DIR}${NC}"
    echo -e "${YELLOW}Continuing anyway, but LLM-Guard may fail to start without models.${NC}"
else
    echo -e "Model cache directory: ${GREEN}$MODEL_CACHE_DIR${NC}"
    echo -e "$(ls -la "$MODEL_CACHE_DIR" | head -n 10)"
    if [ "$(ls -A "$MODEL_CACHE_DIR" | wc -l)" -gt 10 ]; then
        echo -e "... and more files"
    fi
fi

# Determine docker-compose command
if ! command -v docker-compose &> /dev/null; then
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        echo -e "${RED}Error: docker-compose is not installed or not in the PATH${NC}"
        exit 1
    fi
else
    DOCKER_COMPOSE="docker-compose"
fi

# Go to project root directory
cd "$PROJECT_ROOT"

print_step "Stopping Existing Containers"
# Stop existing containers in reverse dependency order
for container in llm-guard vector-db; do
    echo -e "${YELLOW}Stopping ${container} if running...${NC}"
    docker stop ${container} 2>/dev/null || true
    docker rm ${container} 2>/dev/null || true
done

print_step "Cleaning Docker Images"
# Remove existing images
echo -e "${YELLOW}Removing existing LLM-Guard image...${NC}"
docker rmi llm-guard:latest 2>/dev/null || true
docker rmi deploy_llm-guard:latest 2>/dev/null || true

print_step "Building LLM-Guard Image"
# Build the LLM-Guard image
echo -e "${YELLOW}Rebuilding LLM-Guard image with updated Dockerfile...${NC}"
$DOCKER_COMPOSE -f "${COMPOSE_FILE}" build --no-cache llm-guard

echo -e "${GREEN}Build completed!${NC}"

print_step "Starting Containers Sequentially"
# Start the vector-db first (as it's a dependency)
echo -e "${YELLOW}Starting vector-db container...${NC}"
$DOCKER_COMPOSE -f "${COMPOSE_FILE}" up -d vector-db
if ! check_container_health "vector-db" "${MAX_RETRIES}" "${RETRY_INTERVAL}"; then
    echo -e "${RED}Failed to start vector-db. Aborting.${NC}"
    exit 1
fi

# Now start the llm-guard container
echo -e "${YELLOW}Starting llm-guard container...${NC}"
$DOCKER_COMPOSE -f "${COMPOSE_FILE}" up -d llm-guard
if ! check_container_health "llm-guard" "${MAX_RETRIES}" "${RETRY_INTERVAL}"; then
    echo -e "${RED}Failed to start llm-guard. Checking for specific issues...${NC}"

    # Check for common issues
    echo -e "${YELLOW}Inspecting container configuration...${NC}"
    docker inspect llm-guard | grep -E 'Mounts|Volumes|Error'

    echo -e "${YELLOW}Checking if models directory is properly mounted...${NC}"
    docker exec -it llm-guard ls -la /app/models 2>/dev/null || echo "Cannot execute command in container"

    echo -e "${RED}LLM-Guard container failed to start. Please check the logs above for details.${NC}"
    exit 1
fi

# Start remaining services
echo -e "${YELLOW}Starting remaining services...${NC}"
$DOCKER_COMPOSE -f "${COMPOSE_FILE}" up -d

print_step "Verification"
# Check status of all services
echo -e "${YELLOW}Checking status of all containers:${NC}"
$DOCKER_COMPOSE -f "${COMPOSE_FILE}" ps

echo -e "\n${GREEN}LLM-Guard has been rebuilt and containers started.${NC}"
echo -e "${YELLOW}To check container logs:${NC} docker logs llm-guard"
echo -e "${YELLOW}To check container status:${NC} docker ps | grep llm-guard"

# Make the script executable
chmod +x "$0"
