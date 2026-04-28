# RAG Services: Architecture Decisions

## Introduction

This document explains the key architectural decisions made during the implementation of the Retriever and Embedding services for the AI Operations Platform RAG architecture, particularly focusing on our approach to service deployment and development workflows.

## Docker Compose Strategy

### Decision: Unified Docker Compose File

We decided to consolidate all services into a single docker-compose file:

- `docker-compose.yml`: All services (orchestrator, databases, UI, LLM guard, embedding, retrieval)

### Rationale

1. **Simplified Maintenance**
   - Single source of truth for all service configurations
   - No need to maintain multiple compose files with potential configuration drift
   - Easier to ensure consistency across all services

2. **Deployment Simplicity**
   - Single command to start the entire system
   - No need to remember multiple file combinations
   - Reduced complexity for new developers

3. **Configuration Consistency**
   - All services use the same environment variables and patterns
   - Better health check implementations from the RAG services applied to all
   - Unified volume mounting and networking

4. **Maintenance Benefits**
   - Single file to update for configuration changes
   - Reduced risk of inconsistencies between files
   - Clearer service dependencies and relationships

## Development Workflow Integration

### Decision: Integrated Development Experience

We've implemented a unified approach:

1. **Unified Development Experience**:
   - Devcontainer configuration includes all services
   - Development overrides enable seamless editing across all services
   - Single environment for development with full context

2. **Simplified Production Deployment**:
   - Single compose file for all environments
   - Consistent service definitions
   - Clear service boundaries maintained through proper dependency management

### Implementation

1. **VSCode Devcontainer**:
   - Updated `.devcontainer/devcontainer.json` to reference single compose file
   - Added development overrides for all services in the override file
   - Configured port forwarding for all service endpoints
   - Enabled live code editing with cached volume mounts

2. **Standalone Script**:
   - Updated `run_rag_services.sh` to use single compose file
   - Script provides validation, error handling, and helpful commands
   - Simplified commands for developers

## Benefits of This Approach

1. **For Individual Developer (Current Phase)**:
   - Unified experience in a single devcontainer
   - All services start together with one command
   - Shared code editing and debugging
   - No confusion about which files to use

2. **For Team Development (Future Phase)**:
   - Clear service boundaries maintained through proper dependency management
   - Single file to understand the entire system
   - Reduced complexity for team onboarding
   - Easier to maintain and update

## Service Architecture Maintained

Despite the unified compose file, we maintain clear service boundaries:

1. **Embedding Service** (port 8002)
   - Generates vector embeddings using Sentence Transformers
   - Configurable model loading and caching
   - Independent scaling and resource allocation

2. **Retrieval Service** (port 8003)
   - Manages document storage and retrieval
   - Integrates with PostgreSQL and Qdrant
   - Provides search capabilities for the orchestrator

3. **Clear Dependencies**
   - Orchestrator depends on retrieval service
   - Retrieval service depends on embedding service and databases
   - No circular dependencies

## Collection-Based Document Management

### Decision: Collections with Immutable Embedding Model Binding

Implemented in **October 2025** (Migration 016), we introduced a collection-based architecture for organizing documents with guaranteed embedding model consistency.

**Updated:** October 27, 2025 - **ADR-021 Addendum 3: Per-Collection Embedding Model Selection**

### Architecture Overview

1. **Collection Definition**
   - Each collection has a unique name and description
   - **Per-Collection Model Selection (NEW - Oct 27, 2025):**
     - Collection chooses embedding model at creation time
     - Built-in `all-MiniLM-L6-v2` always available (local, 384D, no API costs)
     - Remote models (OpenAI, etc.) available when configured
     - Backend validates model availability via Model Registry
   - Immutable binding to chosen embedding model (cannot change after creation)
   - Tracks embedding provider (`openai`, `local`) and dimensions (e.g., 384, 1536)
   - Maps to a Qdrant collection with naming convention: `collection_{name}`

2. **Document-Collection Relationship**
   - Every document belongs to exactly one collection
   - Documents are embedded using the collection's embedding model
   - Moving documents between collections requires re-embedding if models differ
   - Enforced at the database level with foreign key constraints

3. **Default Collection**
   - System automatically creates a default collection on initialization
   - Uses system-configured default embedding model
   - Pre-existing documents are migrated to the default collection
   - Ensures no orphaned documents in the system

### Rationale

1. **Embedding Model Consistency**
   - Critical requirement: query embeddings must match document embeddings
   - Collection-level binding prevents mismatched embeddings
   - **Per-collection flexibility:** Different collections can use different models (Oct 27, 2025)
   - Enables safe migration to new embedding models by creating new collections

2. **Multi-Collection RAG Queries with Same-Model Constraint (NEW - Oct 27, 2025)**
   - **Constraint:** Use Cases can search multiple collections ONLY if they share the same embedding model
   - **Enforcement:** Frontend filters collection selection (Use Case Wizard), backend validates and returns 400 error
   - **Rationale:** Similarity scores differ between models; no reliable normalization method in v1
   - **Example Valid:** Collection A (all-MiniLM-L6-v2) + Collection B (all-MiniLM-L6-v2) ✅
   - **Example Invalid:** Collection A (all-MiniLM-L6-v2) + Collection B (text-embedding-3-small) ❌
   - **Future:** Multi-model search with score normalization deferred to Phase 5+

3. **Operational Benefits**
   - **Flexibility:** Choose best model for each collection's purpose
   - **Cost Control:** Mix built-in (free) and remote (paid) models
   - **Availability:** Built-in model guarantees 100% uptime (air-gapped friendly)
   - Clear audit trail for which embedding model processed each document
   - Ability to A/B test different embedding models
   - Supports gradual migration strategies for embedding model upgrades
   - Enables collection-specific optimization (chunk size, overlap, etc.)

### Database Schema

```sql
collections (
    id UUID PRIMARY KEY,
    name VARCHAR UNIQUE,
    description TEXT,
    embedding_model VARCHAR NOT NULL,      -- Immutable after creation
    embedding_provider VARCHAR NOT NULL,   -- Immutable after creation
    embedding_dimensions INTEGER NOT NULL, -- Immutable after creation
    qdrant_collection_name VARCHAR UNIQUE,
    is_default BOOLEAN,
    is_active BOOLEAN,
    is_system_managed BOOLEAN,
    created_by VARCHAR,
    document_count INTEGER DEFAULT 0       -- Auto-updated via triggers
)

documents (
    ...
    collection_id UUID REFERENCES collections(id) NOT NULL,
    embedding_model VARCHAR,               -- Must match collection
    embedding_provider VARCHAR,            -- Must match collection
    embedding_dimensions INTEGER           -- Must match collection
)
```

### Access Control

1. **Roles**
   - `admin`: Full access to all collection operations
   - `corpus_admin`: Full access to collection management
   - `use_case_publisher`: Can read collections for UC configuration
   - `analyst`, `user`: Can query against collections via Use Cases

2. **API Endpoints**
   - Admin: `/api/v1/admin/collections` (CRUD operations)
   - Public: `/api/v1/collections/available` (list active collections for UC config)

### Integration with RAG Pipeline

1. **Document Upload**
   - User/admin selects target collection
   - System validates collection exists and is active
   - Document embedded using collection's embedding model
   - Vector stored in collection's Qdrant collection

2. **Query Processing**
   - Use Case specifies which collections to search (`rag.vector_collections`)
   - System retrieves embedding model for each collection
   - Query embedded once per unique embedding model
   - Semantic search performed in relevant Qdrant collections
   - Results merged and ranked across collections

3. **Qdrant Synchronization**
   - Each PostgreSQL collection maps to one Qdrant collection
   - Naming convention ensures uniqueness: `fc_{collection_name}_{hash}`
   - Collection metadata stored in PostgreSQL, vectors in Qdrant
   - Consistency maintained through transactional operations

### Future Enhancements

1. **Collection Templates**
   - Pre-configured collections for common use cases
   - Default chunking strategies per collection type
   - Metadata schema templates

2. **Collection Analytics**
   - Query performance metrics per collection
   - Embedding quality metrics
   - Usage patterns and optimization recommendations

3. **Advanced Collection Features**
   - Collection versioning for embedding model migrations
   - Cross-collection deduplication
   - Collection-specific reranking strategies

**See Also:** ADR-021: Collection-Based Document Management

## Future Evolution Path

As the project transitions from solo development to team-based development:

1. **Near Term**:
   - Keep the current unified setup for simplicity
   - Maintain clear service boundaries through code organization

2. **Team Transition**:
   - Documentation clearly explains service responsibilities
   - New team members understand the system with a single file
   - Development workflow remains consistent

3. **Advanced Scaling (Post-MVP)**:
   - Consider Kubernetes manifests for more granular scaling
   - Potential implementation of dedicated resource profiles for embedding service
   - Service mesh for advanced networking if needed

## Conclusion

The unified approach we've implemented strikes a balance between simplicity and architectural clarity. It supports efficient development workflows while maintaining clear service boundaries that facilitate understanding and future scaling of the system.
