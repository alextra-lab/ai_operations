# Dependency Management Guide

This guide documents the dependency management strategy and upgrade process for AI Operations Platform.

## Overview

The project uses a phased approach to dependency upgrades to ensure system stability while keeping packages up-to-date for security and performance improvements.

## Current Dependency Versions (Post security remediation, 2026-05-30)

For authoritative current versions, read the service `requirements.txt` files directly —
this table is a snapshot and will drift. Notable pins:

| Package | Version | Notes |
|---|---|---|
| `transformers` | 4.53.x / 4.51.3 | Most services use 4.53.x; llm_guard_svc pinned to 4.51.3 (llm-guard compat) |
| `uvicorn` | 0.48.0 | All services |
| `opentelemetry-sdk` | 1.42.1 | All services except llm_guard_svc |
| `opentelemetry-instrumentation-fastapi` | 0.63b1 | All services |
| `fastapi` | ≥0.136.3 | inference-gateway |
| `pydantic` | ≥2.13.4 | inference-gateway |
| `psycopg` | ≥3.3.4 | corpus_svc |
| `sqlalchemy` | ≥2.0.50 | embedding |
| `openai` | ≥2.38.0 | orchestrator |
| `torch` | ≥2.12.0 | llm_guard_svc |
| Node base image | 26-alpine | frontend-angular Dockerfile |
| `ng2-charts` | ^10.0.0 | frontend prod |

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

## Dependabot Strategy

### Why only the root pip entry

`.github/dependabot.yml` has **one pip entry** pointing at `directory: "/"` with a `pip-root`
group. Do not add per-service pip entries (e.g. `directory: "/src/orchestrator"`).

**Why:** `requirements-all-no-llm-guard.txt` and `requirements-all.txt` use `-r` includes to
pull in every service's `requirements.txt`. When Dependabot scans the root, it follows those
includes and sees all packages across all services. The `pip-root` group then bumps the same
package in every service that uses it — in a single PR that passes CI.

Per-service entries create individual PRs that update only one service at a time. Since the same
package (e.g. `opentelemetry-sdk`) is pinned to a specific version in multiple services, a
per-service PR that bumps it in one service leaves the other services on the old pin. The CI
aggregator install then sees two conflicting version requirements and fails.

### Known deferred items (as of 2026-05-30)

- **`typescript` ~6.0.3** in the npm-dev group: `@angular-devkit/build-angular` requires
  `typescript >=5.9 <6.0`. Dependabot will re-open once Angular build tooling adds TypeScript 6
  support. Do not force-merge with `--legacy-peer-deps`.
- **Python 3.14 base images**: Docker PRs for all 5 services deferred pending verification that
  the full dependency set builds on 3.14.

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
