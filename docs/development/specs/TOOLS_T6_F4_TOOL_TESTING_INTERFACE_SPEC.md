# T6-F4: Tool Testing Interface UI – Specification

**Status:** ✅ COMPLETED
**Date:** 2025-11-25
**Priority:** 🟢 MEDIUM
**Owner:** Tools Track
**Dependencies:** T4-F4 (Testing API) ✅, T6-F1 (Tool Management UI) ✅
**Related ADRs:** ADR-001 (Hybrid Tools Architecture), ADR-012 (CSS Strategy)

### Completion Summary

**Completed:** November 25, 2025

**Deliverables:**

- ToolTestingComponent with dynamic parameter forms
- ToolTestingService (API client for testing endpoints)
- TestResultViewerComponent (JSON viewer, error display)
- Tool selector with schema-based form generation
- Test execution with validation
- Test history display (last 10 tests)
- Developer tools navigation integration
- 66 unit tests across 3 test suites

---

## 1. Purpose

Provide a **developer/admin UI** for testing MCP tools before or after they are integrated into use cases, using existing testing APIs:

- `POST /api/v1/tools/test/execute` - Execute tool with parameters
- `POST /api/v1/tools/test/validate-parameters` - Validate parameters without execution

This interface enables:

- Verifying tool connectivity and behavior
- Testing parameter schemas
- Debugging tool integration issues
- Validating tool responses before production use

---

## 2. Scope

### 2.1 In Scope

**Core Features:**

- Tool testing page at `/admin/tools/test` or `/dev/tools/test`
- Tool selection dropdown
- Parameter input (JSON editor)
- Execute test button
- Validate parameters button
- Result display (success/error, duration, response data)
- Test history (last N tests in session)

**User Roles:**

- Admin (full access)
- Developer (full access)

### 2.2 Out of Scope

- Saved test scenarios/templates
- Automated test suites
- Load testing capabilities
- Test result persistence (beyond session)

---

## 3. Actors & User Stories

### 3.1 Actors

- **Developer** – Tests tools during use case development
- **Admin/Operator** – Verifies tools in staging/production
- **Platform Engineer** – Debugs tool integration issues

### 3.2 Key User Stories

**US-1: Select Tool to Test**

- As a developer, I can select a registered tool from a dropdown so I can test it.

**US-2: Enter Test Parameters**

- As a developer, I can enter parameters for the tool call using a JSON editor so I can test different scenarios.

**US-3: Execute Test Call**

- As a developer, I can execute a test call and see the raw result, duration, and any errors so I can verify tool behavior.

**US-4: Validate Parameters**

- As a developer, I can validate parameters against the tool's schema without executing so I can catch errors early.

**US-5: View Test History**

- As a developer, I can see my recent test executions in the session so I can compare results.

---

## 4. UI Design

### 4.1 Route & Layout

- **Route:** `/dev/tools/test` (Developer Tools section)
- **Breadcrumb:** `Developer Tools / Tool Testing`
- **Icon:** `science` or `bug_report`
- **Layout:** ADR-012 layered page
- **Rationale:** Developers are primary users; aligns with existing `/dev/query-tools` placement

**Page Structure:**

```
ToolTestingComponent
├─ Layer 2: Page Header
│  ├─ Title: "Tool Testing"
│  ├─ Subtitle: "Execute test calls and validate parameters"
│  └─ Actions:
│     └─ Clear history button
│
├─ Test Configuration Panel (left, 50%)
│  ├─ Tool selector dropdown
│  ├─ Tool name input (for MCP sub-tool selection)
│  ├─ Parameters JSON editor
│  └─ Action buttons:
│     ├─ Validate Parameters
│     └─ Execute Test
│
└─ Results Panel (right, 50%)
   ├─ Current test result (if any)
   └─ Test history (collapsible list)
```

### 4.2 Tool Selector

**Dropdown:**

- Label: "Select Tool"
- Options: All enabled tools (name + tool_id)
- Grouped by category (optional)
- Search/filter within dropdown

**On Selection:**

- Load tool details (parameters schema if available)
- Pre-fill JSON editor with example parameters (if schema available)
- Clear previous results

### 4.3 Parameters Editor

**JSON Editor:**

- Use Monaco Editor or simple textarea with JSON validation
- Syntax highlighting
- Line numbers
- Validation indicator (valid/invalid JSON)

**Helper:**

- "Load Example" button (if parameters_schema available)
- "Clear" button

**Example Pre-fill:**

```json
{
  "query": "example search query",
  "limit": 10
}
```

### 4.4 Action Buttons

**Validate Parameters Button:**

- Calls `POST /test/validate-parameters`
- Shows validation result:
  - ✅ Valid: "Parameters are valid"
  - ❌ Invalid: "Validation errors: {errors}"
- Does not execute tool

**Execute Test Button:**

- Disabled if:
  - No tool selected
  - Parameters are invalid JSON
- Shows spinner while executing
- Calls `POST /test/execute`
- Displays result in results panel

### 4.5 Results Panel

**Current Test Result:**

- Status badge (success/error)
- Duration: "{X}ms"
- Timestamp: "Executed at {time}"
- Response data:
  - JSON viewer (collapsible, syntax highlighted)
  - Copy button
- Error message (if failed)

**Test History:**

- Collapsible list (last 10 tests in session)
- Each entry:
  - Tool name
  - Status icon
  - Duration
  - Timestamp
  - Click to view full result

---

## 5. API Integration

### 5.1 ToolTestingService

**File:** `src/frontend-angular/src/app/api/services/tool-testing.service.ts`

```typescript
export interface TestExecutionRequest {
  tool_id: string;
  tool_name: string;
  parameters: Record<string, any>;
}

export interface TestExecutionResult {
  success: boolean;
  status: string;
  result?: any;
  error?: string;
  duration_ms: number;
}

export interface ParameterValidationRequest {
  tool_id: string;
  tool_name: string;
  parameters: Record<string, any>;
}

export interface ParameterValidationResult {
  valid: boolean;
  errors?: string[];
}

@Injectable({ providedIn: 'root' })
export class ToolTestingService {
  private readonly baseUrl = '/api/v1/tools/test';

  constructor(private http: HttpClient) {}

  executeTest(request: TestExecutionRequest): Observable<TestExecutionResult> {
    return this.http.post<TestExecutionResult>(
      `${this.baseUrl}/execute`,
      request
    );
  }

  validateParameters(
    request: ParameterValidationRequest
  ): Observable<ParameterValidationResult> {
    return this.http.post<ParameterValidationResult>(
      `${this.baseUrl}/validate-parameters`,
      request
    );
  }
}
```

### 5.2 Test History Management

**Session Storage:**

```typescript
interface TestHistoryEntry {
  id: string; // UUID
  tool_id: string;
  tool_name: string;
  parameters: Record<string, any>;
  result: TestExecutionResult;
  timestamp: Date;
}

class TestHistoryManager {
  private history: TestHistoryEntry[] = [];
  private maxHistory = 10;

  addEntry(entry: TestHistoryEntry): void {
    this.history.unshift(entry);
    if (this.history.length > this.maxHistory) {
      this.history = this.history.slice(0, this.maxHistory);
    }
  }

  getHistory(): TestHistoryEntry[] {
    return this.history;
  }

  clear(): void {
    this.history = [];
  }
}
```

---

## 6. Component Architecture

```
src/frontend-angular/src/app/
├── api/services/
│   ├── tool-testing.service.ts           (~120 lines)
│   └── tool-testing.service.spec.ts      (~150 lines)
│
└── pages/dev/tool-testing/
    ├── tool-testing.component.ts             (~350 lines)
    ├── tool-testing.component.html           (~300 lines)
    ├── tool-testing.component.scss           (~120 lines)
    ├── tool-testing.component.spec.ts        (~400 lines)
    └── components/
        ├── test-result-viewer/
        │   ├── test-result-viewer.component.ts       (~150 lines)
        │   ├── test-result-viewer.component.html     (~120 lines)
        │   └── test-result-viewer.component.scss     (~50 lines)
        └── test-history-list/
            ├── test-history-list.component.ts        (~100 lines)
            ├── test-history-list.component.html      (~80 lines)
            └── test-history-list.component.scss      (~40 lines)
```

**Service Location Note:** `ToolTestingService` follows the canonical pattern of placing API services in `src/frontend-angular/src/app/api/services/`.

**Route Decision:** Testing interface is placed under `/dev/tools/test` (Developer Tools section) as developers are the primary users. This aligns with existing Query Developer Tools at `/dev/query-tools`.

**Total Estimated:** ~1,980 lines

---

## 7. Behavior & UX Details

### 7.1 Parameter Validation

- Validate JSON syntax on blur
- Show inline error if invalid JSON
- Disable execute button if invalid
- Optional: Schema-based validation indicator

### 7.2 Test Execution Pattern (Pseudocode)

```typescript
executeTest(): void {
  if (!this.selectedTool || !this.isValidJSON(this.parameters)) {
    return;
  }

  this.isExecuting = true;
  this.currentResult = null;

  const request: TestExecutionRequest = {
    tool_id: this.selectedTool.id,
    tool_name: this.toolName || this.selectedTool.tool_id,
    parameters: JSON.parse(this.parameters),
  };

  this.testingService.executeTest(request).subscribe({
    next: (result) => {
      this.currentResult = result;
      this.addToHistory({
        id: this.generateId(),
        tool_id: this.selectedTool.id,
        tool_name: request.tool_name,
        parameters: request.parameters,
        result,
        timestamp: new Date(),
      });

      if (result.success) {
        this.snackBar.open('Test executed successfully', 'Close', { duration: 3000 });
      } else {
        this.snackBar.open('Test execution failed', 'Close', { duration: 5000 });
      }
      this.isExecuting = false;
    },
    error: (error: any) => {
      this.snackBar.open(
        error.error?.detail || 'Test execution error',
        'Close',
        { duration: 5000 }
      );
      this.isExecuting = false;
    },
  });
}
```

**Note:** Adapt observable handling to match project standards (subscribe, firstValueFrom, or async pipe).

### 7.3 Empty States

**No Tool Selected:**

- Message: "Select a tool to begin testing"

**No Test Results:**

- Message: "Execute a test to see results"

**No Test History:**

- Message: "Your test history will appear here"

---

## 8. Accessibility

- JSON editor has `aria-label="Tool parameters JSON"`
- Execute button has clear label and disabled state
- Results panel has `role="region"` with `aria-label="Test results"`
- Status indicators use text + icons (not color alone)

---

## 9. Testing Strategy

### 9.1 Unit Tests

**ToolTestingService:**

- Calls correct endpoints
- Handles errors
- Maps responses

**ToolTestingComponent:**

- Tool selection updates state
- Parameter validation works
- Execute test calls service
- Results display correctly
- History management works

**Target Coverage:** 80%+

---

## 10. Acceptance Criteria

- [ ] `/dev/tools/test` or `/admin/tools/test` accessible to developer/admin
- [ ] Can select a tool and see its details
- [ ] Can enter parameters as JSON
- [ ] Can validate parameters without execution
- [ ] Can execute test and see result
- [ ] Test history shows last 10 tests
- [ ] Error handling works for all scenarios
- [ ] 80%+ unit test coverage
- [ ] ADR-012 compliant
- [ ] WCAG 2.1 AA accessible

---

## 11. Implementation Estimate

**Effort:** 1-2 days (1 developer)
**With AI Assist:** 1 day

---

## 12. Related Documentation

- **Backend API:** `src/orchestrator/app/routers/tools_testing.py`
- **T6-F1 Spec:** `TOOLS_T6_F1_ADMIN_TOOLS_MANAGEMENT_SPEC.md`
- **Architecture:** `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`

---

**Status:** Ready for implementation after T6-F1
**Priority:** 🟢 MEDIUM - Developer productivity
**Next Step:** Implement after T6-F1 complete
