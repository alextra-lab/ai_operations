# Corpus Management API

**Version:** 1.0
**Last Updated:** November 1, 2025
**ADR Reference:** ADR-021 Collection-Based Document Management (Addendum 3)

## Overview

The Corpus Management API provides intelligent document processing, chunking strategy selection, and retrieval quality validation. This API implements enhanced corpus management for the Stateless Core v1 architecture.

**Key Features:**
- **7 chunking strategies** - Fixed, sliding, heading-aware, sentence, table, semantic, page-block
- **Preflight analysis** - Intelligent strategy recommendation
- **Test suites** - Retrieval quality validation (Hit@K, MRR, nDCG)
- **Exemplar management** - Few-shot example selection
- **Ephemeral collections** - TTL-based temporary document storage

## Endpoints

### Chunking

#### Chunk Document

Process a document using a specific chunking strategy.

**Endpoint:** `POST /api/v1/corpus/chunk`
**Authentication:** Required (JWT)

**Request:**
```json
{
  "text": "Document content to chunk...",
  "config": {
    "strategy": "heading_aware",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "min_chunk_size": 100,
    "max_chunk_size": 1024
  },
  "document_id": "doc-123"
}
```

**Response:** (200 OK)
```json
{
  "strategy": "heading_aware",
  "chunks": [
    "Chunk 1 content...",
    "Chunk 2 content..."
  ],
  "chunk_count": 2,
  "total_tokens": 856,
  "avg_chunk_size": 428.0,
  "processing_time_ms": 45,
  "metadata": {
    "document_id": "doc-123",
    "strategy": "heading_aware"
  }
}
```

#### Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `fixed_token` | Fixed-size token blocks | General documents |
| `sliding_token` | Overlapping token windows | Dense content |
| `heading_aware` | Split by headings (H1-H3) | Structured documents |
| `sentence_paragraph` | Natural language boundaries | Narrative text |
| `table_aware` | Preserve table structure | Tabular data |
| `semantic_adaptive` | Similarity-based splits (beta) | Research papers |
| `page_block` | PDF layout blocks (beta) | PDF documents |

### Preflight Analysis

#### Analyze Document

Analyze a document and recommend optimal chunking strategy.

**Endpoint:** `POST /api/v1/corpus/preflight`
**Authentication:** Required (JWT)

**Request:**
```json
{
  "text": "Document content...",
  "document_name": "security_policy.md",
  "collection_id": "uuid-here",
  "test_suite_id": "suite-uuid"
}
```

**Response:** (200 OK)
```json
{
  "document_id": "generated-uuid",
  "structure_signals": {
    "heading_density": 0.15,
    "table_ratio": 0.05,
    "avg_paragraph_length": 342.5,
    "sentence_count": 127,
    "has_code_blocks": false,
    "ocr_confidence": null
  },
  "strategy_results": [
    {
      "strategy": "heading_aware",
      "chunk_count": 12,
      "avg_chunk_size": 456.3,
      "quality_score": 0.92,
      "hit_at_5": 0.85,
      "mrr": 0.78,
      "ndcg_at_5": 0.81
    },
    {
      "strategy": "fixed_token",
      "chunk_count": 18,
      "avg_chunk_size": 512.0,
      "quality_score": 0.76,
      "hit_at_5": 0.72,
      "mrr": 0.65,
      "ndcg_at_5": 0.69
    }
  ],
  "recommended_strategy": "heading_aware",
  "confidence": 0.92
}
```

### Collections

#### Create Collection

Create a document collection with specific embedding model.

**Endpoint:** `POST /api/v1/collections`
**Authentication:** Required (JWT)

**Request:**
```json
{
  "name": "Security Policies",
  "description": "Company security policy documents",
  "embedding_model": "all-MiniLM-L6-v2",
  "is_ephemeral": false,
  "ttl_days": null
}
```

**Response:** (201 Created)
```json
{
  "id": "collection-uuid",
  "name": "Security Policies",
  "description": "Company security policy documents",
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_dimensions": 384,
  "is_ephemeral": false,
  "ttl_days": null,
  "expires_at": null,
  "document_count": 0,
  "created_at": "2025-11-01T10:00:00Z"
}
```

#### Create Ephemeral Collection

Create a temporary collection with TTL.

**Request:**
```json
{
  "name": "Conversation Attachments",
  "description": "Temporary documents for conversation",
  "embedding_model": "all-MiniLM-L6-v2",
  "is_ephemeral": true,
  "ttl_days": 1,
  "conversation_id": "conversation-uuid"
}
```

**Response:** (201 Created)
```json
{
  "id": "ephemeral-collection-uuid",
  "is_ephemeral": true,
  "ttl_days": 1,
  "expires_at": "2025-11-02T10:00:00Z"
}
```

### Test Suites

#### Create Test Suite

Create a test suite for retrieval quality validation.

**Endpoint:** `POST /api/v1/corpus/test-suites`
**Authentication:** Required (JWT)

**Request:**
```json
{
  "name": "Security Policy Tests",
  "description": "Test suite for security policy retrieval",
  "collection_ids": ["collection-uuid-1", "collection-uuid-2"],
  "k": 5,
  "questions": [
    {
      "query": "What are password requirements?",
      "expected_doc_ids": ["doc-uuid-1"],
      "expected_phrases": ["minimum 12 characters", "special character"],
      "tags": ["authentication", "password"]
    },
    {
      "query": "What is the data retention policy?",
      "expected_doc_ids": ["doc-uuid-2"],
      "expected_phrases": ["90 days", "archived"],
      "tags": ["compliance", "retention"]
    }
  ]
}
```

**Response:** (201 Created)
```json
{
  "id": "suite-uuid",
  "name": "Security Policy Tests",
  "description": "Test suite for security policy retrieval",
  "collection_ids": ["collection-uuid-1", "collection-uuid-2"],
  "k": 5,
  "question_count": 2,
  "created_at": "2025-11-01T10:00:00Z"
}
```

#### Execute Test Suite

Run test suite and compute retrieval metrics.

**Endpoint:** `POST /api/v1/corpus/test-suites/{suite_id}/execute`
**Authentication:** Required (JWT)

**Response:** (200 OK)
```json
{
  "suite_id": "suite-uuid",
  "execution_id": "exec-uuid",
  "executed_at": "2025-11-01T10:05:00Z",
  "metrics": {
    "hit_at_1": 0.85,
    "hit_at_3": 0.92,
    "hit_at_5": 0.96,
    "mrr": 0.88,
    "ndcg_at_5": 0.91,
    "zero_result_rate": 0.02
  },
  "question_results": [
    {
      "question_id": "q1",
      "query": "What are password requirements?",
      "hit": true,
      "rank": 1,
      "retrieved_docs": ["doc-uuid-1", "doc-uuid-3"],
      "expected_found": 1
    }
  ]
}
```

### Retrieval Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Hit@K | % of queries with ≥1 relevant doc in top K | ≥ 90% |
| MRR | Mean reciprocal rank of first relevant doc | ≥ 0.8 |
| nDCG@K | Normalized discounted cumulative gain | ≥ 0.85 |
| Zero Result Rate | % of queries with no results | ≤ 5% |

## Usage Examples

### TypeScript/Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChunkingConfig {
  strategy: string;
  chunk_size: number;
  chunk_overlap: number;
}

export interface ChunkingResult {
  chunks: string[];
  chunk_count: number;
  avg_chunk_size: number;
}

@Injectable({ providedIn: 'root' })
export class CorpusService {
  private apiUrl = '/api/v1/corpus';

  constructor(private http: HttpClient) {}

  chunkDocument(text: string, config: ChunkingConfig): Observable<ChunkingResult> {
    return this.http.post<ChunkingResult>(`${this.apiUrl}/chunk`, {
      text,
      config
    });
  }

  analyzeDocument(text: string, documentName: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/preflight`, {
      text,
      document_name: documentName
    });
  }

  createTestSuite(suite: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/test-suites`, suite);
  }

  executeTestSuite(suiteId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/test-suites/${suiteId}/execute`, {});
  }
}
```

### Python

```python
import httpx
from typing import Dict, List

class CorpusClient:
    """Client for Corpus Management API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def chunk_document(
        self,
        text: str,
        strategy: str = "heading_aware",
        chunk_size: int = 512
    ) -> Dict:
        """Chunk a document with specified strategy."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/corpus/chunk",
                headers=self.headers,
                json={
                    "text": text,
                    "config": {
                        "strategy": strategy,
                        "chunk_size": chunk_size,
                        "chunk_overlap": int(chunk_size * 0.1)
                    }
                }
            )
            response.raise_for_status()
            return response.json()

    async def analyze_and_chunk(self, text: str, document_name: str) -> Dict:
        """Analyze document and use recommended strategy."""
        # Get recommendation
        preflight = await self.preflight_analysis(text, document_name)
        recommended_strategy = preflight["recommended_strategy"]

        # Chunk with recommended strategy
        return await self.chunk_document(text, strategy=recommended_strategy)

    async def preflight_analysis(
        self,
        text: str,
        document_name: str
    ) -> Dict:
        """Analyze document and get chunking recommendations."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/corpus/preflight",
                headers=self.headers,
                json={
                    "text": text,
                    "document_name": document_name
                }
            )
            response.raise_for_status()
            return response.json()

# Usage
client = CorpusClient("http://localhost:8006", "jwt_token_here")

# Intelligent chunking
text = open("security_policy.md").read()
result = await client.analyze_and_chunk(text, "security_policy.md")
print(f"Chunks: {result['chunk_count']}")
print(f"Strategy: {result['strategy']}")
```

## Best Practices

### 1. Use Preflight for New Documents

```python
# Good: Let preflight recommend strategy
preflight = await client.preflight_analysis(text, filename)
strategy = preflight["recommended_strategy"]
chunks = await client.chunk_document(text, strategy=strategy)

# Bad: Always use same strategy
chunks = await client.chunk_document(text, strategy="fixed_token")
```

### 2. Validate with Test Suites

```typescript
// Create test suite for each collection
const suite = await corpus.createTestSuite({
  name: 'Policy Retrieval Tests',
  collection_ids: [collectionId],
  questions: testQuestions
});

// Run regularly to monitor quality
const results = await corpus.executeTestSuite(suite.id);
if (results.metrics.hit_at_5 < 0.9) {
  alert('Retrieval quality degraded');
}
```

### 3. Clean Up Ephemeral Collections

```python
# Use ephemeral collections for temporary data
ephemeral = await client.create_collection(
    name="Temp Analysis",
    is_ephemeral=True,
    ttl_days=1
)

# Automatic cleanup after TTL expires
```

## Limitations

| Limit | Value | Notes |
|-------|-------|-------|
| Max document size | 10 MB | For preflight analysis |
| Max chunks per document | 10,000 | Practical limit |
| Test suite max questions | 1,000 | Per suite |
| Ephemeral collection TTL | 1-30 days | Configurable |

## Related Documentation

- [ADR-021: Collection-Based Document Management](../development/adrs/ADR-021-Collection-Based-Document-Management.md)
- [ADR-034: Use Case Validation Harness](../development/adrs/ADR-034-Use-Case-Validation-Harness.md)
- [Chunking Strategies Guide](../user-guides/CHUNKING_STRATEGIES.md)
- [Test Suite User Guide](../user-guides/TEST_SUITES.md)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial release for Stateless Core v1 |
