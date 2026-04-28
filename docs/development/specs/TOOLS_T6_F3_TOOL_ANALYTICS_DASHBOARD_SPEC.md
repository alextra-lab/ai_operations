# T6-F3: Tool Analytics Dashboard UI – Specification

**Status:** ✅ COMPLETED
**Date:** 2025-11-25
**Priority:** 🟡 HIGH
**Owner:** Tools Track
**Dependencies:** T4-F2 (Analytics API) ✅, T6-F1 (Tool Management UI) ✅
**Related ADRs:** ADR-001 (Hybrid Tools Architecture), ADR-012 (CSS Strategy)

### Completion Summary

**Completed:** November 25, 2025

**Deliverables:**

- ToolAnalyticsService with API client methods
- Main ToolAnalyticsComponent with ADR-012 layered layout
- UsageSummaryCardsComponent (4 metric cards)
- UsageByToolTableComponent with sorting
- UsageByCenterChartComponent (Chart.js, lazy-loaded)
- Time range filtering (1d, 7d, 30d, 90d)
- Export functionality (CSV/JSON)
- Routes and navigation integration
- 79 unit tests across 5 test suites

---

## 1. Purpose

Provide an **admin-facing analytics dashboard** for monitoring tool usage, cost, and performance trends, using existing analytics APIs:

- `GET /api/v1/tools/analytics/usage/summary` - Per-tool usage statistics
- `GET /api/v1/tools/analytics/usage/by-center` - Center-based aggregation
- `GET /api/v1/tools/analytics/audit` - Detailed audit trail (optional)

This dashboard enables:

- Understanding which tools are most/least used
- Tracking estimated costs per tool and center
- Identifying performance bottlenecks
- Supporting capacity planning and governance decisions

---

## 2. Scope

### 2.1 In Scope

**Core Features:**

- Analytics dashboard page at `/admin/tools/analytics`
- Usage summary per tool (table)
- Usage by center visualization (chart)
- Time range filtering (presets + custom)
- Export functionality (CSV/JSON)

**Metrics Displayed:**

- Total invocations per tool
- Success rate (%)
- Average duration (ms)
- Total estimated cost
- Usage trends over time

### 2.2 Out of Scope

- Real-time streaming metrics
- Per-invocation audit log viewer (separate page if needed)
- Cost allocation and chargeback workflows
- Predictive analytics and forecasting

---

## 3. Actors & User Stories

### 3.1 Actors

- **Admin/Operations** – Monitors usage and cost patterns
- **Engineering Lead** – Evaluates tool effectiveness and cost impact
- **Finance/Governance** – Reviews cost allocation

### 3.2 Key User Stories

**US-1: See Tool Usage Summary**

- As an admin, I can see how often each tool is invoked and its success rate so I can identify heavily-used or problematic tools.

**US-2: Understand Cost Impact**

- As an admin, I can see estimated cost per tool so I can identify expensive tools and optimize usage.

**US-3: See Usage by Center**

- As an admin, I can see which centers are driving tool usage and cost so I can allocate resources appropriately.

**US-4: Filter by Time Range**

- As an admin, I can filter analytics to a specific time range (e.g., last 7 days, last month) so I can compare behavior over time.

**US-5: Export Data**

- As an admin, I can export usage data as CSV or JSON so I can analyze it in external tools or share with stakeholders.

**US-6: Identify Performance Issues**

- As an engineer, I can see average duration trends per tool so I can identify performance degradation.

---

## 4. UI Design

### 4.1 Route & Layout

- **Route:** `/admin/tools/analytics`
- **Breadcrumb:** `Administration / Tools / Analytics`
- **Icon:** `analytics` or `bar_chart`
- **Layout:** ADR-012 layered page

**Page Structure:**

```
ToolAnalyticsDashboardComponent
├─ Layer 2: Page Header
│  ├─ Title: "Tool Analytics"
│  ├─ Subtitle: "Usage, reliability, and cost insights"
│  └─ Actions:
│     ├─ Date range picker (presets + custom)
│     ├─ Export button (CSV/JSON dropdown)
│     └─ Refresh button
│
├─ Summary Cards Row (4 cards)
│  ├─ Total Invocations
│  ├─ Avg Success Rate
│  ├─ Total Cost
│  └─ Most Used Tool
│
└─ Layer 3: Content (tabs or sections)
   ├─ Tab 1: Usage by Tool (table)
   ├─ Tab 2: Usage by Center (chart)
   └─ Tab 3: Timeline (optional, line chart)
```

### 4.2 Summary Cards

**Card 1: Total Invocations**

- Icon: `call_made`
- Value: Sum of all `total_calls`
- Label: "Total Invocations"
- Subtext: "In selected period"

**Card 2: Average Success Rate**

- Icon: `check_circle`
- Value: Weighted average of success rates
- Label: "Avg Success Rate"
- Color: Green (>95%), Yellow (90-95%), Red (<90%)

**Card 3: Total Cost**

- Icon: `euro` or `attach_money`
- Value: Sum of all `total_cost`
- Label: "Estimated Cost"
- Format: €X.XXXX

**Card 4: Most Used Tool**

- Icon: `trending_up`
- Value: Tool name with highest `total_calls`
- Label: "Most Used Tool"
- Subtext: "{count} invocations"

### 4.3 Usage by Tool Table

**Columns:**

- Tool Name
- Tool ID
- Total Calls
- Successful Calls
- Success Rate (%)
- Avg Duration (ms)
- Total Cost (€)

**Sorting:**

- Default: Sort by total calls (descending)
- Allow sorting by any column

**Row Actions:**

- Click row to drill down (future: per-tool detail view)

**Data Source:** `GET /usage/summary` with date filters

### 4.4 Usage by Center Chart

**Chart Type:** Bar chart (horizontal or vertical)

**Charting Stack:** Use Chart.js with lazy-loading via `LibraryLoaderService` (same as Gateway Metrics). Reuse patterns from `gateway-token-chart.component.ts`.

**Configuration:**

- X-axis: Center ID
- Y-axis: Total calls or total cost (toggle)
- Color: Gradient based on value
- Tooltip: Center ID, calls, cost

**Toggle:** Switch between "Calls" and "Cost" view

**Data Source:** `GET /usage/by-center?days={N}`

### 4.5 Timeline Chart (Optional)

**Chart Type:** Line chart

**Configuration:**

- X-axis: Date/time
- Y-axis: Invocations per hour
- Multiple lines (one per tool, top 5 tools)
- Legend: Tool names

**Data Source:** Would require new backend endpoint (out of scope for initial version)

---

## 5. Date Range Filtering

### 5.1 Presets

- Today (last 24 hours)
- Last 7 days
- Last 30 days
- Last 90 days
- Custom (date picker)

### 5.2 Implementation

```typescript
export enum DateRangePreset {
  TODAY = 'today',
  WEEK = 'week',
  MONTH = 'month',
  QUARTER = 'quarter',
  CUSTOM = 'custom',
}

interface DateRange {
  start: Date;
  end: Date;
  preset: DateRangePreset;
}

// When preset changes:
onPresetChange(preset: DateRangePreset): void {
  const now = new Date();
  let start: Date;

  switch (preset) {
    case DateRangePreset.TODAY:
      start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      break;
    case DateRangePreset.WEEK:
      start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      break;
    case DateRangePreset.MONTH:
      start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      break;
    case DateRangePreset.QUARTER:
      start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      break;
    default:
      return; // Custom handled separately
  }

  this.dateRange = { start, end: now, preset };
  this.loadAnalytics();
}
```

---

## 6. Export Functionality

### 6.1 Export Formats

**CSV Export:**

- Headers: Tool Name, Tool ID, Total Calls, Success Rate, Avg Duration, Total Cost
- One row per tool
- Filename: `tool-analytics-{date}.csv`

**JSON Export:**

- Complete analytics data structure
- Includes metadata (date range, export timestamp)
- Filename: `tool-analytics-{date}.json`

### 6.2 Implementation

```typescript
exportToCSV(): void {
  const csv = this.convertToCSV(this.usageSummary);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tool-analytics-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}

exportToJSON(): void {
  const data = {
    exported_at: new Date().toISOString(),
    date_range: this.dateRange,
    usage_summary: this.usageSummary,
    usage_by_center: this.usageByCenter,
  };
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tool-analytics-${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  window.URL.revokeObjectURL(url);
}
```

---

## 7. Component Architecture

```
src/frontend-angular/src/app/
├── api/services/
│   ├── tool-analytics.service.ts         (~200 lines)
│   └── tool-analytics.service.spec.ts    (~250 lines)
│
└── pages/admin/tool-analytics/
    ├── tool-analytics.component.ts           (~400 lines)
    ├── tool-analytics.component.html         (~350 lines)
    ├── tool-analytics.component.scss         (~150 lines)
    ├── tool-analytics.component.spec.ts      (~500 lines)
    └── components/
        ├── usage-summary-cards/
        │   ├── usage-summary-cards.component.ts      (~120 lines)
        │   ├── usage-summary-cards.component.html    (~120 lines)
        │   └── usage-summary-cards.component.scss    (~50 lines)
        ├── usage-by-tool-table/
        │   ├── usage-by-tool-table.component.ts      (~150 lines)
        │   ├── usage-by-tool-table.component.html    (~100 lines)
        │   └── usage-by-tool-table.component.scss    (~50 lines)
        └── usage-by-center-chart/
            ├── usage-by-center-chart.component.ts    (~200 lines)
            ├── usage-by-center-chart.component.html  (~100 lines)
            └── usage-by-center-chart.component.scss  (~50 lines)
```

**Service Location Note:** `ToolAnalyticsService` follows the canonical pattern of placing API services in `src/frontend-angular/src/app/api/services/`.

**Charting Stack Note:** Reuse the same charting library and patterns as `gateway-metrics` component (Chart.js, lazy-loaded).

**Total Estimated:** ~2,700 lines

---

## 8. Testing Strategy

### 8.1 Unit Tests

**ToolAnalyticsService:**

- Builds correct query params from date range
- Handles errors
- Maps responses

**ToolAnalyticsComponent:**

- Loads summary on init
- Applies date range filters
- Exports data correctly
- Handles empty states

**Target Coverage:** 80%+

---

## 9. Acceptance Criteria

- [ ] `/admin/tools/analytics` accessible to admin users
- [ ] Summary cards display aggregated metrics
- [ ] Usage-by-tool table shows per-tool statistics
- [ ] Usage-by-center chart renders correctly
- [ ] Date range filtering works
- [ ] Export to CSV/JSON works
- [ ] 80%+ unit test coverage
- [ ] ADR-012 compliant
- [ ] WCAG 2.1 AA accessible

---

## 10. Implementation Estimate

**Effort:** 2-3 days (1 developer)
**With AI Assist:** 1.5-2 days

---

## 11. Related Documentation

- **Backend API:** `src/orchestrator/app/routers/tools_analytics.py`
- **T6-F1 Spec:** `TOOLS_T6_F1_ADMIN_TOOLS_MANAGEMENT_SPEC.md`
- **Architecture:** `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`

---

**Status:** Ready for implementation after T6-F1
**Priority:** 🟡 HIGH - Cost visibility
**Next Step:** Implement after T6-F1 complete
