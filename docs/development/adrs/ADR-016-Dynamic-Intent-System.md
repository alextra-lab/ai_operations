# ADR-016: Dynamic Intent System with Domain Categorization

**Status:** PROPOSED
**Date:** 2025-10-12
**Authors:** Architecture Team
**Related:** ADR-001 (Hybrid Tools Architecture)

---

## Architecture Hierarchy

**IMPORTANT:** Intent Types provide **minimal defaults only**. Full parameterization happens in Use Case Templates.

```
Intent Type (Minimal Defaults Layer)
  ├── Provides: category, default model preference, default temperature range
  ├── Examples: QUERY, RULE_GENERATION, CONTRACT_REVIEW
  └── Purpose: Classify behavior mode, set sensible defaults

          ↓ Referenced by

Use Case Template (Full Configuration Layer) ← **This is where developers work**
  ├── References: One Intent Type (inherits defaults)
  ├── Configures: system_prompt, tools, RAG params, output format, overrides
  ├── Created by: Developers (via YAML or Admin UI)
  ├── Examples: "Splunk SPL Rule Generator", "Sigma Rule Builder", "Contract NDA Analyzer"
  └── Purpose: Complete specification of AI assistant behavior

          ↓ Instantiated as

Conversation Instance (Runtime)
  ├── Uses: One Use Case Template
  ├── Locks: Intent Type (inherited from template)
  └── Contains: Messages

          ↓ Contains

Messages (Individual exchanges)
  └── Part of: One conversation
```

**Key Distinction:**
- **Intent Type**: "What kind of task is this?" (defaults only)
- **Use Case Template**: "Exactly how should this work?" (full configuration)
- **Conversation**: "Runtime instance of a configured template"

---

## Context

The AI Operations Platform was initially designed as a **Security Operations Center (SOC) assistant** with hardcoded intent types focused on security workflows:

```python
class RequestType(str, Enum):
    QUERY = "QUERY"                    # General Q&A
    RULE_GENERATION = "RULE_GENERATION"  # SIEM detection rules
    SUMMARIZATION = "SUMMARIZATION"      # Document/incident summaries
    ENRICHMENT = "ENRICHMENT"            # Threat intelligence context
```

### Current Limitations

1. **Domain-Locked**: Intent types are hardcoded for SOC operations only
2. **Inflexible**: Adding new intents requires code changes and redeployment
3. **Not Multi-Tenant**: Cannot customize intents per organization/department
4. **Limited Scope**: Cannot serve other enterprise departments (Legal, HR, Finance, Compliance)

### Business Opportunity

Transform the platform into a **general-purpose enterprise AI assistant** that can:

- Serve multiple departments with domain-specific intents
- Allow administrators to define custom intents per organization needs
- Support role-based access to intent categories
- Enable third-party intent plugin systems

---

## Decision

We will implement a **Dynamic Intent System** with the following architecture:

### **1. Intent as First-Class Configurable Entity**

Move from hardcoded enums to database-backed, dynamically loadable intent configurations.

### **2. Intent Categorization by Domain**

Organize intents into domain categories (Security, Legal, HR, Finance, etc.) to support multi-department usage.

### **3. Role-Based Intent Access**

Link intents to user roles, allowing fine-grained access control.

### **4. Backward Compatibility**

Maintain support for existing SOC-focused use cases while enabling future extensibility.

---

## Enhanced Intent Model

### **Database Schema**

```sql
-- Intent Categories (Domains)
CREATE TABLE intent_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_code VARCHAR(50) UNIQUE NOT NULL,  -- 'SECURITY', 'LEGAL', 'HR', 'FINANCE'
    display_name VARCHAR(100) NOT NULL,         -- 'Security Operations', 'Legal Affairs'
    description TEXT,
    icon VARCHAR(50),                           -- 'security', 'gavel', 'people'
    color VARCHAR(20),                          -- '#f44336', '#2196f3'
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Intent Types (Minimal Defaults Only)
-- NOTE: Full configuration happens in Use Case Templates (use_cases table)
CREATE TABLE intent_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_code VARCHAR(50) UNIQUE NOT NULL,    -- 'QUERY', 'RULE_GENERATION', 'CONTRACT_REVIEW'
    display_name VARCHAR(100) NOT NULL,         -- 'General Query', 'Rule Generation'
    description TEXT,
    category_id UUID NOT NULL REFERENCES intent_categories(id) ON DELETE CASCADE,

    -- Minimal Default Configuration (Use Cases can override ALL of these)
    recommended_model VARCHAR(100),             -- 'mistral-small', 'mistral-large' (suggestion only)
    default_temperature_min DECIMAL(3,2),       -- 0.1 (suggested minimum for this intent type)
    default_temperature_max DECIMAL(3,2),       -- 0.3 (suggested maximum for this intent type)

    -- UI Metadata
    icon VARCHAR(50),                           -- 'question_answer', 'policy', 'gavel'
    color VARCHAR(20),                          -- For UI theming

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_system BOOLEAN DEFAULT FALSE,            -- System intents cannot be deleted
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    -- Constraints
    CONSTRAINT valid_temperature_min CHECK (default_temperature_min >= 0 AND default_temperature_min <= 2),
    CONSTRAINT valid_temperature_max CHECK (default_temperature_max >= 0 AND default_temperature_max <= 2),
    CONSTRAINT valid_temperature_range CHECK (default_temperature_min <= default_temperature_max)
);

-- NOTE: Use Case Templates (already exist in use_cases table) contain:
--   - intent_code (references this table)
--   - config_json with full configuration:
--     * system_prompt
--     * generation_params (temperature, max_tokens, etc.)
--     * rag (top_k, similarity_threshold, required_tags)
--     * tools (tool_ids, tool_config)
--     * output_contract
--     * See: docs/development/plans/UNIFIED_BACKEND_IMPLEMENTATION_PLAN.md

-- Role-Based Intent Access
CREATE TABLE role_intent_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) NOT NULL,            -- 'admin', 'analyst', 'legal_counsel'
    intent_id UUID NOT NULL REFERENCES intent_types(id) ON DELETE CASCADE,
    can_use BOOLEAN DEFAULT TRUE,
    can_configure BOOLEAN DEFAULT FALSE,       -- Can modify intent parameters
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(role_name, intent_id)
);

-- Intent Usage Analytics
CREATE TABLE intent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID NOT NULL REFERENCES intent_types(id),
    user_id UUID NOT NULL REFERENCES users(id),
    thread_id UUID REFERENCES conversation_threads(thread_id),
    use_case_id UUID REFERENCES use_cases(use_case_id),
    execution_time_ms INTEGER,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    success BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_intent_types_category ON intent_types(category_id);
CREATE INDEX idx_intent_types_active ON intent_types(is_active);
CREATE INDEX idx_role_intent_role ON role_intent_permissions(role_name);
CREATE INDEX idx_intent_usage_logs_intent ON intent_usage_logs(intent_id);
CREATE INDEX idx_intent_usage_logs_user ON intent_usage_logs(user_id);
```

### **Python Models (Pydantic)**

```python
# src/orchestrator/app/schemas/intent.py (Enhanced)

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

# ============================================================================
# Intent Categories (Domains)
# ============================================================================

class IntentCategory(BaseModel):
    """Domain category for grouping related intents"""
    id: UUID
    category_code: str  # 'SECURITY', 'LEGAL', 'HR', 'FINANCE', 'GENERAL'
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = 'folder'
    color: Optional[str] = '#607D8B'
    is_active: bool = True
    sort_order: int = 0

# Predefined categories (seeded in database)
class IntentCategoryCode(str, Enum):
    SECURITY = "SECURITY"
    LEGAL = "LEGAL"
    HR = "HR"
    FINANCE = "FINANCE"
    COMPLIANCE = "COMPLIANCE"
    GENERAL = "GENERAL"

# ============================================================================
# Intent Types (Dynamic)
# ============================================================================

class IntentTypeConfig(BaseModel):
    """
    Minimal configuration for an intent type.

    NOTE: This provides defaults only. Full configuration happens in Use Case Templates.
    Use Case Templates reference an intent_code and can override any of these suggestions.
    """
    id: UUID
    intent_code: str
    display_name: str
    description: Optional[str] = None
    category_id: UUID

    # Minimal defaults (suggestions for Use Case Templates)
    recommended_model: str = "mistral-small"  # Suggestion only, use cases can override
    default_temperature_min: float = 0.1      # Suggested minimum temp for this intent type
    default_temperature_max: float = 0.7      # Suggested maximum temp for this intent type

    # UI metadata
    icon: Optional[str] = 'chat'
    color: Optional[str] = '#2196F3'

    # Status
    is_active: bool = True
    is_system: bool = False  # System intents cannot be deleted
    sort_order: int = 0

# For reference: Use Case Template (already exists in codebase)
# class UseCaseConfig(BaseModel):
#     """Full configuration for a use case template"""
#     intent_code: str  # References IntentType
#     visibility: VisibilityConfig
#     models: ModelConfig
#     generation_params: GenerationParams  # temperature, max_tokens, etc.
#     rag: RAGConfig  # top_k, similarity_threshold, required_tags
#     tools: ToolsConfig  # tool_ids, configurations
#     output_contract: OutputContract
#     telemetry: TelemetryConfig
#     # See: src/orchestrator/app/schemas/use_case_config.py

class IntentTypeCreate(BaseModel):
    """Request to create new intent type (minimal defaults only)"""
    intent_code: str
    display_name: str
    description: Optional[str] = None
    category_id: UUID
    recommended_model: str = "mistral-small"  # Suggestion for use case templates
    default_temperature_min: float = Field(0.1, ge=0.0, le=2.0)  # Suggested min
    default_temperature_max: float = Field(0.7, ge=0.0, le=2.0)  # Suggested max
    icon: Optional[str] = 'chat'
    color: Optional[str] = '#2196F3'

class IntentTypeUpdate(BaseModel):
    """Request to update intent type"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt_template: Optional[str] = None
    recommended_model: Optional[str] = None
    default_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(None, gt=0)
    rag_top_k: Optional[int] = Field(None, gt=0)
    rag_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    rag_required_tags: Optional[List[str]] = None
    allowed_tool_ids: Optional[List[UUID]] = None
    is_active: Optional[bool] = None

# ============================================================================
# Backward Compatibility (Legacy Enum)
# ============================================================================

class RequestType(str, Enum):
    """
    Legacy enum for backward compatibility.
    These map to system intent_codes in the database.

    DEPRECATED: Use intent_code from IntentTypeConfig instead.
    This enum will be maintained for existing code but new intents
    should be created through the admin API.
    """
    QUERY = "QUERY"
    RULE_GENERATION = "RULE_GENERATION"
    SUMMARIZATION = "SUMMARIZATION"
    ENRICHMENT = "ENRICHMENT"

# ============================================================================
# SOC-Specific Intents (Example Expansion)
# ============================================================================

class SOCIntentCodes:
    """Proposed SOC-specific intent codes"""
    # Current (already implemented)
    QUERY = "QUERY"
    RULE_GENERATION = "RULE_GENERATION"
    SUMMARIZATION = "SUMMARIZATION"
    ENRICHMENT = "ENRICHMENT"

    # Proposed new SOC intents
    INCIDENT_TRIAGE = "INCIDENT_TRIAGE"
    THREAT_HUNTING = "THREAT_HUNTING"
    FORENSIC_ANALYSIS = "FORENSIC_ANALYSIS"
    PLAYBOOK_EXECUTION = "PLAYBOOK_EXECUTION"
    ALERT_CORRELATION = "ALERT_CORRELATION"
    IOC_EXTRACTION = "IOC_EXTRACTION"
    VULNERABILITY_ASSESSMENT = "VULNERABILITY_ASSESSMENT"

# ============================================================================
# Domain-Specific Intent Examples
# ============================================================================

class LegalIntentCodes:
    """Example Legal department intents"""
    CONTRACT_REVIEW = "CONTRACT_REVIEW"
    CLAUSE_EXTRACTION = "CLAUSE_EXTRACTION"
    LEGAL_RESEARCH = "LEGAL_RESEARCH"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    CASE_SUMMARIZATION = "CASE_SUMMARIZATION"
    REGULATORY_QUERY = "REGULATORY_QUERY"

class HRIntentCodes:
    """Example HR department intents"""
    POLICY_LOOKUP = "POLICY_LOOKUP"
    CANDIDATE_SCREENING = "CANDIDATE_SCREENING"
    PERFORMANCE_ANALYSIS = "PERFORMANCE_ANALYSIS"
    BENEFITS_QUERY = "BENEFITS_QUERY"
    JOB_DESCRIPTION_GENERATION = "JOB_DESCRIPTION_GENERATION"

class FinanceIntentCodes:
    """Example Finance department intents"""
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    BUDGET_PLANNING = "BUDGET_PLANNING"
    INVOICE_PROCESSING = "INVOICE_PROCESSING"
    EXPENSE_CATEGORIZATION = "EXPENSE_CATEGORIZATION"
    FORECAST_GENERATION = "FORECAST_GENERATION"

# ============================================================================
# Role-Based Access
# ============================================================================

class RoleIntentPermission(BaseModel):
    """Role-based access control for intents"""
    id: UUID
    role_name: str  # 'admin', 'analyst', 'legal_counsel', 'hr_manager'
    intent_id: UUID
    can_use: bool = True
    can_configure: bool = False

class RoleIntentPermissionCreate(BaseModel):
    role_name: str
    intent_id: UUID
    can_use: bool = True
    can_configure: bool = False
```

---

## System Architecture

### **Intent Loading & Caching**

```python
# src/orchestrator/app/services/intent_service.py

from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from ..db.models import IntentType, IntentCategory, RoleIntentPermission
from ..schemas.intent import IntentTypeConfig, IntentCategory as IntentCategorySchema

class IntentService:
    """Service for managing dynamic intent types"""

    def __init__(self, db: Session):
        self.db = db
        self._intent_cache: Dict[str, IntentTypeConfig] = {}
        self._category_cache: Dict[str, IntentCategorySchema] = {}
        self._load_cache()

    def _load_cache(self):
        """Load all active intents into memory cache"""
        intents = self.db.query(IntentType).filter(IntentType.is_active == True).all()
        for intent in intents:
            self._intent_cache[intent.intent_code] = IntentTypeConfig.model_validate(intent)

        categories = self.db.query(IntentCategory).filter(IntentCategory.is_active == True).all()
        for category in categories:
            self._category_cache[category.category_code] = IntentCategorySchema.model_validate(category)

    def get_intent_by_code(self, intent_code: str) -> Optional[IntentTypeConfig]:
        """Get intent configuration by code"""
        return self._intent_cache.get(intent_code)

    def list_intents_by_category(self, category_code: str) -> List[IntentTypeConfig]:
        """List all intents in a category"""
        category = self._category_cache.get(category_code)
        if not category:
            return []

        return [
            intent for intent in self._intent_cache.values()
            if intent.category_id == category.id
        ]

    def list_intents_for_role(self, role_name: str) -> List[IntentTypeConfig]:
        """List intents accessible to a specific role"""
        permissions = self.db.query(RoleIntentPermission).filter(
            RoleIntentPermission.role_name == role_name,
            RoleIntentPermission.can_use == True
        ).all()

        intent_ids = {p.intent_id for p in permissions}

        return [
            intent for intent in self._intent_cache.values()
            if intent.id in intent_ids
        ]

    def create_intent(self, intent_create: 'IntentTypeCreate', creator_id: UUID) -> IntentTypeConfig:
        """Create new intent type"""
        intent = IntentType(
            **intent_create.model_dump(),
            created_by=creator_id
        )
        self.db.add(intent)
        self.db.commit()
        self.db.refresh(intent)

        # Update cache
        config = IntentTypeConfig.model_validate(intent)
        self._intent_cache[intent.intent_code] = config

        return config

    def update_intent(self, intent_code: str, intent_update: 'IntentTypeUpdate') -> Optional[IntentTypeConfig]:
        """Update existing intent type"""
        intent = self.db.query(IntentType).filter(IntentType.intent_code == intent_code).first()
        if not intent:
            return None

        if intent.is_system:
            # System intents can only update certain fields
            allowed_fields = {'display_name', 'description', 'sort_order'}
            update_data = {k: v for k, v in intent_update.model_dump(exclude_unset=True).items() if k in allowed_fields}
        else:
            update_data = intent_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(intent, field, value)

        self.db.commit()
        self.db.refresh(intent)

        # Update cache
        config = IntentTypeConfig.model_validate(intent)
        self._intent_cache[intent.intent_code] = config

        return config

    def delete_intent(self, intent_code: str) -> bool:
        """Delete intent type (soft delete by setting is_active=False)"""
        intent = self.db.query(IntentType).filter(IntentType.intent_code == intent_code).first()
        if not intent or intent.is_system:
            return False

        intent.is_active = False
        self.db.commit()

        # Remove from cache
        self._intent_cache.pop(intent_code, None)

        return True

    def reload_cache(self):
        """Reload cache from database (call after bulk updates)"""
        self._intent_cache.clear()
        self._category_cache.clear()
        self._load_cache()
```

### **Admin API Endpoints**

```python
# src/orchestrator/app/routers/admin/intents.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from shared.auth import get_current_user
from shared.auth.models import TokenPayload
from ...db.database import SessionLocal
from ...schemas.intent import (
    IntentTypeConfig,
    IntentTypeCreate,
    IntentTypeUpdate,
    IntentCategory,
    RoleIntentPermission,
    RoleIntentPermissionCreate
)
from ...services.intent_service import IntentService

router = APIRouter(prefix="/api/v1/admin/intents", tags=["admin-intents"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_intent_service(db: Session = Depends(get_db)) -> IntentService:
    return IntentService(db)

# ============================================================================
# Intent Types Management
# ============================================================================

@router.get("/types", response_model=List[IntentTypeConfig])
async def list_intent_types(
    category_code: str | None = None,
    active_only: bool = True,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """List all intent types, optionally filtered by category"""
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    if category_code:
        return intent_service.list_intents_by_category(category_code)
    else:
        return list(intent_service._intent_cache.values())

@router.get("/types/{intent_code}", response_model=IntentTypeConfig)
async def get_intent_type(
    intent_code: str,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Get specific intent type by code"""
    intent = intent_service.get_intent_by_code(intent_code)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent type not found")
    return intent

@router.post("/types", response_model=IntentTypeConfig, status_code=status.HTTP_201_CREATED)
async def create_intent_type(
    intent_create: IntentTypeCreate,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Create new intent type (admin only)"""
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        return intent_service.create_intent(intent_create, current_user.user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/types/{intent_code}", response_model=IntentTypeConfig)
async def update_intent_type(
    intent_code: str,
    intent_update: IntentTypeUpdate,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Update intent type configuration"""
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    intent = intent_service.update_intent(intent_code, intent_update)
    if not intent:
        raise HTTPException(status_code=404, detail="Intent type not found")

    return intent

@router.delete("/types/{intent_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_type(
    intent_code: str,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Delete intent type (cannot delete system intents)"""
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not intent_service.delete_intent(intent_code):
        raise HTTPException(status_code=400, detail="Cannot delete system intent or intent not found")

# ============================================================================
# Intent Categories Management
# ============================================================================

@router.get("/categories", response_model=List[IntentCategory])
async def list_intent_categories(
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """List all intent categories"""
    return list(intent_service._category_cache.values())

# ============================================================================
# Role-Based Permissions
# ============================================================================

@router.get("/roles/{role_name}/intents", response_model=List[IntentTypeConfig])
async def list_role_intents(
    role_name: str,
    intent_service: IntentService = Depends(get_intent_service),
    current_user: TokenPayload = Depends(get_current_user)
):
    """List intents accessible to a specific role"""
    if 'admin' not in current_user.roles and role_name not in current_user.roles:
        raise HTTPException(status_code=403, detail="Access denied")

    return intent_service.list_intents_for_role(role_name)

@router.post("/roles/permissions", status_code=status.HTTP_201_CREATED)
async def grant_role_intent_permission(
    permission: RoleIntentPermissionCreate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Grant intent permission to role"""
    if 'admin' not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Implementation...
    pass
```

---

## Seed Data (Initial Intents)

```sql
-- ops/migrations/sql/seed_intent_system.sql

-- ============================================================================
-- Intent Categories
-- ============================================================================

INSERT INTO intent_categories (category_code, display_name, description, icon, color) VALUES
('GENERAL', 'General Purpose', 'General-purpose AI assistant capabilities', 'chat', '#607D8B'),
('SECURITY', 'Security Operations', 'Cybersecurity and SOC workflows', 'security', '#f44336'),
('LEGAL', 'Legal Affairs', 'Legal document analysis and compliance', 'gavel', '#9C27B0'),
('HR', 'Human Resources', 'HR policies, recruitment, and employee management', 'people', '#4CAF50'),
('FINANCE', 'Finance & Accounting', 'Financial analysis and reporting', 'attach_money', '#FF9800'),
('COMPLIANCE', 'Compliance & Risk', 'Regulatory compliance and risk management', 'policy', '#3F51B5');

-- ============================================================================
-- Security Operations Intents
-- ============================================================================

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, default_max_tokens,
    rag_top_k, rag_similarity_threshold, rag_required_tags,
    icon, color, is_system, sort_order
)
SELECT
    'QUERY',
    'General Query',
    'Answer general questions using available knowledge base',
    id,
    'You are a helpful AI assistant with expertise in security operations. Provide clear, accurate answers based on the context provided.',
    'mistral-small',
    0.7,
    2048,
    5,
    0.7,
    ARRAY[]::TEXT[],
    'question_answer',
    '#2196F3',
    TRUE,
    1
FROM intent_categories WHERE category_code = 'SECURITY';

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, default_max_tokens,
    rag_top_k, rag_similarity_threshold, rag_required_tags,
    icon, color, is_system, sort_order
)
SELECT
    'RULE_GENERATION',
    'Detection Rule Generation',
    'Generate SIEM detection rules (Splunk, Sigma, KQL, Yara)',
    id,
    'You are an expert in creating SIEM detection rules. Generate accurate, optimized detection rules for security monitoring platforms. Ensure rules are syntactically correct and follow best practices.',
    'mistral-large',
    0.2,
    4096,
    10,
    0.8,
    ARRAY['rules', 'siem']::TEXT[],
    'policy',
    '#FF5722',
    TRUE,
    2
FROM intent_categories WHERE category_code = 'SECURITY';

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, default_max_tokens,
    icon, color, is_system, sort_order
)
SELECT
    'SUMMARIZATION',
    'Content Summarization',
    'Summarize documents, incidents, or security events',
    id,
    'You are an expert at creating concise, accurate summaries. Extract key points and present them in a clear, structured format.',
    'mistral-small',
    0.5,
    2048,
    'summarize',
    '#4CAF50',
    TRUE,
    3
FROM intent_categories WHERE category_code = 'SECURITY';

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, default_max_tokens,
    rag_top_k, rag_similarity_threshold, rag_required_tags,
    icon, color, is_system, sort_order
)
SELECT
    'ENRICHMENT',
    'Threat Intelligence Enrichment',
    'Enrich IOCs and incidents with threat intelligence context',
    id,
    'You are a threat intelligence analyst. Provide comprehensive context and enrichment for security indicators, including attribution, techniques, and remediation guidance.',
    'mistral-large',
    0.3,
    3072,
    15,
    0.75,
    ARRAY['threat-intel', 'ioc']::TEXT[],
    'psychology',
    '#9C27B0',
    TRUE,
    4
FROM intent_categories WHERE category_code = 'SECURITY';

-- Proposed new SOC intents
INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    recommended_model, default_temperature, icon, is_system
)
SELECT
    'INCIDENT_TRIAGE',
    'Incident Triage & Classification',
    'Assess incident severity, urgency, and recommended response actions',
    id,
    'mistral-large',
    0.3,
    'emergency',
    FALSE
FROM intent_categories WHERE category_code = 'SECURITY';

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    recommended_model, default_temperature, icon, is_system
)
SELECT
    'THREAT_HUNTING',
    'Proactive Threat Hunting',
    'Generate threat hunting queries and identify potential compromises',
    id,
    'mistral-large',
    0.4,
    'search',
    FALSE
FROM intent_categories WHERE category_code = 'SECURITY';

-- ============================================================================
-- Legal Department Intents
-- ============================================================================

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, icon, is_system
)
SELECT
    'CONTRACT_REVIEW',
    'Contract Review & Analysis',
    'Analyze contracts for key terms, risks, and compliance issues',
    id,
    'You are a legal expert specializing in contract analysis. Review contracts for compliance, identify risks, extract key terms, and provide actionable insights.',
    'mistral-large',
    0.2,
    'description',
    FALSE
FROM intent_categories WHERE category_code = 'LEGAL';

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, default_temperature, icon, is_system
)
SELECT
    'LEGAL_RESEARCH',
    'Legal Research',
    'Research case law, statutes, and legal precedents',
    id,
    'You are a legal researcher. Provide comprehensive legal research with citations, relevant case law, and statutory references.',
    'mistral-large',
    0.5,
    'search',
    FALSE
FROM intent_categories WHERE category_code = 'LEGAL';

-- ============================================================================
-- HR Department Intents
-- ============================================================================

INSERT INTO intent_types (
    intent_code, display_name, description, category_id,
    system_prompt_template, recommended_model, icon, is_system
)
SELECT
    'POLICY_LOOKUP',
    'HR Policy Lookup',
    'Answer questions about HR policies, procedures, and benefits',
    id,
    'You are an HR policy expert. Provide clear, accurate information about company policies, benefits, and procedures.',
    'mistral-small',
    'info',
    FALSE
FROM intent_categories WHERE category_code = 'HR';

-- ============================================================================
-- Role-Based Permissions (Examples)
-- ============================================================================

-- Admins get access to everything
INSERT INTO role_intent_permissions (role_name, intent_id, can_use, can_configure)
SELECT 'admin', id, TRUE, TRUE
FROM intent_types;

-- Analysts get SOC intents
INSERT INTO role_intent_permissions (role_name, intent_id, can_use, can_configure)
SELECT 'analyst', id, TRUE, FALSE
FROM intent_types it
JOIN intent_categories ic ON it.category_id = ic.id
WHERE ic.category_code = 'SECURITY';

-- Legal team gets legal intents
INSERT INTO role_intent_permissions (role_name, intent_id, can_use, can_configure)
SELECT 'legal_counsel', id, TRUE, FALSE
FROM intent_types it
JOIN intent_categories ic ON it.category_id = ic.id
WHERE ic.category_code = 'LEGAL';

-- HR managers get HR intents
INSERT INTO role_intent_permissions (role_name, intent_id, can_use, can_configure)
SELECT 'hr_manager', id, TRUE, FALSE
FROM intent_types it
JOIN intent_categories ic ON it.category_id = ic.id
WHERE ic.category_code = 'HR';
```

---

## Migration Path

### **Phase 1: Database & Models (Foundation)**

- Add new tables for intent_categories, intent_types, role_intent_permissions
- Seed initial data with current 4 SOC intents as "system intents"
- Create IntentService for dynamic loading

### **Phase 2: Backend Integration (Orchestrator)**

- Update IntentParser to use IntentService instead of hardcoded enum
- Maintain RequestType enum for backward compatibility
- Update PromptAssembler to fetch templates from intent_types table

### **Phase 3: Admin UI (Configuration)**

- Create admin pages for managing intents and categories
- Add role permission management
- Intent builder wizard

### **Phase 4: User-Facing Changes**

- Update use case creation to select from available intents
- Show category-filtered intents in UI
- Display intent icons and colors

---

## Benefits

### **1. Platform Versatility**

- **Multi-Department**: Serve Security, Legal, HR, Finance, Compliance
- **Multi-Tenant**: Customize intents per organization
- **Industry Agnostic**: Healthcare, Finance, Government, etc.

### **2. No-Code Intent Creation**

- Admins can add new intents without developer involvement
- Configure system prompts, models, parameters through UI
- Enable/disable intents dynamically

### **3. Role-Based Security**

- Fine-grained access control per intent
- Separate analyst workflows from legal workflows
- Audit trail of who uses which intents

### **4. Scalability**

- Plugin architecture for third-party intents
- Intent marketplace potential
- Multi-organization SaaS model

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes to existing code | HIGH | Maintain RequestType enum, gradual migration |
| Performance overhead from DB lookups | MEDIUM | In-memory caching with reload mechanism |
| Poorly configured intents | MEDIUM | Validation rules, intent testing framework |
| Intent proliferation | LOW | Category organization, admin approval workflow |

---

## Success Metrics

- **Extensibility**: Time to add new intent < 5 minutes (via admin UI)
- **Adoption**: Number of departments using platform
- **Performance**: Intent lookup < 1ms (cached)
- **Flexibility**: Number of custom intents created by organizations

---

## References

- Current Intent System: `src/orchestrator/app/schemas/intent.py`
- Orchestrator: `src/orchestrator/app/orchestrator/controller.py`
- Template System: `src/orchestrator/app/orchestrator/prompt_assembler.py`
- ADR-001: Hybrid Tools Architecture

---

## Decision Outcome

**Status:** PROPOSED - Pending stakeholder review

This ADR proposes a significant architectural evolution that transforms the platform from a SOC-specific tool to a general-purpose enterprise AI assistant. Implementation should be phased to maintain backward compatibility and minimize risk.

**Next Steps:**

1. Review and approve this ADR
2. Create detailed implementation plan with phases
3. Design admin UI mockups
4. Implement Phase 1 (database schema)
5. Migrate existing orchestrator to use dynamic intents
