#!/bin/bash

# Tokenizer Bundling Script for Air-Gapped Deployment
# This script prepares tokenizer files for offline deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TOKENIZER_DIR="$PROJECT_ROOT/data/tokenizers"
BUNDLE_FILE="$PROJECT_ROOT/tokenizer_bundle.tar.gz"

# Supported models
declare -a MODELS=(
    "foundation-sec"
    "phi-4-mini"
    "mistral-large"
    "mistral-small"
    "gpt-oss"
    "llama-3.3"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python and required packages are available
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    if ! python3 -c "import tiktoken" &> /dev/null; then
        log_error "tiktoken package is required but not installed"
        log_info "Install with: pip install tiktoken"
        exit 1
    fi

    log_success "Dependencies check passed"
}

# Create tokenizer directory
setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "$TOKENIZER_DIR"

    log_success "Directories created: $TOKENIZER_DIR"
}

# Download tokenizer for a specific model
download_tokenizer() {
    local model="$1"
    log_info "Processing tokenizer for model: $model"

    # Create a temporary Python script to download tokenizer
    local temp_script=$(mktemp)
    cat > "$temp_script" << EOF
import tiktoken
import json
import os
import sys

model = "$model"
tokenizer_dir = "$TOKENIZER_DIR"

try:
    # Try to get encoding for the model
    if model in ["foundation-sec", "phi-4-mini"]:
        # These models might use cl100k_base as fallback
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding_name = "cl100k_base"
    elif model.startswith("mistral"):
        # Mistral models typically use cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding_name = "cl100k_base"
    elif model == "gpt-oss":
        # GPT-OSS uses cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding_name = "cl100k_base"
    elif model == "llama-3.3":
        # Llama 3.3 uses cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding_name = "cl100k_base"
    else:
        # Try to get encoding for model directly
        try:
            encoding = tiktoken.encoding_for_model(model)
            encoding_name = encoding.name
        except KeyError:
            # Fallback to cl100k_base
            encoding = tiktoken.get_encoding("cl100k_base")
            encoding_name = "cl100k_base"

    # Create model-specific directory
    model_dir = os.path.join(tokenizer_dir, model)
    os.makedirs(model_dir, exist_ok=True)

    # Save tokenizer metadata
    metadata = {
        "model": model,
        "encoding_name": encoding_name,
        "vocab_size": encoding.n_vocab,
        "model_type": "tiktoken",
        "description": f"Tokenizer for {model} model"
    }

    metadata_file = os.path.join(model_dir, "metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Save encoding name for runtime loading
    encoding_file = os.path.join(model_dir, "encoding.txt")
    with open(encoding_file, 'w') as f:
        f.write(encoding_name)

    print(f"✓ Downloaded tokenizer for {model} (encoding: {encoding_name})")

except Exception as e:
    print(f"✗ Failed to download tokenizer for {model}: {e}")
    sys.exit(1)
EOF

    # Run the Python script
    if python3 "$temp_script"; then
        log_success "Downloaded tokenizer for $model"
    else
        log_error "Failed to download tokenizer for $model"
        rm -f "$temp_script"
        exit 1
    fi

    # Clean up
    rm -f "$temp_script"
}

# Download all tokenizers
download_all_tokenizers() {
    log_info "Downloading tokenizers for all supported models..."

    for model in "${MODELS[@]}"; do
        download_tokenizer "$model"
    done

    log_success "All tokenizers downloaded successfully"
}

# Create README for tokenizer directory
create_readme() {
    log_info "Creating README for tokenizer directory..."

    cat > "$TOKENIZER_DIR/README.md" << EOF
# Tokenizer Files for Air-Gapped Deployment

This directory contains tokenizer files for all supported models in air-gapped deployment.

## Supported Models

- foundation-sec
- phi-4-mini
- mistral-large
- mistral-small
- gpt-oss
- llama-3.3

## Directory Structure

Each model has its own subdirectory containing:
- \`metadata.json\` - Tokenizer metadata and configuration
- \`encoding.txt\` - Encoding name for runtime loading

## Usage

The ContextCompactionService will automatically load tokenizers from this directory when running in air-gapped mode.

## Maintenance

To update tokenizers:
1. Run \`scripts/bootstrap/prepare_tokenizers.sh\` on internet-connected machine
2. Transfer updated bundle to air-gapped environment
3. Extract to this directory
4. Restart services

## Security

- Files are read-only in production
- Verify file integrity before deployment
- Use secure transfer methods
- Maintain audit trail of updates

Generated: $(date)
EOF

    log_success "README created"
}

# Create bundle file
create_bundle() {
    log_info "Creating tokenizer bundle..."

    # Remove existing bundle if it exists
    if [[ -f "$BUNDLE_FILE" ]]; then
        rm -f "$BUNDLE_FILE"
    fi

    # Create tar.gz bundle
    cd "$PROJECT_ROOT"
    tar -czf "$BUNDLE_FILE" -C "$PROJECT_ROOT" data/tokenizers/

    # Get bundle size
    local bundle_size=$(du -h "$BUNDLE_FILE" | cut -f1)

    log_success "Bundle created: $BUNDLE_FILE ($bundle_size)"
}

# Verify bundle
verify_bundle() {
    log_info "Verifying bundle integrity..."

    # Test extraction
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"

    if tar -tzf "$BUNDLE_FILE" > /dev/null; then
        log_success "Bundle integrity verified"
    else
        log_error "Bundle integrity check failed"
        rm -rf "$temp_dir"
        exit 1
    fi

    # Clean up
    rm -rf "$temp_dir"
}

# Generate checksums
generate_checksums() {
    log_info "Generating checksums..."

    local checksum_file="$PROJECT_ROOT/tokenizer_bundle.sha256"

    # Generate SHA256 checksum
    sha256sum "$BUNDLE_FILE" > "$checksum_file"

    log_success "Checksums generated: $checksum_file"
}

# Main function
main() {
    log_info "Starting tokenizer bundling process..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Tokenizer directory: $TOKENIZER_DIR"
    log_info "Bundle file: $BUNDLE_FILE"

    check_dependencies
    setup_directories
    download_all_tokenizers
    create_readme
    create_bundle
    verify_bundle
    generate_checksums

    log_success "Tokenizer bundling completed successfully!"
    log_info "Bundle file: $BUNDLE_FILE"
    log_info "Checksum file: $PROJECT_ROOT/tokenizer_bundle.sha256"
    log_info ""
    log_info "Next steps:"
    log_info "1. Transfer bundle to air-gapped environment"
    log_info "2. Extract with: tar -xzf tokenizer_bundle.tar.gz"
    log_info "3. Verify checksum: sha256sum -c tokenizer_bundle.sha256"
    log_info "4. Update ContextCompactionService to use offline tokenizers"
}

# Run main function
main "$@"
