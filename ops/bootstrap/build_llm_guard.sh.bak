#!/bin/bash
set -eo pipefail

# Script to build LLM-Guard image with robust model handling
# Uses simple git clone for model downloading rather than complex Python setup

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MODEL_CACHE_DIR="${PROJECT_ROOT}/data/llm-guard-models"
IMAGE_NAME="llm-guard-with-models:latest"  # This must match podman-compose.yml
FORCE_REBUILD=false
PRUNE_BEFORE_BUILD=false

# Define required models
REQUIRED_MODELS=(
  "Isotonic/deberta-v3-base_finetuned_ai4privacy_v2"
  "madhurjindal/autonlp-Gibberish-Detector-492513457"
  "protectai/xlm-roberta-base-language-detection-onnx"
  "protectai/deberta-v3-base-prompt-injection-v2"
)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --force-rebuild)
      FORCE_REBUILD=true
      shift
      ;;
    --prune)
      PRUNE_BEFORE_BUILD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${YELLOW}Building LLM-Guard with pre-cached models${NC}"

# Create model cache directory if it doesn't exist
mkdir -p "$MODEL_CACHE_DIR"
echo -e "Model cache directory: ${GREEN}$MODEL_CACHE_DIR${NC}"

# Function to download model using git clone
download_model() {
    model_name="$1"
    output_dir="$2"

    # Extract repo name from model path
    repo_name=$(echo "$model_name" | awk -F/ '{print $NF}')

    # Check if model already exists
    if [ -d "$output_dir/$repo_name" ] && [ -n "$(ls -A "$output_dir/$repo_name" 2>/dev/null)" ]; then
        echo -e "${GREEN}Model $model_name already exists in $output_dir/$repo_name${NC}"
        return 0
    fi

    # Clone the repository with LFS support
    echo -e "${YELLOW}Downloading model: $model_name${NC}"
    cd "$output_dir"

    # Ensure git-lfs is installed and initialized
    if ! command -v git-lfs &> /dev/null; then
        echo -e "${YELLOW}git-lfs not found. Large files may not download correctly.${NC}"
        echo -e "${YELLOW}Consider installing git-lfs with: brew install git-lfs (macOS) or apt-get install git-lfs (Ubuntu)${NC}"
    else
        git lfs install
    fi

    # Perform the clone operation
    if git clone "https://huggingface.co/${model_name}" 2>/dev/null; then
        echo -e "${GREEN}Successfully downloaded: $model_name${NC}"
        return 0
    else
        echo -e "${RED}Failed to download: $model_name${NC}"
        return 1
    fi
}

# Check if models need to be downloaded
download_needed=false
missing_models=()

for model in "${REQUIRED_MODELS[@]}"; do
    # Extract repo name from model path
    repo_name=$(echo "$model" | awk -F/ '{print $NF}')

    if [ ! -d "$MODEL_CACHE_DIR/$repo_name" ] || [ -z "$(ls -A "$MODEL_CACHE_DIR/$repo_name" 2>/dev/null)" ]; then
        download_needed=true
        missing_models+=("$model")
    fi
done

# Download missing models if needed
if [ "$download_needed" = true ]; then
    echo -e "${YELLOW}Some models are missing and need to be downloaded...${NC}"

    # Download each missing model
    for model in "${missing_models[@]}"; do
        if ! download_model "$model" "$MODEL_CACHE_DIR"; then
            echo -e "${RED}Warning: Failed to download $model. Build may fail if this model is required.${NC}"
        fi
    done
else
    echo -e "${GREEN}All required models found in cache directory${NC}"
fi

# Change to project root for podman operations
cd "$PROJECT_ROOT"

# Prune podman resources if requested
if [ "$PRUNE_BEFORE_BUILD" = true ]; then
    echo -e "${YELLOW}Pruning podman resources before build...${NC}"

    # Stop the container if it's running
    podman stop llm-guard 2>/dev/null || true

    # Remove existing containers
    podman rm llm-guard 2>/dev/null || true

    # Remove existing images
    podman rmi "$IMAGE_NAME" 2>/dev/null || true
    podman rmi llm-guard:latest 2>/dev/null || true

    echo -e "${GREEN}podman pruning complete${NC}"
fi

# Always remove existing image to force rebuild
echo -e "${YELLOW}Removing any existing images...${NC}"
podman rmi "$IMAGE_NAME" 2>/dev/null || true

# Build podman image
echo -e "${YELLOW}Building podman image...${NC}"

# Force rebuild if requested
BUILD_ARGS=""
if [ "$FORCE_REBUILD" = true ]; then
    echo -e "${YELLOW}Forcing complete rebuild with --no-cache${NC}"
    BUILD_ARGS="--no-cache"
fi

# Build the image directly with podman
echo -e "${YELLOW}Building directly from Dockerfile...${NC}"
echo -e "${YELLOW}Models will be mounted from: $MODEL_CACHE_DIR${NC}"

# Add build context arguments
podman_BUILDKIT=1 podman build $BUILD_ARGS \
  --progress=plain \
  -t "$IMAGE_NAME" \
  -f src/llm-guard/Dockerfile \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  src/llm-guard/

# List images for debugging
echo -e "${YELLOW}Listing all podman images:${NC}"
podman images | grep -E 'llm-guard|none'

# Verify image exists
if podman image inspect "$IMAGE_NAME" &>/dev/null; then
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${YELLOW}You can now run the LLM-Guard service with:${NC}"
    echo -e "  podman compose -f deploy/podman-compose.yml up llm-guard"
    echo -e "  OR"
    echo -e "  podman compose -f deploy/podman-compose.yml up"
else
    echo -e "${RED}Build failed: Image $IMAGE_NAME not found${NC}"
    echo -e "${RED}Check for errors in the build process${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Script options:${NC}"
echo -e "  --force-rebuild      Force podman to rebuild with --no-cache (ignores all layers)"
echo -e "  --prune              Remove existing containers and images before building"
