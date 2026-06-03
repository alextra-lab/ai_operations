# Collection Management API Reference

**Version:** 1.1
**Base URL:** `/api/v1/admin/collections`
**Authentication:** Required (Admin or Corpus Admin role)
**Date:** October 27, 2025
**Status:** Implemented

---

## Overview

The Collection Management API provides comprehensive CRUD operations for managing document collections in the AI Operations Platform system. Collections are isolated namespaces for documents that share the same embedding model, enabling multi-tenant and multi-purpose vector storage.

**Key Features:**

- **Per-Collection Embedding Model Selection (NEW - Oct 27, 2025):**
  - Each collection chooses its embedding model at creation (immutable thereafter)
  - Built-in `all-MiniLM-L6-v2` always available (local, 384D, no API costs)
  - Backend validates model availability via Model Registry
  - Frontend provides dropdown with available models
- Create and manage collections with specific embedding models
- List collections with filtering by embedding model and active status
- Update collection metadata (description, is_active flag)
- Delete empty collections (protection against accidental data loss)
- Get collection statistics (document count, chunk count, size)
- Public endpoint for use case configuration

**Architecture Reference:** [ADR-021: Collection-Based Document Management (Addendum 3)](../development/adrs/ADR-021-Collection-Based-Document-Management.md)

---

## Authentication

All admin endpoints require admin or corpus_admin authentication. Public endpoints require any authenticated user.

```bash
Authorization: Bearer <access_token>
```

**Get Admin Token:**

```bash
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')
```

---

## Admin Endpoints

### 1. List Collections (Admin)

**GET** `/api/v1/admin/collections/`

List all collections with optional filtering and pagination. Admin endpoint returns full details including document counts.

**Query Parameters:**

- `active_only` (boolean, default: true) - Only return active collections
- `embedding_model` (string, optional) - Filter by embedding model
- `skip` (integer, default: 0, min: 0) - Number of items to skip
- `limit` (integer, default: 100, min: 1, max: 1000) - Maximum items to return

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/collections/?active_only=true&embedding_model=all-minilm-l6-v2" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "collections": [
    {
      "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
      "name": "threat_intelligence",
      "description": "Threat intelligence reports and IOC data",
      "embedding_model": "all-minilm-l6-v2",
      "embedding_provider": "sentence-transformers",
      "embedding_dimensions": 384,
      "qdrant_collection_name": "collection_threat_intelligence",
      "is_default": false,
      "is_active": true,
      "is_system_managed": false,
      "created_by": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-10-15T10:00:00Z",
      "updated_at": "2025-10-15T10:00:00Z",
      "document_count": 127
    },
    {
      "id": "c8d4f3b2-1234-5678-9abc-def012345678",
      "name": "general_knowledge",
      "description": "General cybersecurity knowledge base",
      "embedding_model": "all-minilm-l6-v2",
      "embedding_provider": "sentence-transformers",
      "embedding_dimensions": 384,
      "qdrant_collection_name": "collection_general_knowledge",
      "is_default": true,
      "is_active": true,
      "is_system_managed": true,
      "created_by": "system",
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z",
      "document_count": 453
    }
  ],
  "total": 2
}
```

**Status Codes:**

- `200 OK` - Collections retrieved successfully
- `403 Forbidden` - Insufficient permissions (requires admin or corpus_admin)
- `500 Internal Server Error` - Server error

---

### 2. Create Collection

**POST** `/api/v1/admin/collections/`

Create a new collection with specified embedding model. The embedding model is **immutable after creation**.

**⚠️ Model Validation (NEW - Oct 27, 2025):**
- Backend validates `embedding_model` exists in Model Registry
- Checks model `is_available=true` and `model_type='embedding'`
- Returns 400 error if model unavailable or not found
- Provider and dimensions normalized from registry (authoritative source)

**Request Body:**

```json
{
  "name": "malware_reports",
  "description": "Malware analysis reports and threat assessments",
  "embedding_model": "all-minilm-l6-v2",
  "embedding_provider": "sentence-transformers",
  "embedding_dimensions": 384
}
```

**Field Requirements:**

- `name` - **Required**, 3-255 characters, unique across collections
- `description` - Optional, max 1000 characters
- `embedding_model` - **Required**, 1-255 characters (must match available model)
- `embedding_provider` - **Required**, 1-100 characters
- `embedding_dimensions` - **Required**, integer > 0 (must match model dimensions)

**Example Request:**

```bash
curl -X POST "http://localhost:8006/api/v1/admin/collections/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "malware_reports",
    "description": "Malware analysis reports",
    "embedding_model": "all-minilm-l6-v2",
    "embedding_provider": "sentence-transformers",
    "embedding_dimensions": 384
  }'
```

**Response:**

```json
{
  "id": "d9e5f4c3-2345-6789-bcde-f01234567890",
  "name": "malware_reports",
  "description": "Malware analysis reports",
  "embedding_model": "all-minilm-l6-v2",
  "embedding_provider": "sentence-transformers",
  "embedding_dimensions": 384,
  "qdrant_collection_name": "collection_malware_reports",
  "is_default": false,
  "is_active": true,
  "is_system_managed": false,
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-10-18T15:00:00Z",
  "updated_at": "2025-10-18T15:00:00Z",
  "document_count": 0
}
```

**Status Codes:**

- `201 Created` - Collection created successfully
- `400 Bad Request` - Invalid request data, embedding model unavailable, or embedding model mismatch
- `409 Conflict` - Collection name already exists
- `403 Forbidden` - Insufficient permissions
- `503 Service Unavailable` - Retrieval service unavailable

**Error Examples:**

```json
// Model not available
{
  "detail": "Embedding model 'text-embedding-3-small' is not available. Choose an available embedding model."
}

// Model not found
{
  "detail": "Embedding model 'invalid-model' is not available. Choose an available embedding model."
}
```

**Business Rules:**

- Collection name must be unique
- Embedding model is **immutable** after creation
- **Model validation (Oct 27, 2025):**
  - Model must exist in Model Registry with `model_type='embedding'`
  - Model must have `is_available=true`
  - Provider and dimensions are normalized from registry (client values ignored)
- Qdrant collection is automatically created with naming convention: `collection_{name}`
- New collections start active by default (`is_active: true`)
- **Multi-Collection Search Constraint:**
  - Use Cases can search multiple collections ONLY if they share the same embedding model
  - Backend enforces this constraint and returns 400 error if violated

---

### 3. Get Collection Details

**GET** `/api/v1/admin/collections/{collection_id}`

Retrieve detailed information for a specific collection.

**Path Parameters:**

- `collection_id` (UUID) - Collection UUID

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/collections/ba0c6e49-2813-4887-8970-e0c1753234f7" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:** Same structure as Create Collection response

**Status Codes:**

- `200 OK` - Collection retrieved successfully
- `404 Not Found` - Collection not found
- `403 Forbidden` - Insufficient permissions

---

### 4. Update Collection

**PUT** `/api/v1/admin/collections/{collection_id}`

Update collection metadata. Only `description` and `is_active` fields can be updated. Embedding model is **immutable**.

**Path Parameters:**

- `collection_id` (UUID) - Collection UUID

**Request Body (all fields optional):**

```json
{
  "description": "Updated description for the collection",
  "is_active": false
}
```

**Example Request:**

```bash
curl -X PUT "http://localhost:8006/api/v1/admin/collections/ba0c6e49-2813-4887-8970-e0c1753234f7" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated: Threat intelligence reports with enhanced IOC coverage",
    "is_active": true
  }'
```

**Response:** Updated CollectionResponse

**Status Codes:**

- `200 OK` - Collection updated successfully
- `400 Bad Request` - Invalid update data
- `404 Not Found` - Collection not found
- `403 Forbidden` - Insufficient permissions

**Business Rules:**

- `embedding_model`, `embedding_provider`, `embedding_dimensions` are immutable
- `name` is immutable (would break Qdrant collection mapping)
- `is_system_managed` collections may have restrictions on updates

---

### 5. Delete Collection

**DELETE** `/api/v1/admin/collections/{collection_id}`

Delete a collection. Collection must be empty (no documents) and cannot be system-managed.

**Path Parameters:**

- `collection_id` (UUID) - Collection UUID

**Example Request:**

```bash
curl -X DELETE "http://localhost:8006/api/v1/admin/collections/ba0c6e49-2813-4887-8970-e0c1753234f7" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```
204 No Content
```

**Status Codes:**

- `204 No Content` - Collection deleted successfully
- `400 Bad Request` - Collection not empty or is system-managed
- `404 Not Found` - Collection not found
- `403 Forbidden` - Insufficient permissions

**Business Rules:**

- Collection must have `document_count == 0` to delete
- System-managed collections (`is_system_managed: true`) cannot be deleted
- Deleting a collection also deletes the associated Qdrant collection
- **Safety:** No cascade delete - must remove all documents first

**Pre-deletion Checklist:**

```bash
# 1. Check document count
curl -X GET "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID/stats" \
  -H "Authorization: Bearer $TOKEN" | jq '.document_count'

# 2. If count > 0, cannot delete (must remove documents first)

# 3. If count == 0, safe to delete
curl -X DELETE "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Get Collection Statistics

**GET** `/api/v1/admin/collections/{collection_id}/stats`

Retrieve detailed statistics for a collection including document count, chunk count, and total size.

**Path Parameters:**

- `collection_id` (UUID) - Collection UUID

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/collections/ba0c6e49-2813-4887-8970-e0c1753234f7/stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
  "name": "threat_intelligence",
  "document_count": 127,
  "total_chunks": 3842,
  "total_size_bytes": 15728640,
  "last_updated": "2025-10-18T14:30:00Z"
}
```

**Status Codes:**

- `200 OK` - Statistics retrieved successfully
- `404 Not Found` - Collection not found
- `403 Forbidden` - Insufficient permissions

**Metrics Provided:**

- `document_count` - Number of documents in collection
- `total_chunks` - Total number of text chunks (vectors in Qdrant)
- `total_size_bytes` - Total storage size of all documents (compressed)
- `last_updated` - Timestamp of last document addition/update

---

## Public Endpoints

### 7. List Available Collections

**GET** `/api/v1/admin/collections/available`

List active collections available for use case configuration. Returns minimal information needed for collection selection.

**Authentication:** Required (any authenticated user)

**Query Parameters:** None (automatically filters to active collections only)

**Example Request:**

```bash
curl -X GET "http://localhost:8006/api/v1/admin/collections/available" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**

```json
{
  "collections": [
    {
      "id": "ba0c6e49-2813-4887-8970-e0c1753234f7",
      "name": "threat_intelligence",
      "description": "Threat intelligence reports and IOC data",
      "embedding_model": "all-minilm-l6-v2",
      "embedding_provider": "sentence-transformers",
      "embedding_dimensions": 384,
      "qdrant_collection_name": "collection_threat_intelligence",
      "is_default": false,
      "is_active": true,
      "is_system_managed": false,
      "created_by": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-10-15T10:00:00Z",
      "updated_at": "2025-10-15T10:00:00Z",
      "document_count": 127
    }
  ],
  "total": 5
}
```

**Status Codes:**

- `200 OK` - Collections retrieved successfully
- `401 Unauthorized` - Not authenticated

**Use Case:**
This endpoint is used by:

- Use Case configuration UI (selecting which collections to search)
- Document upload UI (selecting target collection)
- RAG configuration forms

---

## Data Models

### CollectionResponse

Complete collection details.

```typescript
interface CollectionResponse {
  id: string;                     // UUID
  name: string;                   // Unique collection name
  description: string | null;     // Optional description
  embedding_model: string;        // Embedding model ID (IMMUTABLE)
  embedding_provider: string;     // Provider name (IMMUTABLE)
  embedding_dimensions: number;   // Vector dimensions (IMMUTABLE)
  qdrant_collection_name: string; // Qdrant collection name (auto-generated)
  is_default: boolean;            // Default collection flag
  is_active: boolean;             // Active status
  is_system_managed: boolean;     // System-managed flag (cannot delete)
  created_by: string;             // Creator UUID
  created_at: string;             // ISO 8601 timestamp
  updated_at: string;             // ISO 8601 timestamp
  document_count: number;         // Number of documents in collection
}
```

### CollectionCreate

Request to create a new collection.

```typescript
interface CollectionCreate {
  name: string;                   // 3-255 characters, unique
  description?: string;           // Max 1000 characters
  embedding_model: string;        // Model identifier (1-255 chars)
  embedding_provider: string;     // Provider name (1-100 chars)
  embedding_dimensions: number;   // Must match model dimensions
}
```

### CollectionUpdate

Request to update collection metadata.

```typescript
interface CollectionUpdate {
  description?: string;           // Updated description
  is_active?: boolean;            // Updated active status
}
```

### CollectionStats

Collection statistics.

```typescript
interface CollectionStats {
  id: string;                     // UUID
  name: string;                   // Collection name
  document_count: number;         // Total documents
  total_chunks: number;           // Total text chunks (vectors)
  total_size_bytes: number;       // Total storage size (compressed)
  last_updated: string;           // ISO 8601 timestamp
}
```

---

## Architecture

### Collection-Based Isolation

Collections provide **logical isolation** for documents:

```
Collection: threat_intelligence (embedding: all-minilm-l6-v2, 384 dims)
  ├── Document 1: "APT29 Threat Report" → 45 chunks
  ├── Document 2: "IOC Database Q3 2025" → 123 chunks
  └── Document 3: "MITRE ATT&CK Mapping" → 67 chunks
      ↓ (Cannot mix with different embedding model)

Collection: malware_samples (embedding: bge-large-en-v1.5, 1024 dims)
  ├── Document 4: "Malware Analysis Report" → 89 chunks
  └── Document 5: "Ransomware Patterns" → 112 chunks
```

**Key Constraint:** All documents in a collection must use the **same embedding model**.

### Integration with Use Cases

Use Cases reference collections in their RAG configuration:

```json
// In use_case.config_json
{
  "models": {
    "embedding": "all-minilm-l6-v2"  // Must match collection(s)
  },
  "rag": {
    "enabled": true,
    "vector_collections": ["threat_intelligence", "general_knowledge"]
  }
}
```

**Validation Rules:**

- ✅ All referenced collections must exist
- ✅ All referenced collections must use the same embedding model
- ✅ Use case's `models.embedding` must match collection(s) embedding model
- ❌ Cannot mix collections with different embedding models in one use case

See [ADR-021](../development/adrs/ADR-021-Collection-Based-Document-Management.md) for complete architecture details.

---

## Common Workflows

### Create New Collection for Specific Purpose

```bash
# 1. Determine embedding model (must match documents you'll upload)
EMBEDDING_MODEL="all-minilm-l6-v2"
EMBEDDING_DIMS=384

# 2. Create collection
COLLECTION=$(curl -s -X POST "http://localhost:8006/api/v1/admin/collections/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"incident_reports\",
    \"description\": \"Security incident reports and post-mortems\",
    \"embedding_model\": \"$EMBEDDING_MODEL\",
    \"embedding_provider\": \"sentence-transformers\",
    \"embedding_dimensions\": $EMBEDDING_DIMS
  }" | jq -r '.id')

echo "Created collection: $COLLECTION"

# 3. Upload documents to collection
# (Documents will automatically be assigned to this collection)

# 4. Configure use case to search this collection
# Add "incident_reports" to use_case.config_json.rag.vector_collections
```

---

### Deactivate Collection Temporarily

```bash
# Deactivate collection (documents remain, but not searchable)
curl -X PUT "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Later: Reactivate
curl -X PUT "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

**Use Case:**

- Temporarily disable a collection during maintenance
- Test queries without certain collections
- Prevent searches in outdated/unreliable collections

---

### Delete Collection Safely

```bash
# 1. Check if collection is empty
STATS=$(curl -s -X GET "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID/stats" \
  -H "Authorization: Bearer $TOKEN")

DOC_COUNT=$(echo $STATS | jq -r '.document_count')

if [ "$DOC_COUNT" -eq "0" ]; then
  echo "Collection is empty, safe to delete"

  # 2. Delete collection
  curl -X DELETE "http://localhost:8006/api/v1/admin/collections/$COLLECTION_ID" \
    -H "Authorization: Bearer $TOKEN"

  echo "Collection deleted"
else
  echo "Collection has $DOC_COUNT documents - cannot delete"
  echo "Remove all documents first, then retry"
fi
```

---

### List Collections by Embedding Model

```bash
# Find all collections using a specific embedding model
curl -X GET "http://localhost:8006/api/v1/admin/collections/?embedding_model=all-minilm-l6-v2" \
  -H "Authorization: Bearer $TOKEN" | jq '.collections[] | {name, document_count}'
```

**Use Case:**

- Planning use case RAG configuration (which collections can be combined)
- Identifying collections that need migration to new embedding model
- Resource planning (embedding model load balancing)

---

## Error Handling

### Common Error Scenarios

#### 1. Embedding Model Mismatch

**Scenario:** Trying to combine collections with different embedding models in a use case.

**Error:**

```json
{
  "detail": "All collections in vector_collections must use the same embedding model"
}
```

**Resolution:** Only reference collections with matching embedding models.

---

#### 2. Cannot Delete Non-Empty Collection

**Scenario:** Attempting to delete a collection that has documents.

**Error:**

```json
{
  "detail": "Cannot delete collection 'threat_intelligence': contains 127 documents. Remove all documents first."
}
```

**Resolution:**

1. Remove all documents from collection
2. Verify `document_count == 0`
3. Retry deletion

---

#### 3. System-Managed Collection Protection

**Scenario:** Attempting to delete or modify a system-managed collection.

**Error:**

```json
{
  "detail": "Cannot delete system-managed collection 'general_knowledge'"
}
```

**Resolution:** System-managed collections (like default collections) cannot be deleted. Deactivate instead if needed.

---

#### 4. Collection Name Conflict

**Scenario:** Creating a collection with a name that already exists.

**Error:**

```json
{
  "detail": "Collection with name 'threat_intelligence' already exists"
}
```

**Resolution:** Choose a different collection name.

---

## Multi-Collection RAG Queries

### How Collections Work with Use Cases

When a use case is executed with RAG enabled, the system:

1. **Loads collection configuration** from `config_json.rag.vector_collections`
2. **Validates embedding model consistency** across all collections
3. **Queries each collection** in parallel using the specified `top_k`
4. **Merges results** by similarity score
5. **Returns top_k total chunks** across all collections

**Example:**

```json
// Use Case Config
{
  "models": {
    "embedding": "all-minilm-l6-v2"
  },
  "rag": {
    "enabled": true,
    "vector_collections": ["threat_intelligence", "general_knowledge", "incident_reports"],
    "top_k": 10,
    "similarity_threshold": 0.7
  }
}
```

**Query Behavior:**

- Queries all 3 collections in parallel
- Each returns up to `top_k` chunks
- Combined results sorted by similarity
- Top 10 chunks selected across all collections
- Only chunks with similarity >= 0.7 are included

---

## Proxy Architecture

**Important:** The Collection Management API is a **proxy** to the Retrieval Service.

```
Client Request
  ↓
Orchestrator API (/api/v1/admin/collections)
  ↓ [HTTP Proxy]
Retrieval Service (/api/v1/admin/collections)
  ↓
Qdrant Vector Database
```

**Why Proxy:**

- Unified API surface (all requests go through orchestrator)
- Centralized authentication and authorization
- Consistent error handling and logging
- Simplified client architecture (one base URL)

**Implications:**

- Both services must be running for collection management
- Authentication token forwarded to retrieval service
- Response schemas defined in orchestrator, implemented in retrieval
- Network latency: orchestrator ↔ retrieval (~5-10ms)

---

## Related Documentation

- **Architecture Decision:** [ADR-021: Collection-Based Document Management](../development/adrs/ADR-021-Collection-Based-Document-Management.md)
- **Implementation Summary:** [P2-F3-ENHANCED-Collection-Management.md](../development/completed/tasks/P2-F3-ENHANCED-Collection-Management.md)
- **Session Log:** [2025-10-17-collection-based-document-management.md](../development/sessions/2025-10-17-collection-based-document-management.md)
- **Use Case Integration:** [use-case-management.md](./use-case-management.md) (RAG config section)
- **Document Upload:** [documents.md](./documents.md) (collection selection during upload)

---

## Testing

### Manual Testing

```bash
# Get admin token
TOKEN=$(curl -s -X POST "http://localhost:8006/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=adminpassword" | jq -r '.access_token')

# 1. List all collections
curl -X GET "http://localhost:8006/api/v1/admin/collections/" \
  -H "Authorization: Bearer $TOKEN" | jq '.collections[] | {name, document_count}'

# 2. Create test collection
TEST_COLLECTION=$(curl -s -X POST "http://localhost:8006/api/v1/admin/collections/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_collection",
    "description": "Test collection for API verification",
    "embedding_model": "all-minilm-l6-v2",
    "embedding_provider": "sentence-transformers",
    "embedding_dimensions": 384
  }' | jq -r '.id')

# 3. Get collection details
curl -X GET "http://localhost:8006/api/v1/admin/collections/$TEST_COLLECTION" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 4. Update collection
curl -X PUT "http://localhost:8006/api/v1/admin/collections/$TEST_COLLECTION" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated test collection description"
  }' | jq '.'

# 5. Get statistics
curl -X GET "http://localhost:8006/api/v1/admin/collections/$TEST_COLLECTION/stats" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 6. Delete collection (only if empty)
curl -X DELETE "http://localhost:8006/api/v1/admin/collections/$TEST_COLLECTION" \
  -H "Authorization: Bearer $TOKEN"
```

### Integration Tests

**Test Suite:** `tests/integration/test_collection_management.py`
**Coverage:** Create, list, update, delete, stats, available endpoint

---

## Best Practices

### 1. Collection Naming

**Good Names:**

- `threat_intelligence` - Clear purpose
- `malware_reports` - Descriptive content
- `incident_postmortems` - Specific use case

**Avoid:**

- `collection1` - Non-descriptive
- `test` - Too generic
- `temp` - Implies temporary data

### 2. Embedding Model Selection

**Considerations:**

- **Model dimensions:** Higher dimensions = more storage, potentially better accuracy
- **Model performance:** Embedding speed affects document processing time
- **Model compatibility:** Must match embedding service capabilities

**Available Models (October 2025):**

- `all-minilm-l6-v2` (384 dims) - Fast, good quality, recommended default
- `bge-large-en-v1.5` (1024 dims) - Higher quality, slower
- `text-embedding-ada-002` (1536 dims) - OpenAI, requires API key

### 3. Collection Organization Strategies

**By Data Source:**

- `mitre_attack` - MITRE ATT&CK framework
- `nist_guides` - NIST cybersecurity guides
- `vendor_docs` - Vendor security documentation

**By Purpose:**

- `threat_intelligence` - Threat intel and IOC data
- `malware_analysis` - Malware reports and samples
- `compliance` - Compliance and regulatory docs

**By Classification:**

- `public_knowledge` - Publicly available data
- `internal_docs` - Internal documentation
- `confidential_reports` - Restricted access reports

**Recommendation:** Choose organization strategy based on **RBAC requirements** and **use case needs**.

---

## Security Considerations

### Access Control

- ✅ Admin and corpus_admin roles required for management operations
- ✅ All authenticated users can list available collections
- ✅ JWT token validation on every request
- ✅ Role enforcement at orchestrator and retrieval service levels

### Data Protection

- ✅ Deletion requires empty collection (prevents accidental data loss)
- ✅ System-managed collections protected from deletion
- ✅ Embedding model immutable (prevents accidental schema drift)
- ✅ Audit trail for all collection operations

### Multi-Tenancy

- Collections can be used for **tenant isolation**
- Use `center_id` or custom metadata for tenant-specific collections
- RBAC controls which users can access which collections

---

## Performance Considerations

### Collection Size Impact

| Document Count | Chunks | Query Time | Recommendation |
|----------------|--------|------------|----------------|
| < 1,000 | < 30K | < 50ms | Optimal performance |
| 1,000 - 10,000 | 30K - 300K | 50-200ms | Good performance |
| 10,000 - 100,000 | 300K - 3M | 200-500ms | Monitor performance |
| > 100,000 | > 3M | > 500ms | Consider splitting |

**Optimization Strategies:**

- Use `similarity_threshold` to limit result sets
- Combine collections judiciously (more collections = more queries)
- Monitor query performance with collection stats
- Split very large collections by time period or sub-category

---

## Troubleshooting

### Issue: "Retrieval service unavailable"

**Symptoms:**

```json
{
  "detail": "Retrieval service unavailable"
}
```

**Causes:**

- Retrieval service not running
- Network connectivity issues
- Qdrant database unavailable

**Resolution:**

```bash
# Check service health
docker ps | grep retrieval
docker logs corpus-service

# Check Qdrant
curl http://localhost:6335/collections
```

---

### Issue: "Embedding model mismatch"

**Symptoms:**

```json
{
  "detail": "Use case embedding model 'bge-large-en-v1.5' does not match collection 'threat_intelligence' embedding model 'all-minilm-l6-v2'"
}
```

**Cause:** Use case references collections with incompatible embedding models.

**Resolution:**

1. Use collections with matching embedding models
2. OR create new collection with desired embedding model
3. OR change use case embedding model to match collections

---

## Migration Scenarios

### Changing Embedding Models

**Problem:** Want to upgrade all collections to a new embedding model.

**Solution:**
Collections have **immutable embedding models** by design. Must create new collections:

```bash
# 1. Create new collection with new model
NEW_COLLECTION=$(curl -s -X POST "http://localhost:8006/api/v1/admin/collections/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "threat_intelligence_v2",
    "description": "Threat intel with upgraded embedding model",
    "embedding_model": "bge-large-en-v1.5",
    "embedding_provider": "BAAI",
    "embedding_dimensions": 1024
  }' | jq -r '.id')

# 2. Re-upload documents to new collection
# (Embedding service will use new model)

# 3. Update use cases to use new collection
# Change vector_collections: ["threat_intelligence"] → ["threat_intelligence_v2"]

# 4. After migration complete, deactivate old collection
curl -X PUT "http://localhost:8006/api/v1/admin/collections/$OLD_COLLECTION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_active": false}'

# 5. Eventually delete old collection (after document removal)
```

---

## FAQ

### Q: Can I rename a collection?

**A:** No, collection names are immutable. The name is used to generate the Qdrant collection name (`collection_{name}`). To "rename":

1. Create new collection with desired name
2. Migrate documents
3. Update use cases to reference new collection
4. Delete old collection

### Q: Can I change the embedding model for a collection?

**A:** No, embedding models are immutable. Documents in a collection are already embedded with the original model. To change:

1. Create new collection with new embedding model
2. Re-upload and re-embed documents
3. Update use cases
4. Delete old collection

### Q: What's the difference between `is_active` and `lifecycle_state`?

**A:** Collections use `is_active` (boolean flag). Use Cases use `lifecycle_state` (draft/review/published/archived). Collections don't have lifecycle management - they're either active or inactive.

### Q: Can I search multiple collections with different embedding models?

**A:** No, this would create incompatible vector spaces. All collections in a use case's `vector_collections` must use the same embedding model.

### Q: What happens to documents when I deactivate a collection?

**A:** Documents remain in the collection, but the collection won't appear in search results or available collections lists. Reactivating makes them searchable again immediately.

---

**Last Updated:** October 18, 2025
**API Version:** 1.0
**Implementation Status:** Implemented
