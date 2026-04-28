# Database Seeding Consolidation Analysis

**Date:** 2025-10-26
**Status:** 🔴 **URGENT - Duplicate and conflicting seeding systems**

---

## Executive Summary

We have **TWO COMPETING SEEDING SYSTEMS** that create conflicts and confusion:

1. **SQL Seed Files** (NEW, recommended): `ops/database/seed/*.sql`
2. **Python Seed Scripts** (LEGACY): `ops/bootstrap/seed_*.py`

**Recommendation:** **Deprecate Python seed scripts** and use SQL-only approach.

---

## Current State Analysis

### SQL Seed Files (`ops/database/seed/`)

✅ **Recently updated with complete functionality** (2025-10-26)

| File | Purpose | Status |
|------|---------|--------|
| `001_seed_users.sql` | Users (admin, analyst, testuser) | ✅ Complete |
| `002_seed_intents.sql` | Intent system | ✅ Complete |
| `003_seed_use_cases.sql` | 5 SOC use cases with input_fields | ✅ **Just updated today** |
| `004_seed_pricing.sql` | 15 pricing tiers | ✅ Complete |
| `005_seed_models.sql` | Model registry | ✅ Complete |

### Python Seed Scripts (`ops/bootstrap/`)

⚠️ **Duplicates and conflicts with SQL**

| File | Purpose | Conflicts With | Status |
|------|---------|----------------|--------|
| `seed_users.py` | Creates users via SQLAlchemy | `001_seed_users.sql` | ⚠️ DUPLICATE |
| `seed_use_cases.py` | Seeds use cases with different definitions | `003_seed_use_cases.sql` | ❌ **CONFLICT** |
| `seed_templates.py` | Seeds prompt templates from JSON files | None | ⚠️ **Orphaned** |
| `seed_phase1.py` | Meta-script for phase 1 | Multiple | ⚠️ LEGACY |

---

## Detailed Comparison

### 1. User Seeding - DUPLICATE

**SQL Version** (`001_seed_users.sql`):
```sql
INSERT INTO users (username, hashed_password, role, ...)
VALUES ('admin', '$2b$12$...', 'admin', ...);
```

**Python Version** (`seed_users.py`):
```python
user = User(
    username='admin',
    hashed_password=get_password_hash('admin123'),
    role='admin',
    ...
)
```

**Issue:** Both create the same users. Running both causes duplicates/conflicts.

### 2. Use Case Seeding - **CRITICAL CONFLICT**

**SQL Version** (`003_seed_use_cases.sql`) - **Updated today**:
- 5 use cases: threat-analysis-basic, log-investigation, ioc-lookup, policy-review, incident-summary
- **Includes input_fields** (just added today)
- Uses config from production requirements

**Python Version** (`seed_use_cases.py`) - **DIFFERENT USE CASES**:
- Different use_case_ids: threat-intelligence-query, log-analysis-deep-dive, etc.
- Different configurations
- More complex validation logic

**Issue:** These create DIFFERENT use cases. User doesn't know which ones are correct!

### 3. Prompt Templates - **ORPHANED**

**Python Version ONLY** (`seed_templates.py`):
- Reads from `src/orchestrator/app/config/templates/*.json`
- Seeds `prompt_templates` table

**Issue:** No SQL equivalent. Templates may not exist.

---

## Problems with Python Seed Scripts

### 1. **Dependency Hell**
```python
from src.backend.app.db.models import UseCase
from src.shared.auth.models import User
```
- Requires entire Python codebase
- Requires SQLAlchemy models
- Requires bcrypt, psycopg, etc.
- Can't run in air-gapped deployment until Python environment is set up

### 2. **Fragility**
- Breaks if model definitions change
- Breaks if import paths change
- Breaks if dependencies are missing

### 3. **Less Portable**
- SQL works everywhere PostgreSQL exists
- Python requires specific environment

### 4. **Harder to Audit**
- SQL is declarative and clear
- Python has logic scattered across functions

### 5. **Version Confusion**
- User doesn't know which to run
- Documentation references both
- Different data in dev vs prod

---

## Recommendations

### ✅ **Option 1: SQL-Only Approach (RECOMMENDED)**

**Action Plan:**

1. **Keep:** `ops/database/seed/*.sql` (all 5 files)
2. **Deprecate:** All `ops/bootstrap/seed_*.py` scripts
3. **Move:** `ops/bootstrap/seed_*.py` → `docs/archive/bootstrap-scripts/`
4. **Document:** Clear instructions to use SQL only

**Pros:**
- Single source of truth
- No Python dependencies
- Portable and simple
- Easy to audit
- Works in any environment

**Cons:**
- Lose validation logic from Python scripts
- Can't easily compute password hashes (but we can pre-generate them)

### ⚠️ **Option 2: Python-Only Approach**

**Action Plan:**

1. **Delete:** `ops/database/seed/*.sql`
2. **Keep:** `ops/bootstrap/seed_*.py`
3. **Update:** Python scripts to match SQL data
4. **Document:** Python-first approach

**Pros:**
- Validation logic
- Type safety
- Can use application code

**Cons:**
- Python dependencies
- Less portable
- More complex
- Harder to maintain

### ❌ **Option 3: Keep Both (NOT RECOMMENDED)**

**Why not:**
- Duplicate data
- Version conflicts
- User confusion
- Maintenance nightmare

---

## Migration Path (Recommended)

### Phase 1: Archive Python Scripts (TODAY)

```bash
mkdir -p docs/archive/bootstrap-scripts
mv ops/bootstrap/seed_*.py docs/archive/bootstrap-scripts/
```

**Keep in `ops/bootstrap/`:**
- `download_embedding_models.py` (infrastructure)
- `download_llm_guard_models.py` (infrastructure)
- `build_llm_guard.sh` (infrastructure)
- `build_wheelhouse.sh` (infrastructure)
- `prepare_tokenizers.sh` (infrastructure)

### Phase 2: Document SQL-Only Approach

Update `ops/database/README.md`:

```markdown
## Seeding the Database

Run seed files in order:

1. 001_seed_users.sql - Default users
2. 002_seed_intents.sql - Intent system
3. 003_seed_use_cases.sql - SOC use cases
4. 004_seed_pricing.sql - Pricing tiers
5. 005_seed_models.sql - Model registry

**Note:** Python seed scripts in `docs/archive/bootstrap-scripts/` are
deprecated and should not be used.
```

### Phase 3: Update Documentation

Search and replace in docs:
- `python ops/bootstrap/seed_users.py` → `psql-17 -f ops/database/seed/001_seed_users.sql`
- `python ops/bootstrap/seed_use_cases.py` → `psql-17 -f ops/database/seed/003_seed_use_cases.sql`
- etc.

---

## Special Case: Prompt Templates

**Issue:** `seed_templates.py` reads from JSON files and populates `prompt_templates` table.

**Current SQL approach:** Prompts are embedded in `use_cases.metadata` field (see `003_seed_use_cases.sql` lines 86-92).

**Decision needed:**
- **Option A:** Keep prompts in use_cases.metadata (current approach)
- **Option B:** Create `006_seed_prompt_templates.sql` to populate prompt_templates table

**Recommendation:** Option A - prompts in use_cases.metadata is sufficient for Phase 1.

---

## Decision Required

**User, please decide:**

1. ✅ **SQL-only approach** - Archive Python seed scripts (recommended)
2. ⚠️ **Python-only approach** - Delete SQL seed files (not recommended)
3. ❌ **Keep both** - Document which to use when (really not recommended)

**My recommendation:** Option 1 (SQL-only). The SQL seed files are complete, up-to-date, and ready to use.

---

## Files to Archive

If SQL-only approach is chosen:

```bash
# Move to archive
mv ops/bootstrap/seed_users.py docs/archive/bootstrap-scripts/
mv ops/bootstrap/seed_use_cases.py docs/archive/bootstrap-scripts/
mv ops/bootstrap/seed_templates.py docs/archive/bootstrap-scripts/
mv ops/bootstrap/seed_phase1.py docs/archive/bootstrap-scripts/
```

**Keep these (infrastructure, not seeding):**
- `ops/bootstrap/download_embedding_models.py`
- `ops/bootstrap/download_llm_guard_models.py`
- `ops/bootstrap/build_llm_guard.sh`
- `ops/bootstrap/build_wheelhouse.sh`
- `ops/bootstrap/prepare_tokenizers.sh`

---

**Next Steps:** Awaiting user decision to proceed with archival and documentation updates.
