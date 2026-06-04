# Phase E-I Dependency Upgrade Instructions

## Overview

This document provides step-by-step instructions for implementing the remaining dependency upgrades (Phases E-I) for the AI Operations Platform application. These upgrades focus on security, ML libraries, development tools, document processing, and database drivers.

## Prerequisites

- ✅ Phases A-D completed and committed (commit hash: 2eb2059)
- ✅ All services running successfully
- ✅ Virtual environment active
- ✅ Docker containers operational

## Phase E: Security and Authentication Upgrades

### Target Packages

- `bcrypt`: 4.0.1 → 4.2.0
- `cryptography`: 41.0.7 → 43.0.3
- `python-jose`: 3.3.0 → 3.3.0 (latest)

### Implementation Steps

1. **Backup Current State**

   ```bash
   pip freeze > requirements_backup_phase_e_$(date +%Y%m%d_%H%M%S).txt
   cp -r venv venv_backup_phase_e_$(date +%Y%m%d_%H%M%S)
   ```

2. **Update Requirements Files**

   ```bash
   # Update backend requirements
   sed -i '' 's/bcrypt==4.0.1/bcrypt>=4.2.0/' src/orchestrator/requirements.txt
   sed -i '' 's/cryptography==41.0.7/cryptography>=43.0.3/' src/orchestrator/requirements.txt

   # Update other service requirements if they contain these packages
   grep -r "bcrypt\|cryptography\|python-jose" src/*/requirements.txt
   ```

3. **Install Upgrades**

   ```bash
   pip install -r requirements-all.txt
   ```

4. **Test Security Components**

   ```bash
   # Test JWT functionality
   python -c "from jose import jwt; print('JWT import successful')"

   # Test bcrypt functionality
   python -c "import bcrypt; print('bcrypt import successful')"

   # Test cryptography
   python -c "from cryptography.fernet import Fernet; print('cryptography import successful')"
   ```

5. **Run Authentication Tests**

   ```bash
   # Test JWT token generation and validation
   python ops/testing/test_jwt_flow.py
   ```

## Phase F: Safe ML Upgrades

### Target Packages

- `datasets`: 2.14.6 → 2.20.0
- `spacy`: 3.7.2 → 3.7.4

### ⚠️ Important Constraint

- **NOTE**: `transformers` is split: `llm_guard_svc` uses `>=5.0.0,<5.2.0` (gliner ceiling); other services use `>=5.9.0` via `constraints.txt`. Do not unify them.

### Implementation Steps

1. **Update Requirements Files**

   ```bash
   # Update embedding service requirements
   sed -i '' 's/datasets==2.14.6/datasets>=2.20.0/' src/embedding/requirements.txt
   sed -i '' 's/spacy==3.7.2/spacy>=3.7.4/' src/embedding/requirements.txt
   ```

2. **Install Upgrades**

   ```bash
   pip install -r requirements-all.txt
   ```

3. **Test ML Components**

   ```bash
   # Test datasets functionality
   python -c "import datasets; print('datasets import successful')"

   # Test spacy functionality
   python -c "import spacy; print('spacy import successful')"
   ```

4. **Verify Embedding Compatibility**

   ```bash
   # Run embedding service tests
   python ops/testing/test_embedding_service_isolation.py
   ```

## Phase G: Development Tool Upgrades

### Target Packages

- `mypy`: 1.7.1 → 1.13.0
- `pytest`: 7.4.3 → 8.3.4
- `black`: 23.11.0 → 24.10.0
- `ruff`: 0.1.6 → 0.8.4

### Implementation Steps

1. **Update Development Requirements**

   ```bash
   # Update requirements-dev-all.txt
   sed -i '' 's/mypy==1.7.1/mypy>=1.13.0/' requirements-dev-all.txt
   sed -i '' 's/pytest==7.4.3/pytest>=8.3.4/' requirements-dev-all.txt
   sed -i '' 's/black==23.11.0/black>=24.10.0/' requirements-dev-all.txt
   sed -i '' 's/ruff==0.1.6/ruff>=0.8.4/' requirements-dev-all.txt
   ```

2. **Install Upgrades**

   ```bash
   pip install -r requirements-dev-all.txt
   ```

3. **Test Development Tools**

   ```bash
   # Test mypy
   mypy --version

   # Test pytest
   pytest --version

   # Test black
   black --version

   # Test ruff
   ruff --version
   ```

4. **Run Code Quality Checks**

   ```bash
   # Run linting
   ruff check src/

   # Run formatting check
   black --check src/

   # Run type checking
   mypy src/
   ```

## Phase H: Document Processing Upgrades

### Target Packages

- `pdfplumber`: 0.11.x (primary PDF parser; replaced PyMuPDF, which was removed for license compatibility — AGPL-3.0)
- `PyPDF2`: 3.0.x (PDF metadata extraction)
- `beautifulsoup4`: 4.12.2 → 4.12.3
- `lxml`: 4.9.3 → 5.3.0

### Implementation Steps

1. **Update Requirements Files**

   ```bash
   # Update corpus_svc requirements
   sed -i '' 's/beautifulsoup4==4.12.2/beautifulsoup4>=4.12.3/' src/corpus_svc/requirements.txt
   sed -i '' 's/lxml==4.9.3/lxml>=5.3.0/' src/corpus_svc/requirements.txt
   ```

2. **Install Upgrades**

   ```bash
   pip install -r requirements-all.txt
   ```

3. **Test Document Processing**

   ```bash
   # Test PDF processing
   python -c "import pdfplumber; print('pdfplumber import successful')"
   python -c "import PyPDF2; print('PyPDF2 import successful')"

   # Test HTML parsing
   python -c "from bs4 import BeautifulSoup; print('beautifulsoup4 import successful')"

   # Test XML processing
   python -c "import lxml; print('lxml import successful')"
   ```

4. **Run Document Processing Tests**

   ```bash
   # Test PDF metadata extraction
   python ops/extract_pdf_metadata.py
   ```

## Phase I: Database Driver Upgrades

### Target Packages

- `psycopg`: 3.1.13 → 3.2.3
- `qdrant-client`: 1.7.3 → 1.9.1

### Implementation Steps

1. **Update Requirements Files**

   ```bash
   # Update backend requirements
   sed -i '' 's/psycopg==3.1.13/psycopg>=3.2.3/' src/orchestrator/requirements.txt

   # Update retrieval service requirements
   sed -i '' 's/qdrant-client==1.7.3/qdrant-client>=1.9.1/' src/corpus_svc/requirements.txt
   ```

2. **Install Upgrades**

   ```bash
   pip install -r requirements-all.txt
   ```

3. **Test Database Components**

   ```bash
   # Test PostgreSQL connectivity
   python -c "import psycopg; print('psycopg import successful')"

   # Test Qdrant connectivity
   python -c "import qdrant_client; print('qdrant-client import successful')"
   ```

4. **Run Database Tests**

   ```bash
   # Test database connections
   python ops/check_db_objects.py
   ```

## Comprehensive Testing Strategy

### 1. Individual Service Tests

```bash
# Test each service individually
python ops/testing/test_embedding_service_isolation.py
python ops/testing/test_retrieval_endpoints.py
python ops/testing/test_background_processing_systematic.py
```

### 2. Integration Tests

```bash
# Run full pipeline test
python ops/demonstrate_enhanced_pipeline_fixed.py --username testuser --password password
```

### 3. Performance Benchmarking

```bash
# Measure performance improvements
time python ops/demonstrate_enhanced_pipeline_fixed.py --username testuser --password password
```

## Container Rebuild Process

### 1. Rebuild Wheelhouse

```bash
./ops/bootstrap/build_wheelhouse.sh
```

### 2. Rebuild Containers

```bash
docker-compose -f deploy/docker-compose.yml down
docker-compose -f deploy/docker-compose.yml build --no-cache
docker-compose -f deploy/docker-compose.yml up -d
```

### 3. Verify Container Health

```bash
docker-compose -f deploy/docker-compose.yml ps
docker-compose -f deploy/docker-compose.yml logs --tail=50
```

## Rollback Strategy

### If Issues Arise

1. **Stop containers**: `docker-compose -f deploy/docker-compose.yml down`
2. **Restore backup**: `rm -rf venv && mv venv_backup_phase_e_* venv`
3. **Restore requirements**: `cp requirements_backup_phase_e_* requirements-all.txt`
4. **Rebuild**: Follow container rebuild process

## Commit Strategy

### After Each Phase

```bash
git add .
git commit -m "feat: Implement Phase [X] dependency upgrades

- Upgraded [package names and versions]
- Verified compatibility with existing functionality
- All tests passing
- Performance benchmarks maintained"
```

### Final Commit

```bash
git add .
git commit -m "feat: Complete Phases E-I dependency upgrades

## Phase E: Security upgrades (bcrypt, cryptography, python-jose)
## Phase F: ML upgrades (datasets, spacy) - transformers version split maintained
## Phase G: Development tools (mypy, pytest, black, ruff)
## Phase H: Document processing (pdfplumber, PyPDF2, beautifulsoup4, lxml)
## Phase I: Database drivers (psycopg, qdrant-client)

- All upgrades tested and verified
- Full pipeline functionality maintained
- Performance improvements documented
- Security vulnerabilities addressed"
```

## Success Criteria

### ✅ Phase E Complete When

- All security packages upgraded
- JWT functionality verified
- Authentication tests passing

### ✅ Phase F Complete When

- ML packages upgraded (excluding transformers)
- Embedding compatibility verified
- No llm-guard conflicts

### ✅ Phase G Complete When

- Development tools upgraded
- Code quality checks passing
- Linting and formatting working

### ✅ Phase H Complete When

- Document processing packages upgraded
- PDF extraction functionality verified
- HTML/XML parsing working

### ✅ Phase I Complete When

- Database drivers upgraded
- PostgreSQL connectivity verified
- Qdrant functionality confirmed

### ✅ All Phases Complete When

- Full pipeline test passing
- Performance benchmarks maintained or improved
- All services healthy
- No breaking changes introduced

## Notes

- **Transformers Split**: `llm_guard_svc` uses `>=5.0.0,<5.2.0` (gliner ceiling); all other services use `>=5.9.0`. Do not unify.
- **Testing Priority**: Run tests after each phase before proceeding
- **Backup Strategy**: Create backups before each phase
- **Monitoring**: Watch container logs during upgrades
- **Performance**: Document any performance changes

## Troubleshooting

### Common Issues

1. **Import Errors**: Check virtual environment activation
2. **Container Issues**: Verify Docker networking (host.docker.internal)
3. **Dependency Conflicts**: Use constraints.txt for pinning
4. **Performance Degradation**: Rollback and investigate

### Support Commands

```bash
# Check package versions
pip list | grep -E "(bcrypt|cryptography|datasets|spacy|mypy|pytest|black|ruff|pdfplumber|PyPDF2|beautifulsoup4|lxml|psycopg|qdrant-client)"

# Verify imports
python -c "import [package_name]; print('[package_name] version:', [package_name].__version__)"

# Check container logs
docker-compose -f deploy/docker-compose.yml logs [service_name]
```

---

**Ready to proceed with Phase E-I upgrades!** 🚀
