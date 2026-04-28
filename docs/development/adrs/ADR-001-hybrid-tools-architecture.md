# Tools Implementation Plan - Hybrid Architecture Update

**Date:** October 1, 2025
**Status:** ⚠️ PARTIALLY SUPERSEDED by ADR-057
**Impact:** Major - Affects Phase T3 implementation

> **Note (2025-11-27):** The `tool_purpose` and `service_location` fields defined in this ADR have been superseded by the security-focused classification in [ADR-057: MCP Tool Security Classification](ADR-057-MCP-Tool-Security-Classification.md). All MCP tools now run in the Orchestrator; the security classification provides risk-based access control instead of execution location routing.

---

## Executive Summary

The Tools Implementation Plan has been updated to reflect a **Hybrid Architecture** design where tools are distributed between the **Orchestrator** and **Retrieval Service** based on their purpose.

### Key Decision

**Centralized Registry + Distributed Execution**

- ✅ Platform Registry Layer remains centralized (single source of truth)
- ✅ Tool execution distributed based on `tool_purpose` and `service_location`
- ✅ Retrieval tools enhance RAG capabilities
- ✅ Orchestrator tools handle reasoning and external data

---

## Architecture Changes

### Tool Classification

**Retrieval Tools** (`tool_purpose = "retrieval"`, `service_location = "retrieval_service"`):

- **Purpose**: Access internal platform data stores
- **Examples**: Elasticsearch, PostgreSQL, Qdrant, ClickHouse
- **Execution**: Runs inside the Retrieval Service (corpus_svc)
- **Benefit**: Enhances RAG by adding structured/indexed data retrieval
- **Key Insight**: These tools need direct database connections without network hops

**Orchestrator Tools** (`tool_purpose = "orchestrator"`, `service_location = "orchestrator"`):

- **Purpose**: Reasoning, analysis, or external data access
- **Examples**: Context7, ClearThought, SequentialThinking, Web Scraping, **Docker MCP Gateway**
- **Execution**: Runs inside the Orchestrator service
- **Benefit**: LLM function calling for reasoning or external operations
- **Key Insight**: These tools call external services or perform reasoning - they don't need internal database access

**Example: Docker MCP Gateway**

The Docker MCP Toolkit command `docker mcp gateway run` would be configured as an **Orchestrator Tool**:

- **Why?** It's an external process exposing multiple MCP servers
- **Server Type**: STDIO
- **Command**: `["docker", "mcp", "gateway", "run"]`
- **service_location**: `orchestrator` (doesn't need direct database access)

### Data Flow

```
1. Admin configures tool with service_location
2. Developer adds tool to use case allowlist
3. LLM requests tool call
4. Orchestrator validates against allowlist
5. Orchestrator checks service_location:
   - If "orchestrator": Execute locally
   - If "retrieval_service": Forward via POST /internal/tools/execute
6. Tool result returned to Orchestrator
7. Orchestrator logs audit trail
8. Result incorporated into LLM context
```

---

## Schema Changes

### Database Migration Update

**Added to `tools` table:**

```sql
-- Hybrid Architecture: Tool Purpose and Service Location
tool_purpose VARCHAR(50) NOT NULL,            -- 'retrieval', 'orchestrator'
service_location VARCHAR(50) NOT NULL,        -- 'retrieval_service', 'orchestrator'

-- Constraints
CONSTRAINT valid_tool_purpose CHECK (tool_purpose IN ('retrieval', 'orchestrator')),
CONSTRAINT valid_service_location CHECK (service_location IN ('retrieval_service', 'orchestrator')),

-- Indexes
CREATE INDEX idx_tools_purpose ON tools(tool_purpose);
CREATE INDEX idx_tools_service_location ON tools(service_location);
```

### Pydantic Schema Updates

**New Enums:**

```python
class ToolPurpose(str, Enum):
    """Tool purpose classification for hybrid architecture."""
    RETRIEVAL = "retrieval"      # Internal data access
    ORCHESTRATOR = "orchestrator"  # Reasoning or external data

class ServiceLocation(str, Enum):
    """Service where tool executor runs."""
    RETRIEVAL_SERVICE = "retrieval_service"
    ORCHESTRATOR = "orchestrator"
```

**Updated `ToolBase`:**

```python
class ToolBase(BaseModel):
    # ... existing fields ...

    # Hybrid Architecture
    tool_purpose: ToolPurpose
    service_location: ServiceLocation

    # ... rest of fields ...
```

---

## Implementation Changes

### Phase T1: Tool Infrastructure Foundation

**✅ NO CHANGES** - Database schema, secrets management, admin API, permissions

**Updates:**

- T1-F1: Add `tool_purpose` and `service_location` fields to schema ✓
- All other features remain unchanged

### Phase T2: MCP Client Integration

**✅ NO CHANGES** - MCP client library works the same regardless of where it's called from

### Phase T3: Tool Execution (MAJOR CHANGES)

**Original Plan:**

- T3-F1: Tool Executor Service (single executor in backend)
- T3-F2: Orchestrator Integration
- T3-F3: Tool Result Processing
- T3-F4: Error Handling & Circuit Breakers

**Updated Plan:**

- **T3-F1: Base Tool Executor** (shared base class)
- **T3-F2: Orchestrator Tool Executor** (orchestrator-specific tools)
- **T3-F3: Retrieval Service Tool Executor** (NEW - retrieval-specific tools)
- **T3-F4: Service-to-Service Communication** (NEW - internal API for tool execution)
- **T3-F5: Tool Routing Logic** (NEW - orchestrator determines execution location)
- **T3-F6: Tool Result Processing** (enhanced with service metadata)
- **T3-F7: Error Handling & Circuit Breakers** (distributed health monitoring)

### Phase T4: Enterprise Features

**Updates:**

- T4-F1: Health Monitoring Dashboard (now monitors distributed tools)
- T4-F2: Audit & Analytics (includes service_location in reports)
- T4-F3: Developer UI (shows tool location and status)
- T4-F4: Tool Testing (tests tools in appropriate service)

---

## New Components Required

### 1. Base Tool Executor

**File:** `src/shared/tools/base_executor.py`

```python
"""
Base tool executor with shared logic.

Used by both Orchestrator and Retrieval Service executors.
"""

class BaseToolExecutor:
    """Base class for tool execution."""

    def __init__(self, db: Session):
        self.db = db
        self.discovery_service = ToolDiscoveryService(db)
        self.permission_service = ToolPermissionService(db)
        self.circuit_breaker = CircuitBreaker()

    async def execute_tool(
        self,
        tool_id: UUID,
        tool_name: str,
        parameters: dict[str, Any],
        user_id: UUID,
        user_role: str,
        **kwargs
    ) -> dict[str, Any]:
        """Execute tool with full observability."""
        # Common execution logic
        # - Check enabled
        # - Check circuit breaker
        # - Check permissions
        # - Check rate limits
        # - Execute with retries
        # - Record audit
```

### 2. Orchestrator Tool Executor

**File:** `src/orchestrator/app/services/orchestrator_tool_executor.py`

```python
"""
Tool executor for orchestrator-specific tools.

Executes tools with tool_purpose = 'orchestrator' and service_location = 'orchestrator'.
"""

from src.shared.tools.base_executor import BaseToolExecutor

class OrchestratorToolExecutor(BaseToolExecutor):
    """Executor for orchestrator tools."""

    async def execute_tool(self, **kwargs) -> dict[str, Any]:
        """Execute orchestrator tool locally."""
        # Use base class logic + orchestrator-specific handling
        return await super().execute_tool(**kwargs)
```

### 3. Retrieval Service Tool Executor

**File:** `src/corpus_svc/app/services/retrieval_tool_executor.py`

```python
"""
Tool executor for retrieval-specific tools.

Executes tools with tool_purpose = 'retrieval' and service_location = 'retrieval_service'.
"""

from src.shared.tools.base_executor import BaseToolExecutor

class RetrievalToolExecutor(BaseToolExecutor):
    """Executor for retrieval tools."""

    async def execute_tool(self, **kwargs) -> dict[str, Any]:
        """Execute retrieval tool locally."""
        # Use base class logic + retrieval-specific handling
        return await super().execute_tool(**kwargs)
```

### 4. Internal Tool Execution API

**File:** `src/corpus_svc/app/routers/internal_tools.py`

```python
"""
Internal API for tool execution in Retrieval Service.

Called by Orchestrator when routing retrieval tools.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services.retrieval_tool_executor import RetrievalToolExecutor
from ..utils.service_auth import verify_service_token

router = APIRouter(prefix="/internal/tools", tags=["internal"])


@router.post("/execute")
async def execute_tool(
    tool_name: str,
    parameters: dict[str, Any],
    run_id: str,
    user_id: UUID,
    user_role: str,
    use_case_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    service_token: str = Depends(verify_service_token)
):
    """
    Execute a retrieval tool.

    **Authentication:** Service-to-service token required
    **Called By:** Orchestrator
    """
    # Find tool
    tool = db.query(Tool).filter(
        Tool.tool_id == tool_name,
        Tool.service_location == ServiceLocation.RETRIEVAL_SERVICE
    ).first()

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    # Execute
    executor = RetrievalToolExecutor(db)
    result = await executor.execute_tool(
        tool_id=tool.id,
        tool_name=tool_name,
        parameters=parameters,
        user_id=user_id,
        user_role=user_role,
        run_id=run_id,
        use_case_id=use_case_id
    )

    return {
        "tool_name": tool_name,
        "result": result,
        "service": "retrieval_service",
        "status": "success"
    }
```

### 5. Tool Routing Logic

**File:** `src/orchestrator/app/services/tool_router.py`

```python
"""
Tool routing service.

Routes tool execution requests to appropriate service based on service_location.
"""

import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from ..db.models import Tool
from ..schemas.tool import ServiceLocation
from .orchestrator_tool_executor import OrchestratorToolExecutor

logger = logging.getLogger(__name__)


class ToolRouter:
    """Routes tool execution to appropriate service."""

    def __init__(self, db: Session):
        self.db = db
        self.orchestrator_executor = OrchestratorToolExecutor(db)

    async def route_and_execute(
        self,
        tool_id: UUID,
        tool_name: str,
        parameters: dict[str, Any],
        user_id: UUID,
        user_role: str,
        **kwargs
    ) -> dict[str, Any]:
        """
        Route tool execution to appropriate service.

        Returns:
            Tool execution result with service metadata
        """
        # Load tool configuration
        tool = self.db.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        # Route based on service_location
        if tool.service_location == ServiceLocation.ORCHESTRATOR:
            # Execute locally
            logger.info(f"Executing tool {tool_name} locally in orchestrator")
            result = await self.orchestrator_executor.execute_tool(
                tool_id=tool_id,
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                user_role=user_role,
                **kwargs
            )
            return {
                "result": result,
                "executed_in": "orchestrator",
                "tool_name": tool_name
            }

        elif tool.service_location == ServiceLocation.RETRIEVAL_SERVICE:
            # Forward to Retrieval Service
            logger.info(f"Forwarding tool {tool_name} to retrieval service")
            result = await self._call_retrieval_service(
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                user_role=user_role,
                **kwargs
            )
            return {
                "result": result["result"],
                "executed_in": "retrieval_service",
                "tool_name": tool_name
            }

        else:
            raise ValueError(f"Unknown service location: {tool.service_location}")

    async def _call_retrieval_service(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        user_id: UUID,
        user_role: str,
        run_id: str = None,
        use_case_id: UUID = None,
        **kwargs
    ) -> dict[str, Any]:
        """Call Retrieval Service internal API."""
        import os

        # Get Retrieval Service endpoint from environment
        retrieval_service_url = os.environ.get(
            "RETRIEVAL_SERVICE_URL",
            "http://retrieval:8002"
        )

        # Get service token
        service_token = self._get_service_token()

        # Make HTTP request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{retrieval_service_url}/internal/tools/execute",
                json={
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "user_id": str(user_id),
                    "user_role": user_role,
                    "run_id": run_id,
                    "use_case_id": str(use_case_id) if use_case_id else None
                },
                headers={
                    "Authorization": f"Bearer {service_token}",
                    "X-Service-Name": "orchestrator"
                }
            )

            response.raise_for_status()
            return response.json()

    def _get_service_token(self) -> str:
        """Get service-to-service authentication token."""
        import os
        return os.environ.get("SERVICE_AUTH_TOKEN", "")
```

---

## Service-to-Service Authentication

### Requirements

1. **Service JWT Tokens**: Each service has a service account
2. **Environment Variables**:

   ```bash
   # Backend (Orchestrator)
   RETRIEVAL_SERVICE_URL=http://retrieval:8002
   SERVICE_AUTH_TOKEN=<generated_token>

   # Retrieval Service
   SERVICE_AUTH_TOKENS=orchestrator:<token>,rag:<token>
   ```

3. **Token Validation**: `src/shared/auth/service_auth.py`

   ```python
   def verify_service_token(token: str) -> dict:
       """Verify service-to-service authentication token."""
       # Decode JWT, verify signature, check service_id claim
       pass
   ```

---

## Target Tool Configurations (Updated)

### Retrieval Tools

| Tool ID | Name | Category | Purpose | Service Location |
|---------|------|----------|---------|------------------|
| `elasticsearch_search` | Elasticsearch Search | database | retrieval | retrieval_service |
| `postgres_query` | PostgreSQL Query | database | retrieval | retrieval_service |
| `qdrant_search` | Qdrant Vector Search | vector_db | retrieval | retrieval_service |
| `clickhouse_analytics` | ClickHouse Analytics | database | retrieval | retrieval_service |

### Orchestrator Tools

| Tool ID | Name | Category | Purpose | Service Location |
|---------|------|----------|---------|------------------|
| `context7_docs` | Context7 Documentation | documentation | orchestrator | orchestrator |
| `clearthought` | ClearThought Reasoning | reasoning | orchestrator | orchestrator |
| `sequential_thinking` | Sequential Thinking | reasoning | orchestrator | orchestrator |
| `web_scraper` | Web Scraping | web_scraping | orchestrator | orchestrator |
| `collaborative_reasoning` | Collaborative Reasoning | reasoning | orchestrator | orchestrator |

---

## Migration Plan

### For Existing Deployments (If B4-F3 was deployed)

1. **Run schema migration** to add `tool_purpose` and `service_location` columns
2. **Update existing tool records** with appropriate values:

   ```sql
   UPDATE tools
   SET tool_purpose = 'orchestrator',
       service_location = 'orchestrator'
   WHERE category IN ('reasoning', 'web_scraping', 'documentation');

   UPDATE tools
   SET tool_purpose = 'retrieval',
       service_location = 'retrieval_service'
   WHERE category IN ('database', 'vector_db');
   ```

3. **Deploy Retrieval Service updates** with Tool Executor
4. **Deploy Backend updates** with Tool Router
5. **Test service-to-service communication**

### For Fresh Deployments

1. Deploy with full hybrid architecture from start
2. All tools configured with correct `service_location` from creation

---

## Benefits Recap

✅ **Clean Separation**: Data retrieval vs. reasoning/external operations
✅ **Enhanced RAG**: Retrieval Service can use tools internally for richer context
✅ **Centralized Security**: Single Platform Registry for configs, secrets, permissions
✅ **Distributed Execution**: Tools run where they're most efficient
✅ **Service Isolation**: Services remain independent and scalable
✅ **Minimal Overhead**: Service-to-service calls add only ~5-10ms
✅ **Future-Proof**: Easy to add more service types (e.g., specialized analytics service)

---

## Next Steps

1. ✅ Architecture documented (this file)
2. ⏳ Update `TOOLS_IMPLEMENTATION_PLAN.md` Phase T3
3. ⏳ Create `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md` updates
4. ⏳ Begin implementation with T1-F1 (schema updates)
5. ⏳ Implement T3 with distributed execution

---

## Deprecation Notice (2025-11-27)

### What Changed

The `tool_purpose` and `service_location` fields are now **deprecated** in favor of a security-focused classification model defined in [ADR-057](ADR-057-MCP-Tool-Security-Classification.md).

### Why

The original hybrid architecture conflated two concerns:

1. **Technical execution location** - Where does the MCP client run?
2. **Security classification** - What are the risks of this tool?

In practice:

- **All MCP tools run in Orchestrator** - The "retrieval service" execution path was never implemented
- **Docker MCP Gateway** breaks the binary classification (contains tools of all types)
- **Users don't understand `tool_purpose`** - It's an internal architectural detail
- **Security controls are the real need** - Risk-based access control is more valuable

### New Model (ADR-057)

Instead of `tool_purpose` / `service_location`, tools are now classified by:

| Attribute | Purpose |
|-----------|---------|
| `data_source_type` | Internal, External, None, Mixed |
| `data_flow_direction` | Ingress, Egress, Bidirectional, None |
| `network_access_level` | Isolated, Internal, External |
| `max_data_sensitivity` | Public, Internal, Confidential, Restricted |

### Migration

1. Old fields kept for backward compatibility (default to `orchestrator`)
2. New security fields added with sensible defaults
3. UI collects security classification instead of `tool_purpose`
4. Use Cases can restrict tools based on security attributes

### Corpus Service Clarification

The **Corpus Service** is specifically for:

- ✅ Document corpus (RAG knowledge base)
- ✅ Chunking, embeddings, semantic search
- ✅ Static ingested content

**MCP tools** are for:

- ✅ Dynamic data retrieval (Elasticsearch datalake, APIs)
- ✅ Reasoning (ClearThought, Sequential Thinking)
- ✅ External integrations (web scraping, third-party services)

All MCP tools run in **Orchestrator**, not Corpus Service.

---

**Status:** ⚠️ PARTIALLY SUPERSEDED - See ADR-057
**Approved By:** Architecture review (Claude-4.5 Max reasoning)
**Document Version:** 1.1 (updated 2025-11-27)
