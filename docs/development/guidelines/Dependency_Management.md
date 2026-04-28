# Dependency Management Guide

This guide documents the dependency management strategy and upgrade process for AI Operations Platform.

## Overview

The project uses a phased approach to dependency upgrades to ensure system stability while keeping packages up-to-date for security and performance improvements.

## Current Dependency Versions (Post Phase E-I Upgrades)

### Security Packages (Phase E)

- **bcrypt**: 4.3.0 (target: 4.2.0+) ✅
- **cryptography**: 44.0.3 (target: 43.0.3+) ✅
- **python-jose**: 3.5.0 (target: 3.3.0+) ✅

### ML Packages (Phase F)

- **datasets**: 3.6.0 (target: 2.20.0+) ✅
- **spacy**: 3.7.5 (target: 3.7.4+) ✅
- **transformers**: 4.53.x (orchestrator, embedding, corpus_svc, inference-gateway); 4.51.3 (llm_guard_svc only, llm-guard pin) ✅

### Development Tools (Phase G)

- **mypy**: 1.15.0 (target: 1.13.0+) ✅
- **pytest**: 8.4.0 (target: 8.3.4+) ✅
- **black**: 25.1.0 (target: 24.10.0+) ✅
- **ruff**: 0.11.12 (target: 0.8.4+) ✅

### Document Processing (Phase H)

- **pdfplumber**: 0.11.x (PDF text and table extraction; replaces PyMuPDF as the primary PDF parser)
- **PyPDF2**: 3.0.x (PDF metadata extraction)
- **pytesseract**: 0.3.x (optional OCR fallback)
- **beautifulsoup4**: 4.13.3 (target: 4.12.3+) ✅
- **lxml**: 5.4.0 (target: 5.3.0+) ✅

### Database Drivers (Phase I)

- **psycopg**: 3.2.10 (target: 3.2.3+) ✅
- **qdrant-client**: 1.14.2 (target: 1.9.1+) ✅

## Upgrade Process

### Phase-Based Approach

Dependencies are upgraded in phases to minimize risk and ensure system stability:

1. **Phase E**: Security upgrades (bcrypt, cryptography, python-jose)
2. **Phase F**: Safe ML upgrades (datasets, spacy) - excludes transformers
3. **Phase G**: Development tools (mypy, pytest, black, ruff)
4. **Phase H**: Document processing (pdfplumber, PyPDF2, beautifulsoup4, lxml)
5. **Phase I**: Database drivers (psycopg, qdrant-client)

### Upgrade Steps

For each phase:

1. **Backup**: Create requirements backup and virtual environment backup
2. **Update**: Modify requirements.txt files with new version constraints
3. **Install**: Run `pip install -r requirements-all.txt` for a single env, or use the wheelhouse (two-pass build provides transformers 4.53.x for most services and 4.51.3 for llm_guard_svc only).
4. **Test**: Verify package imports and basic functionality
5. **Container**: Rebuild affected containers
6. **Verify**: Ensure all services remain healthy

### Wheelhouse build (two transformers versions)

The wheelhouse is built in two passes so that most services get secure transformers 4.53.x while llm_guard_svc keeps its pinned 4.51.3:

1. **Pass 1**: `requirements-all-no-llm-guard.txt` with `constraints.txt` → wheels for orchestrator, embedding, corpus_svc, inference-gateway, shared (transformers 4.53.x).
2. **Pass 2**: `src/llm_guard_svc/requirements.txt` → wheels for llm_guard_svc (transformers 4.51.3).

Both passes write into the same wheelhouse. Each container installs with its own `requirements.txt`, so pip picks the correct transformers version per service.

### Container Rebuild Process

After dependency upgrades:

```bash
# Export environment variables
export $(grep -v '^#' config/env/.env | xargs)

# Rebuild containers without cache
docker-compose -f deploy/docker-compose.yml build --no-cache

# Restart services
docker-compose -f deploy/docker-compose.yml up -d

# Verify health
docker-compose -f deploy/docker-compose.yml ps
```

## Important Constraints

### LLM-Guard Compatibility

The `transformers` package version is constrained by the `llm-guard` dependency:

- **llm-guard**: Requires specific transformers version
- **Constraint**: Do not upgrade transformers independently
- **Solution**: Wait for llm-guard updates that support newer transformers versions

### Spacy Models

When upgrading spacy, ensure model compatibility:

```bash
# Check model compatibility
python -m spacy validate

# Download latest compatible models
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

## Troubleshooting

### Import Errors After Upgrades

If containers fail with import errors:

1. **Check imports**: Verify the package is correctly imported
2. **Rebuild without cache**: Use `--no-cache` flag to ensure fresh build
3. **Check dependencies**: Ensure all transitive dependencies are compatible

### Example Fix: BadRequestError Import

```python
# Before (causing import error)
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    OpenAI,
    RateLimitError,
)

# After (working)
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,  # Added missing import
    OpenAI,
    RateLimitError,
)

# Export for other modules
__all__ = ["LLMClient", "BadRequestError"]
```

## Future Upgrades

### Planned Phases

- **Phase J**: Additional security packages (if needed)
- **Phase K**: Performance optimization packages
- **Phase L**: Monitoring and observability updates

### Monitoring

- Monitor security advisories for critical packages
- Track llm-guard releases for transformers compatibility
- Regular dependency audits using `pip-audit`

## Best Practices

1. **Test in isolation**: Test each phase independently
2. **Backup before upgrades**: Always create backups before major changes
3. **Incremental updates**: Use `>=` constraints rather than exact versions
4. **Container validation**: Always verify container health after upgrades
5. **Documentation**: Update this guide after each upgrade phase

## Files Modified in Phase E-I

### Requirements Files

- `src/orchestrator/requirements.txt`
- `src/corpus_svc/requirements.txt`
- `src/embedding/requirements.txt`

### Code Changes

- `src/orchestrator/app/orchestrator/llm_client.py` - Added BadRequestError import
- `ops/bootstrap/build_wheelhouse.sh` - Updated spacy version

### Documentation

- `docs/development/Dependency_Management.md` - This file
- `PHASE_E_I_UPGRADE_INSTRUCTIONS.md` - Upgrade instructions

## Verification Commands

```bash
# Check package versions
pip list | grep -E "(bcrypt|cryptography|python-jose|datasets|spacy|mypy|pytest|black|ruff|pdfplumber|PyPDF2|beautifulsoup4|lxml|psycopg|qdrant-client)"

# Test imports
python -c "
from jose import jwt
import bcrypt
from cryptography.fernet import Fernet
import datasets
import spacy
import mypy
import pytest
import black
import ruff
import pdfplumber
import PyPDF2
from bs4 import BeautifulSoup
import lxml
import psycopg
import qdrant_client
print('All imports successful')
"

# Verify container health
docker-compose -f deploy/docker-compose.yml ps
```
