# Capabilities API

**Version:** 1.0
**Last Updated:** November 1, 2025
**ADR Reference:** ADR-032 Capabilities & Edition Flags

## Overview

The Capabilities API provides system capability and edition information to clients, enabling adaptive UI behavior based on available features. This API implements ADR-032 (Capabilities & Edition Flags) for the Stateless Core v1 architecture.

## Endpoints

### Get System Capabilities

Retrieves the current system capabilities and edition configuration.

**Endpoint:** `GET /api/system/capabilities`
**Authentication:** Required (JWT)
**Rate Limit:** 100 requests/minute

#### Request

```http
GET /api/system/capabilities HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "edition": "core",
  "version": "1.0.0",
  "stateless": true,
  "stateful": false,
  "capabilities": [
    {
      "name": "stateless_execution",
      "display_name": "Stateless Execution",
      "description": "Execute use cases without server-side state storage",
      "category": "core",
      "status": "enabled",
      "edition": "core",
      "version": "1.0.0"
    },
    {
      "name": "client_exports",
      "display_name": "Client-Owned Exports",
      "description": "Export conversations in Markdown/JSON formats",
      "category": "export",
      "status": "enabled",
      "edition": "core",
      "version": "1.0.0"
    },
    {
      "name": "run_manifests",
      "display_name": "Run Manifests",
      "description": "PII-free telemetry for quality metrics",
      "category": "telemetry",
      "status": "enabled",
      "edition": "core",
      "version": "1.0.0"
    },
    {
      "name": "corpus_management",
      "display_name": "Corpus Management",
      "description": "Document chunking and preflight analysis",
      "category": "corpus",
      "status": "enabled",
      "edition": "core",
      "version": "1.0.0"
    },
    {
      "name": "history_storage",
      "display_name": "Conversation History Storage",
      "description": "Server-side conversation persistence",
      "category": "storage",
      "status": "disabled",
      "edition": "plus",
      "version": "2.0.0"
    },
    {
      "name": "evidence_sink",
      "display_name": "Evidence Collection",
      "description": "WORM-compliant evidence storage",
      "category": "compliance",
      "status": "disabled",
      "edition": "plus",
      "version": "2.0.0"
    }
  ],
  "feature_flags": {
    "RUN_MANIFEST_ENABLED": true,
    "STATEFUL_ENABLED": false,
    "HISTORY_PROVIDER": "none",
    "EVIDENCE_SINK": "none",
    "CRYPTO_PROVIDER": "none"
  },
  "export_formats": ["md", "json"],
  "providers": {
    "history": "edge_only",
    "evidence": "none",
    "crypto": "none"
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `edition` | string | Current system edition (`core` or `plus`) |
| `version` | string | System version (semantic versioning) |
| `stateless` | boolean | Stateless execution mode enabled |
| `stateful` | boolean | Stateful execution mode enabled |
| `capabilities` | array | List of system capabilities |
| `feature_flags` | object | Runtime feature flag configuration |
| `export_formats` | array | Supported export formats |
| `providers` | object | Active provider implementations |

#### Capability Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Capability identifier (snake_case) |
| `display_name` | string | Human-readable capability name |
| `description` | string | Capability description |
| `category` | string | Capability category |
| `status` | string | Current status (`enabled`, `disabled`, `beta`) |
| `edition` | string | Required edition (`core`, `plus`) |
| `version` | string | Capability version |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized (invalid/missing JWT) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Check Specific Capability

Check if a specific capability is enabled.

**Endpoint:** `GET /api/system/capabilities/{capability_name}`
**Authentication:** Required (JWT)

#### Request

```http
GET /api/system/capabilities/client_exports HTTP/1.1
Host: api.aio.local
Authorization: Bearer <jwt_token>
```

#### Response

**Status:** 200 OK

```json
{
  "name": "client_exports",
  "enabled": true,
  "edition_required": "core",
  "current_edition": "core",
  "available": true
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Capability name |
| `enabled` | boolean | Whether capability is currently enabled |
| `edition_required` | string | Minimum edition required |
| `current_edition` | string | Current system edition |
| `available` | boolean | Whether capability is available (edition match) |

#### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |
| 404 | Capability not found |
| 500 | Internal server error |

## Capability Categories

### Core Capabilities (Edition: core)

| Capability | Description | Status |
|------------|-------------|--------|
| `stateless_execution` | Execute use cases without server-side state | Enabled |
| `client_exports` | Export conversations (MD/JSON) | Enabled |
| `run_manifests` | PII-free telemetry collection | Enabled |
| `corpus_management` | Document chunking and preflight | Enabled |
| `use_case_validation` | Use case testing framework | Enabled |
| `sampling_presets` | Predefined LLM sampling configurations | Enabled |

### Plus Capabilities (Edition: plus)

| Capability | Description | Status |
|------------|-------------|--------|
| `history_storage` | Server-side conversation persistence | Future |
| `evidence_sink` | WORM-compliant evidence collection | Future |
| `field_encryption` | Field-level data encryption | Future |
| `compliance_reporting` | Automated compliance reports | Future |
| `hsm_integration` | Hardware security module support | Future |

## Usage Examples

### TypeScript/Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface CapabilitiesResponse {
  edition: string;
  stateless: boolean;
  stateful: boolean;
  capabilities: Capability[];
  feature_flags: Record<string, any>;
  export_formats: string[];
}

export interface Capability {
  name: string;
  display_name: string;
  status: 'enabled' | 'disabled' | 'beta';
  edition: 'core' | 'plus';
}

@Injectable({ providedIn: 'root' })
export class CapabilitiesService {
  private apiUrl = '/api/system/capabilities';

  constructor(private http: HttpClient) {}

  getCapabilities(): Observable<CapabilitiesResponse> {
    return this.http.get<CapabilitiesResponse>(this.apiUrl);
  }

  hasCapability(capabilityName: string): Observable<boolean> {
    return this.http.get<{enabled: boolean}>(
      `${this.apiUrl}/${capabilityName}`
    ).pipe(
      map(response => response.enabled)
    );
  }
}
```

### Python

```python
import httpx
from typing import Dict, List

class CapabilitiesClient:
    """Client for Capabilities API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get_capabilities(self) -> Dict:
        """Get all system capabilities."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/system/capabilities",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def has_capability(self, name: str) -> bool:
        """Check if specific capability is enabled."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/system/capabilities/{name}",
                headers=self.headers
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return response.json().get("enabled", False)

# Usage
client = CapabilitiesClient("http://localhost:8006", "jwt_token_here")
capabilities = await client.get_capabilities()

if capabilities["stateless"]:
    print("Stateless mode is enabled")

can_export = await client.has_capability("client_exports")
if can_export:
    print("Client exports are available")
```

### cURL

```bash
# Get all capabilities
curl -X GET http://localhost:8006/api/system/capabilities \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"

# Check specific capability
curl -X GET http://localhost:8006/api/system/capabilities/client_exports \
  -H "Authorization: Bearer <jwt_token>"
```

## Frontend UI Adaptation

### Conditional Feature Display

```typescript
@Component({
  selector: 'app-export-menu',
  template: `
    <button *ngIf="canExport$ | async" (click)="exportConversation()">
      Export Conversation
    </button>
    <button *ngIf="canSaveHistory$ | async" (click)="saveHistory()">
      Save History
    </button>
  `
})
export class ExportMenuComponent implements OnInit {
  canExport$: Observable<boolean>;
  canSaveHistory$: Observable<boolean>;

  constructor(private capabilities: CapabilitiesService) {}

  ngOnInit() {
    this.canExport$ = this.capabilities.hasCapability('client_exports');
    this.canSaveHistory$ = this.capabilities.hasCapability('history_storage');
  }
}
```

### Edition Upgrade Prompt

```typescript
@Component({
  selector: 'app-feature-gate',
  template: `
    <div *ngIf="isPlusFeature && !hasPlusEdition">
      <p>This feature requires AI Operations Platform (AIOP) Plus edition.</p>
      <button (click)="showUpgradeInfo()">Learn More</button>
    </div>
    <ng-content *ngIf="!isPlusFeature || hasPlusEdition"></ng-content>
  `
})
export class FeatureGateComponent implements OnInit {
  @Input() requiredEdition: 'core' | 'plus' = 'core';

  isPlusFeature = false;
  hasPlusEdition = false;

  constructor(private capabilities: CapabilitiesService) {}

  async ngOnInit() {
    const caps = await this.capabilities.getCapabilities().toPromise();
    this.isPlusFeature = this.requiredEdition === 'plus';
    this.hasPlusEdition = caps.edition === 'plus';
  }
}
```

## Provider Configuration

The `providers` object indicates which provider implementations are active:

| Provider | Values | Description |
|----------|--------|-------------|
| `history` | `edge_only`, `governed` | Conversation history provider |
| `evidence` | `none`, `worm` | Evidence collection provider |
| `crypto` | `none`, `kms` | Cryptographic operations provider |

**Stateless Core v1 defaults:**
- `history`: `edge_only` (no server-side storage)
- `evidence`: `none` (no evidence collection)
- `crypto`: `none` (no field-level encryption)

## Best Practices

### 1. Cache Capabilities

```typescript
@Injectable({ providedIn: 'root' })
export class CapabilitiesService {
  private cache$ = new BehaviorSubject<CapabilitiesResponse | null>(null);
  private cacheTime = 0;
  private cacheTTL = 300000; // 5 minutes

  async getCapabilities(): Promise<CapabilitiesResponse> {
    const now = Date.now();
    if (this.cache$.value && (now - this.cacheTime) < this.cacheTTL) {
      return this.cache$.value;
    }

    const caps = await this.http.get<CapabilitiesResponse>(this.apiUrl).toPromise();
    this.cache$.next(caps);
    this.cacheTime = now;
    return caps;
  }
}
```

### 2. Handle Degraded Modes

```typescript
async function initializeApp() {
  try {
    const capabilities = await capabilitiesService.getCapabilities();
    configureApp(capabilities);
  } catch (error) {
    // Fallback to core-only mode
    console.warn('Failed to fetch capabilities, assuming core edition');
    configureApp({ edition: 'core', stateless: true });
  }
}
```

### 3. Feature Detection

```typescript
// Good: Check capability before using feature
if (await capabilities.hasCapability('client_exports')) {
  showExportButton();
}

// Bad: Assume feature availability
showExportButton(); // May fail if not available
```

## Error Handling

```typescript
try {
  const capabilities = await client.getCapabilities();
  // Process capabilities
} catch (error) {
  if (error.response?.status === 401) {
    // Re-authenticate
  } else if (error.response?.status === 429) {
    // Rate limited - wait and retry
  } else {
    // Log error and use safe defaults
    console.error('Failed to fetch capabilities:', error);
    useSafeDefaults();
  }
}
```

## Related Documentation

- [ADR-032: Capabilities & Edition Flags](../development/adrs/ADR-032-Capabilities-Edition-Flags.md)
- [ADR-030: No Transcripts; Run Manifests Only](../development/adrs/ADR-030-No-Transcripts-Run-Manifests.md)
- [Summaries API](summaries.md)
- [Run Manifests API](run-manifests.md)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-01 | Initial release for Stateless Core v1 |
