# Run Manifests API

**Version:** 1.0
**Last Updated:** November 1, 2025
**ADR Reference:** ADR-030 No Transcripts; Run Manifests Only

## Overview

The Run Manifests API provides access to PII-free execution telemetry for quality metrics, repeatability analysis, and use case validation. Run manifests capture execution metadata without storing conversation content, enabling quality tracking in the Stateless Core v1 architecture.

**Key Features:**
- **PII-free telemetry** - No conversation content stored
- **Quality metrics** - Schema validity, conformance scores, latency
- **Tool chain tracking** - Which tools were invoked
- **Idempotence validation** - Detect non-deterministic behavior
- **Cost tracking** - Token usage and execution costs

## Data Model

### Run Manifest Fields

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | UUID | Unique run identifier |
| `ts_utc` | timestamp | Execution timestamp (UTC) |
| `use_case_id` | string | Use case executed |
| `template_ver` | string | Template version used |
| `model_name` | string | LLM model name |
| `model_version` | string | LLM model version |
| `params_hash` | string | MD5 hash of generation parameters |
| `schema_valid` | boolean | Output matched expected schema |
| `conformance` | float | Conformance score (0.0-1.0) |
| `tool_chain` | array | Tools invoked in order |
| `idempotence_ok` | boolean | Idempotence check passed |
| `latency_total_ms` | integer | Total execution time |
| `latency_llm_ms` | integer | LLM processing time |
| `latency_tools_ms` | integer | Tool execution time |
| `tokens_in` | integer | Input tokens consumed |
| `tokens_out` | integer | Output tokens generated |
| `result_kind` | enum | Result type (success, contract_violation, policy_block, error) |

### Result Kinds

| Value | Description |
|-------|-------------|
| `success` | Execution completed successfully |
| `contract_violation` | Output failed schema validation |
| `policy_block` | Blocked by policy rules |
| `error` | Execution error occurred |

## Endpoints

### Query Run Manifests

Retrieve run manifests with filtering and pagination.

**Endpoint:** `GET /api/v1/run-manifests`
**Authentication:** Required (JWT)
**Permissions:** `admin` or `analytics_viewer`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `use_case_id` | string | No | Filter by use case |
| `result_kind` | string | No | Filter by result type |
| `start_date` | ISO8601 | No | Filter from date |
| `end_date` | ISO8601 | No | Filter to date |
| `limit` | integer | No | Results per page (default: 100, max: 1000) |
| `offset` | integer | No | Pagination offset (default: 0) |
| `sort_by` | string | No | Sort field (default: `ts_utc`) |
| `sort_order` | string | No | Sort direction (`asc`, `desc`) (default: `desc`) |

#### Request

```http
GET /api/v1/run-manifests?use_case_id=threat-triage-v1&limit=50&sort_order=desc HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "manifests": [
    {
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "ts_utc": "2025-11-01T14:23:45.123Z",
      "use_case_id": "threat-triage-v1",
      "template_ver": "2.1.0",
      "model_name": "gpt-4",
      "model_version": "gpt-4-0613",
      "params_hash": "a1b2c3d4e5f6",
      "schema_valid": true,
      "conformance": 0.987,
      "tool_chain": ["semantic_search", "llm_generation"],
      "idempotence_ok": true,
      "latency_total_ms": 2341,
      "latency_llm_ms": 1845,
      "latency_tools_ms": 496,
      "tokens_in": 1523,
      "tokens_out": 487,
      "result_kind": "success"
    }
  ],
  "total_count": 1247,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

### Get Single Run Manifest

Retrieve a specific run manifest by ID.

**Endpoint:** `GET /api/v1/run-manifests/{run_id}`
**Authentication:** Required (JWT)

#### Request

```http
GET /api/v1/run-manifests/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "ts_utc": "2025-11-01T14:23:45.123Z",
  "use_case_id": "threat-triage-v1",
  "template_ver": "2.1.0",
  "model_name": "gpt-4",
  "model_version": "gpt-4-0613",
  "params_hash": "a1b2c3d4e5f6",
  "schema_valid": true,
  "conformance": 0.987,
  "tool_chain": ["semantic_search", "llm_generation"],
  "idempotence_ok": true,
  "latency_total_ms": 2341,
  "latency_llm_ms": 1845,
  "latency_tools_ms": 496,
  "tokens_in": 1523,
  "tokens_out": 487,
  "result_kind": "success"
}
```

### Aggregate Metrics

Get aggregated metrics across multiple run manifests.

**Endpoint:** `GET /api/v1/run-manifests/metrics/aggregate`
**Authentication:** Required (JWT)

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `use_case_id` | string | Yes | Use case to analyze |
| `start_date` | ISO8601 | No | Analysis from date |
| `end_date` | ISO8601 | No | Analysis to date |
| `group_by` | string | No | Group by field (`hour`, `day`, `week`) |

#### Request

```http
GET /api/v1/run-manifests/metrics/aggregate?use_case_id=threat-triage-v1&group_by=day HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "use_case_id": "threat-triage-v1",
  "period": {
    "start": "2025-10-01T00:00:00Z",
    "end": "2025-11-01T23:59:59Z"
  },
  "total_runs": 1247,
  "metrics": {
    "schema_validity_rate": 0.995,
    "avg_conformance": 0.982,
    "tool_selection_stability": 0.991,
    "p50_latency_ms": 1823,
    "p95_latency_ms": 3456,
    "p99_latency_ms": 4789,
    "avg_tokens_in": 1456.3,
    "avg_tokens_out": 523.7,
    "idempotence_violations": 3,
    "success_rate": 0.987
  },
  "result_distribution": {
    "success": 1231,
    "contract_violation": 8,
    "policy_block": 2,
    "error": 6
  },
  "daily_breakdown": [
    {
      "date": "2025-10-01",
      "runs": 42,
      "svr": 0.976,
      "avg_latency_ms": 1892
    }
  ]
}
```

### Delete Old Manifests

Delete run manifests older than specified date (admin only).

**Endpoint:** `DELETE /api/v1/run-manifests`
**Authentication:** Required (JWT)
**Permissions:** `admin`

#### Request

```http
DELETE /api/v1/run-manifests?older_than=2025-09-01T00:00:00Z HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "deleted_count": 1523,
  "oldest_remaining": "2025-09-01T00:05:23Z"
}
```

## Quality Metrics

### Schema Validity Rate (SVR)

Percentage of runs where output matched expected schema.

**Formula:** `valid_runs / total_runs`
**Target:** ≥ 99.5%
**Interpretation:**
- **≥ 99.5%:** Excellent - schema compliance maintained
- **95-99.5%:** Good - minor schema issues
- **< 95%:** Poor - investigate template/model issues

### Conformance Score

Weighted score measuring output quality across multiple dimensions.

**Components:**
- Schema validity (40%)
- Tool selection accuracy (30%)
- Policy compliance (30%)

**Range:** 0.0 to 1.0
**Target:** ≥ 0.98
**Interpretation:**
- **≥ 0.98:** Excellent quality
- **0.95-0.98:** Acceptable quality
- **< 0.95:** Needs improvement

### Tool Selection Stability

Percentage of runs with consistent tool chain for same inputs.

**Formula:** `most_common_chain_count / total_runs`
**Target:** ≥ 0.99
**Interpretation:**
- **≥ 0.99:** Highly deterministic
- **0.95-0.99:** Acceptable variation
- **< 0.95:** Non-deterministic behavior detected

## Usage Examples

### TypeScript/Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RunManifest {
  run_id: string;
  ts_utc: string;
  use_case_id: string;
  schema_valid: boolean;
  conformance: number;
  latency_total_ms: number;
  result_kind: string;
}

export interface ManifestQueryParams {
  use_case_id?: string;
  result_kind?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface ManifestsResponse {
  manifests: RunManifest[];
  total_count: number;
  has_more: boolean;
}

@Injectable({ providedIn: 'root' })
export class RunManifestsService {
  private apiUrl = '/api/v1/run-manifests';

  constructor(private http: HttpClient) {}

  queryManifests(params: ManifestQueryParams): Observable<ManifestsResponse> {
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        httpParams = httpParams.set(key, value.toString());
      }
    });

    return this.http.get<ManifestsResponse>(this.apiUrl, { params: httpParams });
  }

  getManifest(runId: string): Observable<RunManifest> {
    return this.http.get<RunManifest>(`${this.apiUrl}/${runId}`);
  }

  getAggregateMetrics(
    useCaseId: string,
    startDate?: string,
    endDate?: string
  ): Observable<any> {
    let params = new HttpParams().set('use_case_id', useCaseId);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);

    return this.http.get(`${this.apiUrl}/metrics/aggregate`, { params });
  }
}
```

### Python

```python
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class RunManifestsClient:
    """Client for Run Manifests API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def query_manifests(
        self,
        use_case_id: Optional[str] = None,
        result_kind: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """Query run manifests with filters."""
        params = {"limit": limit, "offset": offset}
        if use_case_id:
            params["use_case_id"] = use_case_id
        if result_kind:
            params["result_kind"] = result_kind
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/run-manifests",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def get_aggregate_metrics(
        self,
        use_case_id: str,
        days: int = 30
    ) -> Dict:
        """Get aggregate metrics for use case."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        params = {
            "use_case_id": use_case_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": "day"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/run-manifests/metrics/aggregate",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()

    async def check_quality_slos(self, use_case_id: str) -> bool:
        """Check if use case meets quality SLOs."""
        metrics = await self.get_aggregate_metrics(use_case_id)

        svr_ok = metrics["metrics"]["schema_validity_rate"] >= 0.995
        conformance_ok = metrics["metrics"]["avg_conformance"] >= 0.98
        stability_ok = metrics["metrics"]["tool_selection_stability"] >= 0.99

        return svr_ok and conformance_ok and stability_ok

# Usage
client = RunManifestsClient("http://localhost:8006", "jwt_token_here")

# Query recent failures
failures = await client.query_manifests(
    use_case_id="threat-triage-v1",
    result_kind="error",
    start_date=datetime.utcnow() - timedelta(days=7)
)

# Check quality
quality_ok = await client.check_quality_slos("threat-triage-v1")
if not quality_ok:
    print("Quality SLOs not met - investigate")
```

### cURL

```bash
# Query recent runs
curl -X GET "http://localhost:8006/api/v1/run-manifests?use_case_id=threat-triage-v1&limit=50" \
  -H "Authorization: Bearer <jwt_token>"

# Get aggregate metrics
curl -X GET "http://localhost:8006/api/v1/run-manifests/metrics/aggregate?use_case_id=threat-triage-v1&group_by=day" \
  -H "Authorization: Bearer <jwt_token>"

# Get specific run
curl -X GET "http://localhost:8006/api/v1/run-manifests/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <jwt_token>"

# Delete old manifests (admin only)
curl -X DELETE "http://localhost:8006/api/v1/run-manifests?older_than=2025-09-01T00:00:00Z" \
  -H "Authorization: Bearer <jwt_token>"
```

## Monitoring & Alerting

### Quality Alerts

```yaml
# Example Prometheus alerting rules
groups:
  - name: run_manifest_quality
    rules:
      - alert: LowSchemaValidityRate
        expr: run_manifest_svr < 0.995
        for: 5m
        annotations:
          summary: "Schema Validity Rate below 99.5%"
          description: "SVR is {{ $value | humanizePercentage }}"

      - alert: LowConformanceScore
        expr: run_manifest_avg_conformance < 0.98
        for: 10m
        annotations:
          summary: "Conformance score below 0.98"

      - alert: HighIdempotenceViolations
        expr: rate(run_manifest_idempotence_violations[1h]) > 0.01
        for: 5m
        annotations:
          summary: "Idempotence violations detected"
```

### Dashboard Queries

```python
# Daily SVR trend
daily_svr = await client.query_manifests(
    use_case_id="threat-triage-v1",
    start_date=datetime.utcnow() - timedelta(days=30)
)

# Latency percentiles
metrics = await client.get_aggregate_metrics("threat-triage-v1")
print(f"p50: {metrics['metrics']['p50_latency_ms']}ms")
print(f"p95: {metrics['metrics']['p95_latency_ms']}ms")
print(f"p99: {metrics['metrics']['p99_latency_ms']}ms")
```

## Data Retention

**Default Policy:**
- Run manifests retained for 90 days
- Aggregated metrics retained indefinitely
- Manual deletion available for compliance

**Storage Estimates:**
- ~500 bytes per manifest
- 10,000 runs/day = ~5 MB/day = ~450 MB/90 days

## Best Practices

1. **Monitor SVR Daily** - Schema validity rate is the primary quality indicator
2. **Alert on Conformance Drops** - Set up alerts for < 0.98 conformance
3. **Track Latency Trends** - Monitor p95/p99 latency for performance degradation
4. **Regular Cleanup** - Delete old manifests to manage storage
5. **Use Aggregates for Dashboards** - More efficient than raw manifest queries

## Related Documentation

- [ADR-030: No Transcripts; Run Manifests Only](../development/adrs/ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-034: Use Case Validation Harness](../development/adrs/ADR-034-Use-Case-Validation-Harness.md)
- [Capabilities API](capabilities.md)
- [Use Case Validation Guide](../user-guides/USE_CASE_VALIDATION.md)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial release for Stateless Core v1 |
