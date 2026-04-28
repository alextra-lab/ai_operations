# T6-F2: Tool Health Dashboard UI – Specification

**Status:** ✅ COMPLETED (2025-11-25)
**Date:** 2025-11-24
**Priority:** 🟡 HIGH
**Owner:** Tools Track
**Dependencies:** T4-F1 (Health API) ✅, T6-F1 (Tool Management UI) ✅
**Related ADRs:** ADR-001 (Hybrid Tools Architecture), ADR-012 (CSS Strategy)

---

## 1. Purpose

Provide an **admin-facing health monitoring dashboard** to visualize MCP tool availability and performance over time, using existing health APIs:

- `GET /api/v1/tools/health/status` - Overall health summary
- `GET /api/v1/tools/health/{tool_id}/history` - Per-tool health history
- `POST /api/v1/tools/health/{tool_id}/check` - Manual health check trigger

This dashboard enables operators to:

- Monitor overall tools health at a glance
- Identify offline or degraded tools quickly
- Inspect health history trends per tool
- Trigger manual health checks for verification

---

## 2. Scope

### 2.1 In Scope

**Core Features:**

- Health dashboard page at `/admin/tools/health`
- Summary cards showing overall health metrics
- Per-tool health status table
- Health history chart for selected tool
- Manual health check trigger per tool
- Auto-refresh capability (optional, configurable)

**Visualizations:**

- KPI cards (total, online, offline, health %)
- Health status table with sortable columns
- Line chart showing health over time (24h default)
- Response time chart (optional)

### 2.2 Out of Scope

- Alerting and notifications
- Health check configuration UI (managed via tool edit)
- Automated remediation workflows
- Integration with external monitoring systems

---

## 3. Actors & User Stories

### 3.1 Actors

- **Admin/Operator** – Monitors tool health and responds to outages
- **Platform Engineer** – Investigates performance degradation

### 3.2 Key User Stories

**US-1: Overall Health Overview**

- As an operator, I can see total tools, online/offline counts, and health percentage so I can quickly assess platform readiness.

**US-2: Identify Unhealthy Tools**

- As an operator, I can see which tools are offline or unhealthy in a table so I can prioritize investigation.

**US-3: Inspect Health History**

- As an operator, I can view health check history for a tool over the last N hours so I can understand if issues are intermittent or persistent.

**US-4: Trigger Manual Health Check**

- As an operator, I can trigger a manual health check on a tool so I can verify recovery after applying a fix.

**US-5: Monitor Response Times**

- As an engineer, I can see response time trends for tools so I can identify performance degradation before failures occur.

---

## 4. UI Design

### 4.1 Route & Layout

- **Route:** `/admin/tools/health`
- **Breadcrumb:** `Administration / Tools / Health`
- **Icon:** `monitor_heart` or `health_and_safety`
- **Layout:** ADR-012 layered page

**Page Structure:**

```
ToolHealthDashboardComponent
├─ Layer 2: Page Header
│  ├─ Title: "Tool Health"
│  ├─ Subtitle: "Monitor MCP tool availability and performance"
│  └─ Actions:
│     ├─ Auto-refresh toggle (on/off, 30s interval)
│     └─ Manual refresh button
│
├─ Summary Cards Row (4 cards)
│  ├─ Total Tools
│  ├─ Online Tools (green)
│  ├─ Offline Tools (red)
│  └─ Health % (gauge or progress bar)
│
└─ Layer 3: Content (split view)
   ├─ Left: Health Status Table (60% width)
   │  └─ All tools with current status
   └─ Right: Health History Panel (40% width)
      └─ Chart for selected tool
```

### 4.2 Summary Cards

**Card 1: Total Tools**

- Icon: `build`
- Value: `summary.total_tools`
- Label: "Total Tools"

**Card 2: Online**

- Icon: `check_circle` (green)
- Value: `summary.online`
- Label: "Online"
- Color: Green (#4caf50)

**Card 3: Offline**

- Icon: `error` (red)
- Value: `summary.offline`
- Label: "Offline"
- Color: Red (#f44336)

**Card 4: Health Percentage**

- Icon: `speed` (gauge)
- Value: `summary.health_percentage%`
- Label: "Health"
- Visual: Circular progress or linear gauge
- Color: Green (>80%), Yellow (50-80%), Red (<50%)

**Last Check Timestamp:**

- Below cards: "Last health check: {timestamp}" or "Never checked"

### 4.3 Health Status Table

**Columns:**

- Name
- Tool ID
- Status (Online/Offline/Disabled)
- Last Check (relative time)
- Response Time (ms, from last check)
- Actions (View History, Trigger Check)

**Status Indicators:**

- 🟢 Online: `is_enabled && is_healthy`
- 🔴 Offline: `is_enabled && !is_healthy`
- ⚪ Disabled: `!is_enabled`
- ⚫ Unknown: `last_health_check == null`

**Sorting:**

- Default: Sort by status (offline first), then name
- Allow sorting by any column

**Row Selection:**

- Click row to load history in right panel
- Highlight selected row

### 4.4 Health History Panel

**When No Tool Selected:**

- Message: "Select a tool to view health history"

**When Tool Selected:**

- Tool name and ID header
- Time range selector:
  - 1 hour
  - 6 hours
  - 24 hours (default)
  - 72 hours
  - 7 days
- Health status timeline chart:
  - X-axis: Time
  - Y-axis: Status (Online/Offline) or Response Time (ms)
  - Green line for online periods
  - Red line for offline periods
  - Grey for no data
- Latest check details:
  - Status
  - Response time
  - Timestamp
  - Error message (if failed)
- Actions:
  - "Trigger Health Check" button
  - "View Full Analytics" link → `/admin/tools/analytics?tool_id={id}`

---

## 5. API Integration

### 5.1 ToolHealthService

**File:** `src/frontend-angular/src/app/api/services/tool-health.service.ts`

```typescript
export interface HealthSummary {
  total_tools: number;
  online: number;
  offline: number;
  health_percentage: number;
  last_check: string | null;
}

export interface ToolHealthCheckRecord {
  id: string;
  tool_id: string;
  status: string;
  is_healthy: boolean;
  response_time_ms: number | null;
  error_message: string | null;
  checked_at: string;
}

@Injectable({ providedIn: 'root' })
export class ToolHealthService {
  private readonly baseUrl = '/api/v1/tools/health';

  constructor(private http: HttpClient) {}

  getOverallStatus(): Observable<HealthSummary> {
    return this.http.get<HealthSummary>(`${this.baseUrl}/status`);
  }

  getToolHistory(
    toolId: string,
    hours: number = 24
  ): Observable<ToolHealthCheckRecord[]> {
    return this.http.get<ToolHealthCheckRecord[]>(
      `${this.baseUrl}/${toolId}/history`,
      { params: { hours: hours.toString() } }
    );
  }

  triggerHealthCheck(toolId: string): Observable<ToolHealthCheckRecord> {
    return this.http.post<ToolHealthCheckRecord>(
      `${this.baseUrl}/${toolId}/check`,
      {}
    );
  }
}
```

### 5.2 Data Flow

**Tool List Source Decision:** `ToolHealthComponent` fetches its own tool list via `ToolAdminService.listTools()` (no runtime dependency on T6-F1 state). This ensures the health dashboard works when navigated to directly and always shows current data.

1. **On Init:**
   - Call `getOverallStatus()` → populate summary cards
   - Call `ToolAdminService.listTools()` → populate health table
   - No tool selected initially

2. **On Tool Selection (row click):**
   - Call `getToolHistory(tool.id, 24)` → render chart
   - Display latest check details

3. **On Time Range Change:**
   - Call `getToolHistory(tool.id, selectedHours)`
   - Update chart

4. **On "Trigger Check" Click:**
   - Call `triggerHealthCheck(tool.id)`
   - Show spinner
   - On success:
     - Refresh summary
     - Refresh history for that tool
     - Show snackbar: "Health check completed"

5. **On Auto-Refresh (if enabled):**
   - Every 30 seconds:
     - Refresh summary
     - Refresh history for selected tool (if any)

---

## 6. Component Architecture

```
src/frontend-angular/src/app/
├── api/services/
│   ├── tool-health.service.ts           (~150 lines)
│   └── tool-health.service.spec.ts      (~200 lines)
│
└── pages/admin/tool-health/
    ├── tool-health.component.ts              (~350 lines)
    ├── tool-health.component.html            (~300 lines)
    ├── tool-health.component.scss            (~150 lines)
    ├── tool-health.component.spec.ts         (~450 lines)
    └── components/
        ├── health-summary-cards/
        │   ├── health-summary-cards.component.ts      (~100 lines)
        │   ├── health-summary-cards.component.html    (~100 lines)
        │   └── health-summary-cards.component.scss    (~50 lines)
        └── health-history-chart/
            ├── health-history-chart.component.ts      (~200 lines)
            ├── health-history-chart.component.html    (~150 lines)
            └── health-history-chart.component.scss    (~50 lines)
```

**Service Location Note:** `ToolHealthService` follows the canonical pattern of placing API services in `src/frontend-angular/src/app/api/services/`.

**Charting Stack Note:** Reuse the same charting library and patterns as `gateway-metrics` component (Chart.js, lazy-loaded).

**Total Estimated:** ~2,250 lines

---

## 7. Charting Library

**Decision:** Use Chart.js with lazy-loading via `LibraryLoaderService` (already integrated in Gateway Metrics).

**Existing Implementation:**

- Gateway Metrics uses Chart.js loaded via `LibraryLoaderService.loadChartJS()`
- Patterns available in:
  - `gateway-latency-chart.component.ts` (line chart)
  - `gateway-token-chart.component.ts` (bar chart)
  - `gateway-cost-chart.component.ts` (area chart)

**Reuse Pattern:**

- Lazy-load Chart.js in `ngAfterViewInit()`
- Create chart instance with configuration
- Update chart on data changes
- Destroy chart in `ngOnDestroy()`

**Chart Configuration:**

```typescript
{
  type: 'line',
  data: {
    labels: timestamps,
    datasets: [
      {
        label: 'Health Status',
        data: healthValues, // 1 for online, 0 for offline
        borderColor: '#4caf50',
        backgroundColor: 'rgba(76, 175, 80, 0.1)',
        stepped: true, // Step chart for discrete status changes
      },
      {
        label: 'Response Time (ms)',
        data: responseTimes,
        borderColor: '#2196f3',
        yAxisID: 'y1',
      }
    ]
  },
  options: {
    responsive: true,
    scales: {
      y: { title: { text: 'Status' }, min: 0, max: 1 },
      y1: { title: { text: 'Response Time (ms)' }, position: 'right' }
    }
  }
}
```

---

## 8. Behavior & UX Details

### 8.1 Auto-Refresh

- Toggle in header: "Auto-refresh (30s)"
- When enabled:
  - Refresh summary every 30 seconds
  - Refresh selected tool history every 30 seconds
  - Show indicator: "Last updated: {time}"
- When disabled:
  - Manual refresh only

### 8.2 Manual Health Check

- Button per tool in table: "Check Now"
- On click:
  - Show spinner on that row
  - Call `triggerHealthCheck()`
  - On success:
    - Update tool status in table
    - Refresh summary cards
    - If tool is selected, refresh history
    - Show snackbar: "Health check completed for {tool.name}"
  - On error:
    - Show snackbar: "Health check failed: {error}"

### 8.3 Empty States

**No Tools Registered:**

- Icon: `build`
- Message: "No tools registered yet"
- Action: "Register Your First Tool" button → wizard

**All Tools Disabled:**

- Icon: `power_off`
- Message: "All tools are disabled"
- Suggestion: "Enable tools in Tool Management"

**No Health Data:**

- Icon: `schedule`
- Message: "No health checks recorded yet"
- Suggestion: "Health checks run automatically every {interval} seconds"

---

## 9. Accessibility

- Summary cards have `role="region"` with `aria-label`
- Table has proper `<thead>`, `<tbody>`, `<th scope="col">`
- Chart has textual description for screen readers
- Status icons have `aria-label` (not just color)
- Keyboard navigation for table and actions

---

## 10. Testing Strategy

### 10.1 Unit Tests

**ToolHealthService:**

- Calls correct endpoints with params
- Handles errors appropriately
- Maps responses correctly

**ToolHealthComponent:**

- Loads summary on init
- Displays summary cards correctly
- Loads tool list
- Handles tool selection
- Loads history for selected tool
- Triggers manual check
- Auto-refresh works (if enabled)
- Empty states render correctly

**Target Coverage:** 80%+

### 10.2 Integration Tests (Future)

- Navigate to `/admin/tools/health`
- Verify summary matches backend
- Select tool and verify history loads
- Trigger manual check and verify backend receives request

---

## 11. Acceptance Criteria

### 11.1 Functional

- [ ] `/admin/tools/health` accessible to admin users
- [ ] Summary cards reflect `/status` API data accurately
- [ ] Health table lists all tools with current status
- [ ] Clicking a tool row loads its health history
- [ ] History chart renders correctly for selected tool
- [ ] Time range selector updates chart
- [ ] Manual health check triggers and updates data
- [ ] Auto-refresh works when enabled
- [ ] Empty states display appropriately

### 11.2 Quality

- [ ] 80%+ unit test coverage
- [ ] All tests passing
- [ ] ADR-012 layout compliance
- [ ] WCAG 2.1 AA accessibility
- [ ] Clean compilation and linting
- [ ] Performance: summary load < 500ms, history load < 1s

### 11.3 Integration

- [ ] Linked from T6-F1 tool list (health icon/link)
- [ ] Can navigate back to tool management
- [ ] Uses existing `ToolHealthService` or creates new one
- [ ] Compatible with existing auth/RBAC

---

## 12. Implementation Estimate

**Effort:** 2-3 days (1 developer)

**Breakdown:**

- Day 1: Service + main component + summary cards (6-8 hours)
- Day 2: Health table + history chart integration (6-8 hours)
- Day 3: Manual check, auto-refresh, testing (4-6 hours)

**With AI Assist:** 1.5-2 days

---

## 13. Dependencies

### 13.1 Backend APIs (Already Exist)

✅ All required endpoints implemented in:

- `src/orchestrator/app/routers/tools_health.py` (3 endpoints)
- `src/orchestrator/app/services/tool_health_monitor.py`

### 13.2 Frontend Dependencies

✅ Existing:

- Chart.js (check if already used in Gateway Metrics)
- Angular Material
- Admin layout pattern

❌ Need to Create:

- `ToolHealthService` (if not exists)
- `ToolHealthComponent` and sub-components

---

## 14. Related Documentation

- **Backend API:** `src/orchestrator/app/routers/tools_health.py`
- **Architecture:** `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`
- **T6-F1 Spec:** `TOOLS_T6_F1_ADMIN_TOOLS_MANAGEMENT_SPEC.md`
- **ADR-012:** Layered Page Layout Pattern

---

**Status:** Ready for implementation after T6-F1
**Priority:** 🟡 HIGH - Operational visibility
**Next Step:** Implement after T6-F1 complete
