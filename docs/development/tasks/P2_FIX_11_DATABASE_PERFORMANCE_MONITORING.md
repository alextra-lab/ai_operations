# P2-FIX-11: Database Performance Monitoring Enhancement

**Status:** 📋 DEFERRED (Phase 6)
**Updated:** 2025-10-25
**Phase Assignment:** Phase 6 - Performance & Production
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 2-3 days
**Assigned:** TBD
**Created:** 2025-10-12
**Updated:** 2025-10-18
**Dependencies:** None

## 🎯 **Objective**

Enhance database performance monitoring capabilities to detect non-optimized backend code, slow queries, and database-level performance issues. Currently, the system has excellent application-level monitoring but lacks PostgreSQL-level query insights.

## 📊 **Current State Analysis**

### ✅ **Existing Monitoring (Strong Foundation)**

- **Application Metrics**: Request timing, user context, processing times
- **Audit Trail**: Complete request→response lifecycle in `audit_logs` table
- **Query History**: LLM queries with metrics and results in `query_history` table
- **Tool Performance**: Tool invocation timing and results in `tool_invocations` table
- **Structured Logging**: JSON logs with request ID propagation for correlation
- **SQLAlchemy Integration**: Request ID propagation for all DB operations

### ❌ **Missing Capabilities (Gaps)**

- **PostgreSQL Query Statistics**: No `pg_stat_statements` extension
- **SQL Query Logging**: No actual SQL statement capture
- **Slow Query Detection**: No database-level performance monitoring
- **Query Plan Analysis**: No execution plan insights
- **SQLAlchemy Debug Mode**: No query-level debugging in development

## 🚀 **Implementation Plan**

### **Phase 1: PostgreSQL Query Statistics (Priority: High)**

#### 1.1 Enable `pg_stat_statements` Extension

```sql
-- Add to database initialization/migration
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure query logging for performance monitoring
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1 second
ALTER SYSTEM SET log_statement = 'mod';              -- Log DDL and DML
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Reload configuration
SELECT pg_reload_conf();
```

#### 1.2 Add PostgreSQL Configuration to Docker

**File:** `deploy/docker-compose.yml` (and `docker-compose.test.yml`)

```yaml
postgres-db:
  image: postgres:17.6
  environment:
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_DB=${POSTGRES_DB}
    # Add PostgreSQL performance monitoring
    - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256
  volumes:
    - ../data/postgres:/var/lib/postgresql/data
    - ./config/postgresql/postgresql.conf:/etc/postgresql/postgresql.conf  # NEW
    - ./config/postgresql/pg_hba.conf:/etc/postgresql/pg_hba.conf          # NEW
  command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
```

#### 1.3 Create PostgreSQL Configuration Files

**File:** `config/postgresql/postgresql.conf`

```ini
# Performance Monitoring Configuration
shared_preload_libraries = 'pg_stat_statements'

# Query Statistics
pg_stat_statements.max = 10000
pg_stat_statements.track = all
pg_stat_statements.track_utility = on

# Query Logging
log_min_duration_statement = 1000  # Log slow queries (>1 second)
log_statement = 'mod'              # Log DDL and DML
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# Performance Insights
track_activities = on
track_counts = on
track_io_timing = on
track_functions = all

# Connection Monitoring
log_connections = on
log_disconnections = on
log_hostname = on
```

### **Phase 2: SQLAlchemy Query Logging (Priority: Medium)**

#### 2.1 Enable Development Query Logging

**File:** `src/orchestrator/app/db/database.py`

```python
def make_engine() -> Engine:
    db_name = get_db_name()
    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username=pg_user,
        password=pg_password,
        host=pg_host,
        port=pg_port,
        database=db_name,
    )

    # Enable query logging in development/test environments
    echo_queries = DEVELOPMENT or TESTING
    echo_pool = DEVELOPMENT or TESTING  # Log connection pool events

    return create_engine(
        connection_url,
        pool_pre_ping=True,
        echo=echo_queries,
        echo_pool=echo_pool,
        pool_logging_name="aiop_pool"
    )
```

#### 2.2 Add Environment Variables

**File:** `config/env/env.template`

```bash
# Database Performance Monitoring
POSTGRES_ENABLE_QUERY_LOGGING=false
POSTGRES_LOG_SLOW_QUERIES_MS=1000
POSTGRES_ENABLE_CONNECTION_LOGGING=false
```

### **Phase 3: Performance Monitoring API (Priority: Medium)**

#### 3.1 Create Database Performance Router

**File:** `src/orchestrator/app/routers/db_performance.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.database import get_db

router = APIRouter(prefix="/api/v1/db-performance", tags=["database-performance"])

@router.get("/slow-queries")
async def get_slow_queries(
    limit: int = 10,
    min_duration_ms: int = 1000,
    db: Session = Depends(get_db)
):
    """Get slowest queries from pg_stat_statements."""
    query = """
    SELECT
        query,
        calls,
        total_exec_time,
        mean_exec_time,
        rows,
        shared_blks_hit,
        shared_blks_read
    FROM pg_stat_statements
    WHERE mean_exec_time > %s
    ORDER BY mean_exec_time DESC
    LIMIT %s;
    """
    # Implementation here

@router.get("/frequent-queries")
async def get_frequent_queries(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get most frequently executed queries."""
    # Implementation here

@router.get("/query-plans/{query_hash}")
async def get_query_plan(
    query_hash: str,
    db: Session = Depends(get_db)
):
    """Get execution plan for a specific query."""
    # Implementation here
```

#### 3.2 Add Database Performance Models

**File:** `src/orchestrator/app/models/db_performance.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SlowQuery(BaseModel):
    query: str
    calls: int
    total_exec_time: float
    mean_exec_time: float
    rows: int
    shared_blks_hit: int
    shared_blks_read: int

class FrequentQuery(BaseModel):
    query: str
    calls: int
    total_exec_time: float
    mean_exec_time: float

class QueryPlan(BaseModel):
    query: str
    plan: str
    execution_time: float
    planning_time: float
```

### **Phase 4: Frontend Performance Dashboard (Priority: Low)**

#### 4.1 Create Database Performance Component

**File:** `src/frontend-angular/src/app/pages/admin/db-performance.component.ts`

```typescript
// Component for displaying database performance metrics
// - Slow queries table
// - Frequent queries table
// - Query execution plans
// - Database connection stats
```

## 📋 **Implementation Tasks**

### **Backend Tasks**

- [ ] **Task 1**: Create PostgreSQL configuration files (`config/postgresql/`)
- [ ] **Task 2**: Update Docker Compose to use custom PostgreSQL config
- [ ] **Task 3**: Add database migration to enable `pg_stat_statements`
- [ ] **Task 4**: Enhance SQLAlchemy engine configuration for query logging
- [ ] **Task 5**: Create database performance API router
- [ ] **Task 6**: Add database performance Pydantic models
- [ ] **Task 7**: Integrate performance router into main app
- [ ] **Task 8**: Add environment variables for performance monitoring

### **Frontend Tasks**

- [ ] **Task 9**: Create database performance dashboard component
- [ ] **Task 10**: Add database performance service
- [ ] **Task 11**: Integrate performance dashboard into admin section
- [ ] **Task 12**: Add database performance routing

### **Testing Tasks**

- [ ] **Task 13**: Create unit tests for performance API endpoints
- [ ] **Task 14**: Create integration tests for PostgreSQL monitoring
- [ ] **Task 15**: Add performance monitoring to CI/CD pipeline
- [ ] **Task 16**: Create database performance test scenarios

### **Documentation Tasks**

- [ ] **Task 17**: Document PostgreSQL performance configuration
- [ ] **Task 18**: Create database performance monitoring guide
- [ ] **Task 19**: Update deployment documentation
- [ ] **Task 20**: Add troubleshooting guide for performance issues

## 🔧 **Configuration Requirements**

### **Environment Variables**

```bash
# Add to config/env/env.template
POSTGRES_ENABLE_QUERY_LOGGING=false
POSTGRES_LOG_SLOW_QUERIES_MS=1000
POSTGRES_ENABLE_CONNECTION_LOGGING=false
POSTGRES_STAT_STATEMENTS_MAX=10000
```

### **Database Permissions**

```sql
-- Grant permissions for performance monitoring
GRANT SELECT ON pg_stat_statements TO aio_user;
GRANT SELECT ON pg_stat_activity TO aio_user;
GRANT SELECT ON pg_stat_database TO aio_user;
```

## 📊 **Expected Benefits**

### **Performance Insights**

- **Slow Query Detection**: Identify queries taking >1 second
- **Frequent Query Analysis**: Find N+1 query problems
- **Index Optimization**: Discover missing indexes
- **Connection Pool Monitoring**: Detect connection issues

### **Development Efficiency**

- **Query Debugging**: See actual SQL in development logs
- **Performance Regression Detection**: Track query performance over time
- **Optimization Opportunities**: Data-driven performance improvements

### **Operational Monitoring**

- **Production Performance**: Monitor database health in production
- **Capacity Planning**: Understand database load patterns
- **Troubleshooting**: Quick identification of performance bottlenecks

## 🚨 **Risk Assessment**

### **Low Risk**

- PostgreSQL configuration changes (standard monitoring features)
- Development-only query logging (no production impact)
- Read-only performance APIs (no data modification)

### **Mitigation Strategies**

- **Gradual Rollout**: Enable monitoring in test environment first
- **Performance Impact**: Monitor for any performance degradation
- **Log Volume**: Configure appropriate log retention policies
- **Permissions**: Use minimal required database permissions

## 🔄 **Integration Points**

### **Existing Systems**

- **Audit Middleware**: Extend with database performance metrics
- **Query History**: Correlate with PostgreSQL query statistics
- **Health Checks**: Add database performance to health endpoints
- **Admin Dashboard**: Integrate performance monitoring into admin UI

### **Future Enhancements**

- **Automated Alerts**: Alert on slow queries or performance degradation
- **Performance Baselines**: Establish performance benchmarks
- **Query Optimization Suggestions**: AI-powered optimization recommendations
- **Historical Trending**: Track performance metrics over time

## 📈 **Success Metrics**

### **Technical Metrics**

- [ ] `pg_stat_statements` extension active and collecting data
- [ ] Slow queries (>1s) logged and accessible via API
- [ ] Development query logging functional
- [ ] Performance dashboard displaying metrics

### **Business Metrics**

- [ ] Reduced database-related performance issues
- [ ] Faster identification of optimization opportunities
- [ ] Improved developer debugging experience
- [ ] Enhanced production monitoring capabilities

## 🔗 **Related Documentation**

- [Observability Patterns](../architecture/observability_patterns.md)
- [Database Schema](../architecture/database_schema.md)
- [Performance Optimization Guidelines](../guidelines/PERFORMANCE_OPTIMIZATION.md)
- [Monitoring and Alerting Setup](../guides/monitoring-setup.md)

---

**Next Steps:**

1. Review and approve this task specification
2. Assign to development team member
3. Begin with Phase 1 (PostgreSQL configuration)
4. Iterate through phases with testing at each step
