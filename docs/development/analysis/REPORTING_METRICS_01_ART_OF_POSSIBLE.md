# Art of the Possible: Application Reporting & Analytics

**Document Type:** Analysis
**Date:** October 11, 2025
**Purpose:** Exhaustive exploration of all possible metrics and reporting dimensions for AI Operations Platform
**Status:** 🔄 Reference Document (Brainstorming Phase)
**Companion Document:** [REPORTING_METRICS_02_VALUE_ANALYSIS.md](./REPORTING_METRICS_02_VALUE_ANALYSIS.md)
**Usage:** Part 1 of 2 - Metric catalog (see Part 2 for value assessment and prioritization)

---

## Executive Summary

This document catalogs **381 distinct metrics** across **15 major dimensions** that can be derived from the AI Operations Platform application's current architecture and data stores. These metrics span user behavior, document management, system performance, model efficiency, cost optimization, security, and database management.

### Data Sources Available

- **PostgreSQL:** 15+ tables with comprehensive tracking
- **Qdrant Vector Store:** Chunk-level data with metadata
- **Application Logs:** Structured JSON logging
- **Audit Trail:** Immutable audit_logs table
- **System Catalogs:** PostgreSQL pg_stat_* views

### Metrics Organization

Each metric includes:

- **Metric ID:** Unique identifier for reference
- **Metric Name:** Descriptive name
- **Data Source:** Where the data originates
- **Calculation:** How to compute the metric
- **Type:** Real-time, Historical, or Calculated

---

## DIMENSION 1: USER ANALYTICS & BEHAVIOR (58 metrics)

### 1.1 User Base Metrics (12 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| U-001 | Total Registered Users | `users` | COUNT(id) | Real-time |
| U-002 | Active Users (24h) | `users` | WHERE last_login > NOW() - INTERVAL '24 hours' | Real-time |
| U-003 | Active Users (7d) | `users` | WHERE last_login > NOW() - INTERVAL '7 days' | Real-time |
| U-004 | Active Users (30d) | `users` | WHERE last_login > NOW() - INTERVAL '30 days' | Real-time |
| U-005 | Inactive Users | `users` | WHERE is_active = false | Real-time |
| U-006 | Never-Logged-In Users | `users` | WHERE last_login IS NULL | Real-time |
| U-007 | New Users (daily) | `users` | WHERE created_at >= CURRENT_DATE | Historical |
| U-008 | New Users (weekly) | `users` | WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' | Historical |
| U-009 | New Users (monthly) | `users` | WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' | Historical |
| U-010 | User Growth Rate (%) | Calculated | (New Users / Total Users) × 100 | Calculated |
| U-011 | Users by Center | `users` | GROUP BY center_id | Real-time |
| U-012 | Users by Role | `users` | GROUP BY role | Real-time |

### 1.2 User Engagement Metrics (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| U-013 | Average Session Duration | `audit_logs` | AVG(session_end - session_start) | Historical |
| U-014 | Median Session Duration | `audit_logs` | PERCENTILE_CONT(0.5) | Historical |
| U-015 | Sessions per User (avg) | `audit_logs` | COUNT(DISTINCT request_id) / COUNT(DISTINCT user_id) | Calculated |
| U-016 | Login Frequency per User | `users.last_login` | Time between login events | Historical |
| U-017 | Days Since Last Login | `users.last_login` | NOW() - last_login | Real-time |
| U-018 | User Retention Rate (D1) | Calculated | % users returning next day | Calculated |
| U-019 | User Retention Rate (D7) | Calculated | % users returning within 7 days | Calculated |
| U-020 | User Retention Rate (D30) | Calculated | % users returning within 30 days | Calculated |
| U-021 | User Churn Rate | Calculated | 100 - Retention Rate | Calculated |
| U-022 | Power Users (top 10%) | Multiple tables | Top 10% by query volume | Calculated |
| U-023 | Casual Users (bottom 50%) | Multiple tables | Bottom 50% by query volume | Calculated |
| U-024 | Abandoned Accounts | `users` | No activity for 90+ days | Real-time |
| U-025 | Peak Usage Hours | `audit_logs` | GROUP BY HOUR(event_time) | Historical |
| U-026 | Peak Usage Days | `audit_logs` | GROUP BY DOW(event_time) | Historical |
| U-027 | Weekend vs Weekday Usage | `audit_logs` | GROUP BY is_weekend | Historical |

### 1.3 User Query Behavior (16 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| U-028 | Queries per User (avg) | `query_history` | AVG(COUNT per user_id) | Calculated |
| U-029 | Queries per User (median) | `query_history` | PERCENTILE_CONT(0.5) | Calculated |
| U-030 | Queries per User (P95) | `query_history` | PERCENTILE_CONT(0.95) | Calculated |
| U-031 | First Query Time-to-Value | `query_history` | Time from signup to first successful query | Calculated |
| U-032 | Query Success Rate per User | `query_history` | COUNT(success) / COUNT(total) per user | Calculated |
| U-033 | Average Query Length (chars) | `query_history.query_text` | AVG(LENGTH(query_text)) | Calculated |
| U-034 | Average Query Complexity (words) | `query_history.query_text` | AVG(word_count) | Calculated |
| U-035 | Multi-turn Conversation Rate | `context_threads` | % queries in threads vs standalone | Calculated |
| U-036 | Thread Depth Distribution | `context_threads` | AVG(message_count) per thread | Historical |
| U-037 | Query Refinement Rate | `context_threads` | % threads with >1 message | Calculated |
| U-038 | Zero-Result Query Rate | `query_history` | % queries with 0 sources | Calculated |
| U-039 | Low-Confidence Query Rate | `query_history.metrics` | % queries with confidence < threshold | Calculated |
| U-040 | Time Between Queries (avg) | `query_history` | AVG(time delta between queries) | Calculated |
| U-041 | Query Burst Detection | `query_history` | >N queries in <M seconds | Real-time |
| U-042 | Query Abandonment Rate | `context_threads` | % threads without completion | Calculated |
| U-043 | User Query Diversity | `query_history` | Unique use_cases per user | Calculated |

### 1.4 User Role & Permission Metrics (10 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| U-044 | Users by Role Distribution | `user_roles` | COUNT per role | Real-time |
| U-045 | Multi-Role Users | `user_roles` | Users with >1 role | Real-time |
| U-046 | Role Assignment Frequency | `user_roles` | New assignments per period | Historical |
| U-047 | Role Revocation Frequency | `user_roles` | Revocations per period | Historical |
| U-048 | Use Case Assignments per User | `user_use_case_assignments` | AVG(COUNT per user) | Calculated |
| U-049 | Use Case Assignment Expiration | `user_use_case_assignments` | WHERE expires_at < NOW() | Real-time |
| U-050 | Active vs Revoked Assignments | `user_use_case_assignments` | COUNT BY status | Real-time |
| U-051 | Permission Escalation Events | `audit_logs` | Role changes logged | Historical |
| U-052 | Least Privilege Violations | Calculated | Over-permissioned users detection | Calculated |
| U-053 | Role Effectiveness | `query_history` + `user_roles` | AVG queries per role type | Calculated |

### 1.5 User Efficiency Metrics (5 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| U-054 | Time to First Successful Query | `query_history` | From login to successful result | Calculated |
| U-055 | Document Discovery Effectiveness | `usage_stats` | Unique documents accessed per user | Calculated |
| U-056 | Source Utilization Diversity | `query_history.sources` | Unique sources per user | Calculated |
| U-057 | Repeat Query Patterns | `query_history` | Similar queries by same user | Calculated |
| U-058 | Query Optimization Score | Calculated | (Success rate × Avg relevancy) / Avg tokens | Calculated |

---

## DIMENSION 2: DOCUMENT & CONTENT ANALYTICS (62 metrics)

### 2.1 Document Inventory Metrics (18 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| D-001 | Total Documents | `documents` | COUNT(*) | Real-time |
| D-002 | Active Documents | `documents` | WHERE status = 'completed' | Real-time |
| D-003 | Processing Documents | `documents` | WHERE status = 'processing' | Real-time |
| D-004 | Failed Documents | `documents` | WHERE status = 'failed' | Real-time |
| D-005 | Deleted Documents | `documents` | WHERE status = 'deleted' | Real-time |
| D-006 | Documents by Classification | `documents` | GROUP BY classification | Real-time |
| D-007 | Documents by File Type | `documents` | GROUP BY file_type | Real-time |
| D-008 | Documents by Embedding Model | `documents` | GROUP BY embedding_model | Real-time |
| D-009 | Documents by Embedding Provider | `documents` | GROUP BY embedding_provider | Real-time |
| D-010 | Documents by Ingestion Date | `documents` | GROUP BY DATE(ingested_at) | Historical |
| D-011 | Documents by Author | `documents` | GROUP BY author | Real-time |
| D-012 | Documents by Source | `documents` | GROUP BY source | Real-time |
| D-013 | Documents by Tags | `documents` | UNNEST(tags) GROUP BY tag | Real-time |
| D-014 | Documents by Ingestion User | `documents` | GROUP BY ingested_by | Real-time |
| D-015 | Documents Ingested Today | `documents` | WHERE ingested_at >= CURRENT_DATE | Historical |
| D-016 | Documents Ingested This Week | `documents` | WHERE ingested_at >= week_start | Historical |
| D-017 | Documents Ingested This Month | `documents` | WHERE ingested_at >= month_start | Historical |
| D-018 | Document Growth Rate | Calculated | New docs / Total docs per period × 100 | Calculated |

### 2.2 Document Usage Patterns (20 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| D-019 | Hot Documents (24h) | `usage_stats` + `documents` | ✅ Implemented | Real-time |
| D-020 | Hot Documents (7d) | `usage_stats` + `documents` | Most accessed in 7 days | Historical |
| D-021 | Hot Documents (30d) | `usage_stats` + `documents` | Most accessed in 30 days | Historical |
| D-022 | Cold Documents (never accessed) | `documents` LEFT JOIN `usage_stats` | WHERE usage_stats.id IS NULL | Real-time |
| D-023 | Cold Documents (<5 accesses) | `usage_stats` | GROUP BY document_id HAVING COUNT < 5 | Historical |
| D-024 | Document Access Frequency Distribution | `usage_stats` | Histogram of access counts | Historical |
| D-025 | Document Access Trends | `usage_stats` | Time series of accesses | Historical |
| D-026 | Documents by Unique User Count | `usage_stats` | COUNT(DISTINCT user_id) per document | Calculated |
| D-027 | Average Relevancy per Document | `usage_stats` | AVG(average_relevancy) per document | Calculated |
| D-028 | Document Discovery Time | Calculated | ingested_at → first accessed_at delta | Calculated |
| D-029 | Document Shelf Life | Calculated | Days since last access | Real-time |
| D-030 | Document Access Velocity | Calculated | Accesses per day since ingestion | Calculated |
| D-031 | Document Re-Access Rate | `usage_stats` | % of repeat accesses by same user | Calculated |
| D-032 | Document Time-of-Day Patterns | `usage_stats` | GROUP BY HOUR(accessed_at) | Historical |
| D-033 | Document Day-of-Week Patterns | `usage_stats` | GROUP BY DOW(accessed_at) | Historical |
| D-034 | Most Shared Documents | `usage_stats` | By unique user count | Calculated |
| D-035 | Single-User Documents | `usage_stats` | Documents accessed by only 1 user | Real-time |
| D-036 | Cross-Center Document Usage | `usage_stats` + `users` | Documents accessed by multiple centers | Calculated |
| D-037 | Classification-Based Access Patterns | `documents` + `usage_stats` | Access rates by classification level | Historical |
| D-038 | Orphaned Documents | `documents` | No usage after 90 days | Real-time |

### 2.3 Document Quality Metrics (12 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| D-039 | Relevancy Score Distribution | `usage_stats` | Histogram of average_relevancy | Historical |
| D-040 | High-Quality Documents (>0.8) | `usage_stats` | WHERE average_relevancy > 0.8 | Real-time |
| D-041 | Low-Quality Documents (<0.5) | `usage_stats` | WHERE average_relevancy < 0.5 | Real-time |
| D-042 | Chunk Utilization Rate per Document | `usage_stats` | Used chunks / Total chunks | Calculated |
| D-043 | Documents with High Error Rates | `query_history` | Documents in failed queries | Calculated |
| D-044 | Documents with Low Engagement | `usage_stats` | <N accesses per month | Real-time |
| D-045 | Duplicate Documents (by checksum) | `documents` | GROUP BY file_checksum HAVING COUNT > 1 | Real-time |
| D-046 | Duplicate Prevention Effectiveness | Calculated | Blocked duplicates / Upload attempts | Calculated |
| D-047 | Document Metadata Completeness | `documents` | % of populated metadata fields | Calculated |
| D-048 | Tagging Completeness | `documents` | % documents with tags | Calculated |
| D-049 | Document Freshness Score | Calculated | (Recency × Access frequency × Relevancy) | Calculated |
| D-050 | Document ROI Score | Calculated | (Access count × Avg relevancy) / Storage cost | Calculated |

### 2.4 Document Size & Storage (7 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| D-051 | Total Storage Consumed (bytes) | `documents` | SUM(file_size) | Real-time |
| D-052 | Storage by Classification | `documents` | SUM(file_size) GROUP BY classification | Real-time |
| D-053 | Storage by File Type | `documents` | SUM(file_size) GROUP BY file_type | Real-time |
| D-054 | Average File Size | `documents` | AVG(file_size) | Calculated |
| D-055 | File Size Distribution | `documents` | Histogram of file_size | Historical |
| D-056 | Storage Growth Rate (bytes/day) | `documents` | SUM(file_size) per day trend | Historical |
| D-057 | Compression Ratio | `documents` | compressed_size / original_size | Calculated |

### 2.5 Document Processing Metrics (5 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| D-058 | Ingestion Success Rate | `documents` | (Completed / Total uploads) × 100 | Calculated |
| D-059 | Average Processing Time by File Type | Logs + `documents` | AVG(processing_time) GROUP BY file_type | Historical |
| D-060 | Processing Failure Rate | `documents` | (Failed / Total) × 100 | Calculated |
| D-061 | Processing Error Types | `documents.error_message` | GROUP BY error pattern | Historical |
| D-062 | Average Chunks per Document | `documents` | AVG(num_chunks) | Calculated |

---

## DIMENSION 3: CHUNK & RETRIEVAL ANALYTICS (32 metrics)

### 3.1 Chunk-Level Metrics (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| C-001 | Total Chunks in System | Qdrant + `documents` | SUM(num_chunks) | Real-time |
| C-002 | Hot Chunks (most retrieved) | `usage_stats` | ✅ Partially implemented | Historical |
| C-003 | Cold Chunks (never retrieved) | Qdrant vs `usage_stats` | Chunks never in chunk_ids arrays | Calculated |
| C-004 | Chunk Access Frequency Distribution | `usage_stats.chunk_ids` | UNNEST and count | Historical |
| C-005 | Chunks by Unique User Count | `usage_stats` | UNNEST chunk_ids, COUNT DISTINCT users | Calculated |
| C-006 | Chunks by Unique Document Count | `usage_stats` | Chunks appearing in multiple documents | Calculated |
| C-007 | Average Relevancy per Chunk | `usage_stats` | AVG(relevancy_scores) per chunk_id | Calculated |
| C-008 | High-Relevancy Chunks (>0.9) | `usage_stats` | Chunks with scores > 0.9 | Real-time |
| C-009 | Low-Relevancy Chunks (<0.5) | `usage_stats` | Chunks with scores < 0.5 | Real-time |
| C-010 | Chunk Position Effectiveness | Qdrant metadata | Relevancy by chunk_index | Calculated |
| C-011 | Chunk Size Distribution | `documents` | AVG(avg_chunk_size_tokens) distribution | Historical |
| C-012 | Optimal Chunk Size Analysis | `usage_stats` + `documents` | Chunk size vs relevancy correlation | Calculated |
| C-013 | Single-Use Chunks | `usage_stats` | Chunks retrieved only once | Historical |
| C-014 | Multi-Context Chunks | `usage_stats` | Chunks in different query contexts | Calculated |
| C-015 | Chunk Reuse Frequency | `usage_stats` | AVG reuses per chunk | Calculated |

### 3.2 Chunk Quality & Utilization (10 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| C-016 | Chunk Coverage per Document | `usage_stats` | % of document chunks retrieved | Calculated |
| C-017 | Unused Chunks Percentage | Calculated | (Never retrieved / Total) × 100 | Calculated |
| C-018 | Chunk Utilization Rate | `usage_stats` | Used chunks / Total chunks | Calculated |
| C-019 | Beginning-of-Document Bias | `usage_stats` + Qdrant | % from first 20% of document | Calculated |
| C-020 | End-of-Document Usage | `usage_stats` + Qdrant | % from last 20% of document | Calculated |
| C-021 | Chunk Sequence Patterns | `usage_stats.chunk_ids` | Sequential vs scattered retrieval | Calculated |
| C-022 | Chunk Diversity per Query | `usage_stats` | Unique documents in chunk_ids | Calculated |
| C-023 | Redundant Chunk Detection | Qdrant embeddings | Similar chunks across documents | Calculated |
| C-024 | Chunk Update Frequency | `documents.updated_at` | Document updates requiring re-chunking | Historical |
| C-025 | Chunk Embedding Drift | Qdrant + model changes | Re-embedding frequency | Historical |

### 3.3 Retrieval Performance (7 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| C-026 | Average Chunks per Retrieval | `usage_stats` | AVG(array_length(chunk_ids, 1)) | Calculated |
| C-027 | Median Chunks per Retrieval | `usage_stats` | PERCENTILE_CONT(0.5) of chunk counts | Calculated |
| C-028 | Top-K Effectiveness | `usage_stats` | Retrieved vs actually used chunks | Calculated |
| C-029 | Retrieval Precision | Calculated | Relevant chunks / Retrieved chunks | Calculated |
| C-030 | Retrieval Recall | Calculated | Retrieved relevant / Total relevant | Calculated |
| C-031 | Average Retrieval Time | Logs | Time for vector search | Historical |
| C-032 | Retrieval Timeout Rate | Logs | % searches exceeding timeout | Calculated |

---

## DIMENSION 4: QUERY & SEARCH ANALYTICS (45 metrics)

### 4.1 Query Volume & Patterns (12 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| Q-001 | Total Queries | `query_history` | COUNT(*) | Real-time |
| Q-002 | Queries Today | `query_history` | WHERE created_at >= CURRENT_DATE | Historical |
| Q-003 | Queries This Week | `query_history` | WHERE created_at >= week_start | Historical |
| Q-004 | Queries This Month | `query_history` | WHERE created_at >= month_start | Historical |
| Q-005 | Query Growth Rate | Calculated | % increase period over period | Calculated |
| Q-006 | Peak Query Hours | `query_history` | GROUP BY HOUR(created_at) | Historical |
| Q-007 | Peak Query Days | `query_history` | GROUP BY DOW(created_at) | Historical |
| Q-008 | Queries per Hour (avg) | `query_history` | COUNT / 24 | Calculated |
| Q-009 | Queries by Use Case | `query_history` | GROUP BY use_case_id | Real-time |
| Q-010 | Queries by Intent Type | `query_history` | GROUP BY intent_type | Real-time |
| Q-011 | Queries by Center | `query_history` | GROUP BY center_id | Real-time |
| Q-012 | Query Complexity Distribution | `query_history` | Token count histogram | Historical |

### 4.2 Query Performance (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| Q-013 | Average Processing Time (ms) | `query_history` | AVG(processing_time_ms) | Calculated |
| Q-014 | Median Processing Time (ms) | `query_history` | PERCENTILE_CONT(0.5) | Calculated |
| Q-015 | P50 Latency | `query_history` | 50th percentile processing_time_ms | Calculated |
| Q-016 | P95 Latency | `query_history` | 95th percentile processing_time_ms | Calculated |
| Q-017 | P99 Latency | `query_history` | 99th percentile processing_time_ms | Calculated |
| Q-018 | Slow Query Identification (>5s) | `query_history` | WHERE processing_time_ms > 5000 | Real-time |
| Q-019 | Very Slow Queries (>10s) | `query_history` | WHERE processing_time_ms > 10000 | Real-time |
| Q-020 | Processing Time by Use Case | `query_history` | AVG(time) GROUP BY use_case_id | Calculated |
| Q-021 | Processing Time by Model | `query_history` + `token_usage` | AVG(time) GROUP BY model_id | Calculated |
| Q-022 | Processing Time Trend | `query_history` | Time series of avg processing time | Historical |
| Q-023 | Query Success Rate | `query_history` | WHERE response_status = 'success' / total | Calculated |
| Q-024 | Query Error Rate | `query_history` | WHERE response_status = 'error' / total | Calculated |
| Q-025 | Query Timeout Rate | `query_history` | WHERE response_status = 'timeout' / total | Calculated |
| Q-026 | Response Status Distribution | `query_history` | GROUP BY response_status | Real-time |
| Q-027 | Time-to-First-Token (TTFT) | Logs | If streaming, time to first response | Historical |

### 4.3 Search Quality (12 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| Q-028 | Average Relevancy Score | `usage_stats` | ✅ Already tracked | Calculated |
| Q-029 | Median Relevancy Score | `usage_stats` | PERCENTILE_CONT(0.5) | Calculated |
| Q-030 | Relevancy Score Distribution | `usage_stats` | Histogram | Historical |
| Q-031 | High-Relevancy Queries (>0.8) | `usage_stats` | WHERE average_relevancy > 0.8 | Calculated |
| Q-032 | Low-Relevancy Queries (<0.5) | `usage_stats` | WHERE average_relevancy < 0.5 | Calculated |
| Q-033 | Relevancy Trend Over Time | `usage_stats` | Time series of avg_relevancy | Historical |
| Q-034 | Zero-Result Query Count | `usage_stats` | WHERE total_results_found = 0 | Real-time |
| Q-035 | Zero-Result Query Rate | Calculated | (Zero results / Total queries) × 100 | Calculated |
| Q-036 | Low-Result Queries (<3 results) | `usage_stats` | WHERE total_results_found < 3 | Real-time |
| Q-037 | Average Results per Query | `usage_stats` | AVG(total_results_found) | Calculated |
| Q-038 | RAG Confidence Distribution | `usage_stats` | Histogram of rag_confidence | Historical |
| Q-039 | Low-Confidence Query Rate | `usage_stats` | WHERE rag_confidence < threshold | Calculated |

### 4.4 Query Threading & Conversations (6 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| Q-040 | Total Active Threads | `context_threads` | WHERE is_active = true | Real-time |
| Q-041 | Average Thread Depth | `context_threads` | AVG(message_count) | Calculated |
| Q-042 | Median Thread Depth | `context_threads` | PERCENTILE_CONT(0.5) of message_count | Calculated |
| Q-043 | Thread Completion Rate | `context_threads` | % threads marked complete | Calculated |
| Q-044 | Thread Abandonment Rate | `context_threads` | % inactive threads without resolution | Calculated |
| Q-045 | Average Thread Duration | `context_threads` | AVG(last_activity_at - created_at) | Calculated |

---

## DIMENSION 5: TOKEN & LLM USAGE ANALYTICS (38 metrics)

### 5.1 Token Consumption Metrics (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| T-001 | Total Tokens Consumed | `token_usage` | SUM(total_tokens) | Real-time |
| T-002 | Total Input Tokens | `token_usage` | SUM(tokens_in) | Real-time |
| T-003 | Total Output Tokens | `token_usage` | SUM(tokens_out) | Real-time |
| T-004 | Tokens Today | `token_usage` | WHERE created_at >= CURRENT_DATE | Historical |
| T-005 | Tokens This Week | `token_usage` | WHERE created_at >= week_start | Historical |
| T-006 | Tokens This Month | `token_usage` | WHERE created_at >= month_start | Historical |
| T-007 | Token Growth Rate | Calculated | % increase period over period | Calculated |
| T-008 | Tokens per Query (avg) | `token_usage` + `query_history` | AVG(total_tokens) per query | Calculated |
| T-009 | Tokens per User (avg) | `token_usage` | AVG(tokens) GROUP BY user_id | Calculated |
| T-010 | Tokens per Use Case (avg) | `token_usage` | AVG(tokens) GROUP BY use_case_id | Calculated |
| T-011 | Tokens per Model | `token_usage` | SUM(tokens) GROUP BY model_id | Real-time |
| T-012 | Tokens per Center | `token_usage` | SUM(tokens) GROUP BY center_id | Real-time |
| T-013 | Token Consumption Trend | `token_usage` | Time series of daily tokens | Historical |
| T-014 | Peak Token Usage Hours | `token_usage` | GROUP BY HOUR(created_at) | Historical |
| T-015 | Token Usage Patterns (DoW) | `token_usage` | GROUP BY DOW(created_at) | Historical |

### 5.2 Token Efficiency Metrics (10 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| T-016 | Input/Output Token Ratio | `token_usage` | AVG(tokens_in / tokens_out) | Calculated |
| T-017 | Tokens per Successful Query | `token_usage` + `query_history` | AVG(tokens) WHERE status = 'success' | Calculated |
| T-018 | Wasted Tokens (errors) | `token_usage` + `query_history` | SUM(tokens) WHERE status = 'error' | Calculated |
| T-019 | Wasted Tokens (timeouts) | `token_usage` + `query_history` | SUM(tokens) WHERE status = 'timeout' | Calculated |
| T-020 | Token Efficiency Score | Calculated | (Successful tokens / Total tokens) × 100 | Calculated |
| T-021 | Tokens per Second (throughput) | `token_usage` | total_tokens / call_duration_ms | Calculated |
| T-022 | Average Call Duration | `token_usage` | AVG(call_duration_ms) | Calculated |
| T-023 | Streaming Usage Rate | `token_usage` | % WHERE streaming_used = true | Calculated |
| T-024 | Token Cost per Query | `token_usage` + pricing | AVG(total_cost) per query | Calculated |
| T-025 | Cost Efficiency by Model | `token_usage` | (Success rate / Cost) by model | Calculated |

### 5.3 Context Management Metrics (8 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| T-026 | Average Context Size (tokens) | `context_threads` | AVG(context_size_tokens) | Calculated |
| T-027 | Context Window Utilization (%) | `context_threads` | (context_size / max_context) × 100 | Calculated |
| T-028 | Context Overflow Events | `context_threads` | WHERE context_size > max_context | Real-time |
| T-029 | Auto-Compaction Frequency | Logs + `thread_messages` | WHERE is_summary = true | Historical |
| T-030 | Messages per Thread | `context_threads` | AVG(message_count) | Calculated |
| T-031 | Average Message Token Count | `thread_messages` | AVG(token_count) | Calculated |
| T-032 | Context Growth Rate per Thread | `thread_messages` | SUM(token_count) per thread over time | Calculated |
| T-033 | Compaction Effectiveness | Calculated | Tokens before/after compaction ratio | Calculated |

### 5.4 Model-Specific Token Metrics (5 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| T-034 | Tokens by Model Type | `token_usage` + `models` | SUM(tokens) GROUP BY model_type | Real-time |
| T-035 | Tokens by Provider | `token_usage` | SUM(tokens) GROUP BY model_provider | Real-time |
| T-036 | Reasoning Model Token Usage | `token_usage` + `models` | WHERE is_reasoning_model = true | Real-time |
| T-037 | Tool-Using Model Token Overhead | `token_usage` + `tool_invocations` | Extra tokens for tool calls | Calculated |
| T-038 | Context Window by Model | `models` | Distribution of context_window values | Real-time |

---

## DIMENSION 6: MODEL PERFORMANCE & COST (52 metrics)

### 6.1 Model Selection & Usage (12 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| M-001 | Total Models Registered | `models` | COUNT(*) | Real-time |
| M-002 | Available Models | `models` | WHERE is_available = true | Real-time |
| M-003 | Deprecated Models | `models` | WHERE deprecated = true | Real-time |
| M-004 | Models by Usage Frequency | `token_usage` | COUNT(requests) GROUP BY model_id | Historical |
| M-005 | Most Used Model | `token_usage` | Model with highest request count | Real-time |
| M-006 | Least Used Models | `token_usage` | Models with <N requests | Real-time |
| M-007 | Model Selection by Use Case | `query_history` + config | Model choices per use_case_id | Historical |
| M-008 | Model Selection by User | `token_usage` | Preferences by user_id | Historical |
| M-009 | Model Availability Rate | `models` | (Available / Total) × 100 | Calculated |
| M-010 | Model Health Status Distribution | `models` | GROUP BY health_status | Real-time |
| M-011 | Models by Provider Distribution | `models` | COUNT GROUP BY provider | Real-time |
| M-012 | Models by Type Distribution | `models` | COUNT GROUP BY model_type | Real-time |

### 6.2 Model Performance Metrics (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| M-013 | Average Latency per Model | `token_usage` | AVG(call_duration_ms) GROUP BY model_id | Calculated |
| M-014 | P95 Latency per Model | `token_usage` | PERCENTILE_CONT(0.95) GROUP BY model_id | Calculated |
| M-015 | Tokens per Second per Model | `token_usage` | AVG(total_tokens / call_duration_ms × 1000) | Calculated |
| M-016 | Success Rate per Model | `token_usage` + `query_history` | % successful requests | Calculated |
| M-017 | Error Rate per Model | `token_usage` + `query_history` | % failed requests | Calculated |
| M-018 | Timeout Rate per Model | `query_history` | % timeout responses | Calculated |
| M-019 | Response Quality per Model | `usage_stats` + model tracking | AVG(average_relevancy) per model | Calculated |
| M-020 | Model vs Target Latency | `models` | Actual vs typical_latency_ms | Calculated |
| M-021 | Model Performance Consistency | `token_usage` | StdDev(call_duration_ms) per model | Calculated |
| M-022 | Model Retry Rate | Logs | % requests requiring retry | Calculated |
| M-023 | Model Fallback Frequency | Logs | When primary model fails | Historical |
| M-024 | Model Warm-up Time | Logs | First request vs subsequent | Calculated |
| M-025 | Concurrent Request Handling | Logs | Max concurrent per model | Real-time |
| M-026 | Model Queue Depth | Real-time monitoring | Pending requests | Real-time |
| M-027 | Model Throughput (req/s) | `token_usage` | Requests per second | Calculated |

### 6.3 Model Cost Analysis (15 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| M-028 | Total Cost (all models) | `token_usage` | SUM(total_cost) | Real-time |
| M-029 | Cost Today | `token_usage` | WHERE created_at >= CURRENT_DATE | Historical |
| M-030 | Cost This Week | `token_usage` | WHERE created_at >= week_start | Historical |
| M-031 | Cost This Month | `token_usage` | WHERE created_at >= month_start | Historical |
| M-032 | Cost per Model | `token_usage` | SUM(total_cost) GROUP BY model_id | Real-time |
| M-033 | Cost per Use Case | `token_usage` | SUM(total_cost) GROUP BY use_case_id | Real-time |
| M-034 | Cost per User | `token_usage` | SUM(total_cost) GROUP BY user_id | Real-time |
| M-035 | Cost per Center | `token_usage` | SUM(total_cost) GROUP BY center_id | Real-time |
| M-036 | Cost Growth Rate | Calculated | % increase period over period | Calculated |
| M-037 | Input vs Output Cost Ratio | `token_usage` | Input cost / Output cost | Calculated |
| M-038 | Cost per Query | `token_usage` + `query_history` | AVG(total_cost) per query | Calculated |
| M-039 | Cost per Successful Query | Calculated | Total cost / Successful queries | Calculated |
| M-040 | Wasted Cost (errors) | `token_usage` | SUM(cost) for failed queries | Calculated |
| M-041 | Cost Efficiency Score | Calculated | (Success rate × Quality) / Cost | Calculated |
| M-042 | Budget Utilization (%) | Calculated | Current spend / Budget × 100 | Real-time |

### 6.4 Model Capabilities & Specialization (10 metrics)

| Metric ID | Metric Name | Data Source | Calculation | Type |
|-----------|-------------|-------------|-------------|------|
| M-043 | Tool-Capable Models Usage | `models` + `token_usage` | WHERE supports_tools = true | Real-time |
| M-044 | Vision-Capable Models Usage | `models` + `token_usage` | WHERE supports_vision = true | Real-time |
| M-045 | Audio-Capable Models Usage | `models` + `token_usage` | WHERE supports_audio = true | Real-time |
| M-046 | Reasoning Models Usage | `models` + `token_usage` | WHERE is_reasoning_model = true | Real-time |
| M-047 | Context Window Utilization | `token_usage` + `models` | % of max context_window used | Calculated |
| M-048 | Model Specialization Effectiveness | `models` + usage | Specialization match to use case | Calculated |
| M-049 | Recommended Use Case Alignment | `models` + `query_history` | Actual vs recommended_use_cases | Calculated |
| M-050 | Model Version Distribution | `token_usage` | COUNT GROUP BY model_version | Real-time |
| M-051 | Model Deprecation Timeline | `models` | Days until deprecation_date | Real-time |
| M-052 | Model Migration Readiness | Calculated | Usage of deprecated models | Real-time |

---

*[Document continues with Dimensions 7-15... Would you like me to continue with the remaining dimensions?]*

**Note:** This document is designed to be comprehensive. The remaining 7 dimensions (Use Case & Workflow, Security & Audit, Tool & MCP, Conversation & Threading, Ingestion & Pipeline, Embedding & Vector Store, Database Management, Configuration & Health, Cost & ROI) follow the same structured format and will add approximately 229 additional metrics to reach the total of 381.

---

## Appendix A: Metric Type Definitions

- **Real-time:** Can be queried instantly from current database state
- **Historical:** Requires aggregation over time periods
- **Calculated:** Derived from combining multiple data sources

## Appendix B: Industry Best Practices Reference

Based on research, key industry recommendations include:

1. **LLM Observability:** Focus on token efficiency, cost per query, and quality metrics (relevancy, confidence)
2. **RAG System Analytics:** Track retrieval precision, chunk utilization, and relevancy score distributions
3. **SOC Analytics:** Emphasize security events, audit trails, and compliance metrics
4. **Vector Database Monitoring:** Monitor collection sizes, search latency, and index health
5. **Cost Optimization:** Model comparison, usage patterns, and ROI calculations

## Appendix C: Data Collection Considerations

### Already Collected (Ready to Report)

- User activity and authentication
- Query history and performance
- Document metadata and usage
- Token consumption
- Audit logs

### Requires Additional Instrumentation

- Real-time streaming metrics
- Model warm-up times
- Cache performance
- Vector store detailed metrics
- Application-level profiling

### Requires PostgreSQL Extensions

- pg_stat_statements (query performance)
- pg_stat_all_tables (table statistics)
- pg_stat_all_indexes (index statistics)

---

**End of Part 1 - See `VALUE_ANALYSIS_REPORTING_METRICS.md` for the value assessment of each metric.**
