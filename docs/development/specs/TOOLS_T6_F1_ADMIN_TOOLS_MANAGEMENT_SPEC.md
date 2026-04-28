# T6-F1: Admin Tools Management UI – Specification

**Status:** 📋 PLANNED
**Date:** 2025-11-24
**Priority:** 🔴 CRITICAL
**Owner:** Tools Track
**Dependencies:** T1-F3 (Admin API) ✅, T5-F2 (Registration Wizard) ✅
**Related ADRs:** ADR-001 (Hybrid Tools Architecture), ADR-012 (CSS Strategy), ADR-056 (MCP Tool Registration Workflow)

---

## 1. Purpose

Provide the **primary admin UI** for managing MCP tools after registration. This is the **critical missing piece** that blocks production use of the Tools Track.

**Without this UI, admins cannot:**

- See what tools are registered
- Enable or disable tools
- Check tool health status
- Edit tool configuration
- Delete tools
- Navigate from registration wizard success

**This spec defines the `/admin/tools` page** that serves as the operational control surface for the entire Tools Track.

---

## 2. Scope

### 2.1 In Scope

**Core Functionality:**

- Tools list page at `/admin/tools` with Material table
- Enable/disable toggles per tool
- Health status indicators (online/offline/unknown)
- CRUD operations (view, edit, delete)
- Navigation to registration wizard
- Integration with existing admin APIs (15 endpoints available)

**Dialogs:**

- Tool Details Dialog (read-only view of complete configuration)
- Tool Edit Dialog (edit metadata, limits, non-MCP fields)
- Tool Delete Confirmation Dialog (with safety checks)

**Service Layer:**

- `ToolAdminService` - API client for admin operations
- Integration with `ToolRegistrationService` for navigation

### 2.2 Out of Scope (Future Features)

- Full health history charts (T6-F2)
- Usage analytics dashboard (T6-F3)
- Tool testing interface (T6-F4)
- Permission matrix editor (T6-F5)
- Bulk operations (multi-select)
- Tool cloning/duplication

---

## 3. Actors & User Stories

### 3.1 Actors

- **Admin** – Full control over tools (create via wizard, update, delete, enable/disable)
- **Platform Operator** – Monitors tool status and takes corrective action

### 3.2 Key User Stories

**US-1: List All Tools**

- As an admin, I can see all registered tools in a table with key metadata (name, ID, category, status, health) so I can quickly understand what is available.

**US-2: Enable/Disable Tools**

- As an admin, I can toggle a tool's enabled status so I can control whether it is available for use case execution without deleting it.

**US-3: View Tool Details**

- As an admin, I can open a details view for any tool so I can inspect its complete configuration (MCP settings, capabilities, limits, health summary).

**US-4: Edit Tool Configuration**

- As an admin, I can edit non-destructive tool properties (name, description, tags, timeouts, rate limits) so I can refine behavior without re-registration.

**US-5: Delete Tools**

- As an admin, I can delete tools that are no longer needed, with clear warnings about impact, so I can keep the registry clean.

**US-6: Navigate from Registration**

- As an admin, when I complete the registration wizard, I am redirected to `/admin/tools` so I can immediately see and manage the newly registered tool.

**US-7: Filter and Search**

- As an admin, I can filter tools by category, enabled status, health status, and search by name/ID so I can quickly find specific tools.

---

## 4. UI Design

### 4.1 Route & Navigation

- **Route:** `/admin/tools`
- **Breadcrumb:** `Administration / Tools`
- **Icon:** `build` or `construction`
- **Nav Position:** Admin section, between "Audit Logs" and existing items

**Add to `app.routes.ts`:**

```typescript
{
  path: 'tools',
  loadComponent: () =>
    import('./pages/admin/tool-management/tool-management.component').then(
      (m) => m.ToolManagementComponent
    ),
  data: { breadcrumb: 'Tool Management', icon: 'build' },
}
```

### 4.2 Page Layout (ADR-012 Compliant)

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Page Header (Fixed)                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Tool Management                                         │ │
│ │ Administer MCP tools, health, and availability         │ │
│ │                                                         │ │
│ │ [Register New Tool]  [Refresh]                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Filters Row:                                                │
│ [Category ▼] [✓ Enabled Only] [✓ Healthy Only] [Search..] │
│ 15 tools total                                              │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Content Area (Scrollable)                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Name │ ID │ Category │ Status │ Health │ Actions │ │ │
│ │ ├─────────────────────────────────────────────────────┤ │ │
│ │ │ Qdrant │ qdrant_vec │ vector_db │ ⚫ On │ ✓ │ 👁 ✏ 🗑 │ │ │
│ │ │ Elastic │ elastic_s │ database │ ⚪ Off │ — │ 👁 ✏ 🗑 │ │ │
│ │ │ Web Fetch │ web_fetch │ scraping │ ⚫ On │ ✗ │ 👁 ✏ 🗑 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Footer (Fixed)                                     │
│ [< Previous] Page 1 of 2 [Next >]                          │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Table Columns

| Column | Data | Display | Sortable |
|--------|------|---------|----------|
| **Name** | `tool.name` | Text + icon | Yes |
| **Tool ID** | `tool.tool_id` | Monospace text | Yes |
| **Category** | `tool.category` | Chip with color | Yes |
| **Provider** | `tool.provider` | Text or "—" | Yes |
| **Status** | `tool.is_enabled` | Slide toggle | No |
| **Health** | `tool.is_healthy` | Icon (✓/✗/—) + tooltip | Yes |
| **Last Check** | `tool.last_health_check` | Relative time | Yes |
| **Actions** | — | Icon buttons | No |

**Status Toggle:**

- Green slide toggle when enabled
- Grey when disabled
- Tooltip: "Click to enable/disable"
- Calls `POST /enable` or `/disable` on change

**Health Icon:**

- ✅ Green check: `is_enabled && is_healthy`
- ❌ Red X: `is_enabled && !is_healthy`
- ⚪ Grey dash: `!is_enabled` or `last_health_check == null`
- Tooltip: "Last checked: {timestamp}" or "Never checked"

**Actions:**

- 👁 View Details (eye icon) → Opens details dialog
- ✏ Edit (pencil icon) → Opens edit dialog
- 🗑 Delete (trash icon) → Opens delete confirmation

### 4.4 Filters & Search

**Filter Controls:**

- **Category Dropdown:**
  - Options: "All Categories", "Database", "Vector DB", "Web Scraping", "Reasoning", "Documentation", "Custom"
  - Default: "All Categories"
- **Enabled Only Toggle:**
  - Checkbox or slide toggle
  - Default: unchecked (show all)
- **Healthy Only Toggle:**
  - Checkbox or slide toggle
  - Default: unchecked (show all)
- **Search Input:**
  - Placeholder: "Search by name or ID..."
  - Debounced (300ms)
  - Searches `tool.name` and `tool.tool_id`

**Filter Behavior:**

- Client-side filtering for responsiveness
- Show count: "15 tools total" or "3 of 15 tools shown"

---

## 5. Dialogs

### 5.1 Tool Details Dialog

**Trigger:** Click view icon
**Size:** Large (800px width)
**Mode:** Read-only

**Content Sections:**

**Basic Information:**

- Tool ID (slug)
- Name
- Description
- Category
- Provider
- Version
- Documentation URL
- Tags (chips)

**MCP Configuration:**

- Server Type (STDIO/HTTP/SSE)
- Endpoint or Command (formatted)
- Protocol Version
- Timeout (seconds)

**Capabilities (if discovered):**

- JSON viewer (collapsible, syntax highlighted)
- Tool count summary

**Parameters Schema (if available):**

- JSON viewer (collapsible)

**Limits & Configuration:**

- Rate limit per minute
- Max concurrent calls
- Health check interval

**Health Summary:**

- Current status (enabled/disabled, healthy/unhealthy)
- Last health check timestamp
- Last response time (if available)
- Link: "View Full Health History" → `/admin/tools/health?tool_id={id}` (opens T6-F2 dashboard)

**Note:** Full health history charting is implemented in T6-F2 (Health Dashboard). T6-F1 only shows current status and provides navigation link.

**Usage Summary (optional):**

- Total invocations (last 30 days)
- Success rate
- Link: "View Full Analytics" → `/admin/tools/analytics?tool_id={id}`

**Actions:**

- Close button
- Edit button (opens edit dialog)

### 5.2 Tool Edit Dialog

**Trigger:** Click edit icon or "Edit" from details
**Size:** Medium (600px width)
**Mode:** Editable form

**Editable Fields:**

- Name (text input, required)
- Description (textarea, optional)
- Tags (chip input, optional)
- Timeout seconds (number input, 1-300, required)
- Rate limit per minute (number input, >= 1 or null, optional)
- Health check interval (number input, >= 60, optional)

**Non-Editable (Display Only):**

- Tool ID
- Category
- Purpose
- Service Location
- MCP Server Type
- MCP Endpoint/Command
- Provider

**Validation:**

- Name: required, 1-255 chars
- Timeout: 1-300 seconds
- Rate limit: null or >= 1
- Health interval: null or >= 60

**Actions:**

- Cancel (close without saving)
- Save (PUT `/api/v1/admin/tools/{tool_id}`)

**On Save Success:**

- Close dialog
- Refresh tools list
- Show snackbar: "Tool '{name}' updated successfully"

**On Save Error:**

- Show inline error in dialog
- Keep dialog open for correction

### 5.3 Tool Delete Confirmation Dialog

**Trigger:** Click delete icon
**Size:** Small (400px width)
**Mode:** Confirmation

**Content:**

- Warning icon (red)
- Title: "Delete Tool?"
- Message:

  ```
  This will permanently delete the tool:

  Name: {tool.name}
  Tool ID: {tool.tool_id}

  This action cannot be undone. Ensure no active use cases
  depend on this tool.
  ```

- Checkbox: "I understand the impact"
- Tool name confirmation input (type tool ID to confirm)

**Actions:**

- Cancel (close without deleting)
- Delete (DELETE `/api/v1/admin/tools/{tool_id}`, disabled until confirmed)

**On Delete Success:**

- Close dialog
- Remove tool from list (client-side)
- Show snackbar: "Tool '{name}' deleted successfully"

**On Delete Error:**

- Show snackbar with error
- Keep dialog open

---

## 6. API Integration

### 6.1 Backend Endpoints (Already Exist)

**Tool CRUD:**

```
GET    /api/v1/admin/tools                    # List tools
GET    /api/v1/admin/tools/{tool_id}          # Get tool details
PUT    /api/v1/admin/tools/{tool_id}          # Update tool
DELETE /api/v1/admin/tools/{tool_id}          # Delete tool
POST   /api/v1/admin/tools/{tool_id}/enable   # Enable tool
POST   /api/v1/admin/tools/{tool_id}/disable  # Disable tool
```

**Query Parameters for List:**

- `category`: ToolCategory enum (optional)
- `enabled_only`: boolean (default false)
- `healthy_only`: boolean (default false)

### 6.2 ToolAdminService

**File:** `src/frontend-angular/src/app/api/services/tool-admin.service.ts`

```typescript
@Injectable({ providedIn: 'root' })
export class ToolAdminService {
  private readonly baseUrl = '/api/v1/admin/tools';

  constructor(private http: HttpClient) {}

  listTools(
    category?: ToolCategory,
    enabledOnly?: boolean,
    healthyOnly?: boolean
  ): Observable<ToolListItem[]> {
    let params = new HttpParams();
    if (category) params = params.set('category', category);
    if (enabledOnly) params = params.set('enabled_only', 'true');
    if (healthyOnly) params = params.set('healthy_only', 'true');

    return this.http.get<ToolListItem[]>(this.baseUrl, { params });
  }

  getTool(toolId: string): Observable<Tool> {
    return this.http.get<Tool>(`${this.baseUrl}/${toolId}`);
  }

  updateTool(toolId: string, updates: ToolUpdate): Observable<Tool> {
    return this.http.put<Tool>(`${this.baseUrl}/${toolId}`, updates);
  }

  deleteTool(toolId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${toolId}`);
  }

  enableTool(toolId: string): Observable<Tool> {
    return this.http.post<Tool>(`${this.baseUrl}/${toolId}/enable`, {});
  }

  disableTool(toolId: string): Observable<Tool> {
    return this.http.post<Tool>(`${this.baseUrl}/${toolId}/disable`, {});
  }
}
```

### 6.3 Data Models

**Reuse existing from `tool.models.ts`:**

- `ToolListItem` - For table rows
- `Tool` - For details/edit
- `ToolCategory` - Enum for filters
- `ToolStatus` - Enum for status display

**Add if needed:**

```typescript
export interface ToolUpdate {
  name?: string;
  description?: string;
  tags?: string[];
  timeout_seconds?: number;
  rate_limit_per_minute?: number | null;
  health_check_interval_seconds?: number | null;
}

export interface ToolFilters {
  category: ToolCategory | null;
  enabledOnly: boolean;
  healthyOnly: boolean;
  searchTerm: string;
}
```

---

## 7. Component Architecture

### 7.1 File Structure

```
src/frontend-angular/src/app/
├── api/services/
│   ├── tool-admin.service.ts            (API client, ~150 lines)
│   └── tool-admin.service.spec.ts       (service tests, ~200 lines)
│
└── pages/admin/tool-management/
    ├── tool-management.component.ts         (main component, ~300 lines)
    ├── tool-management.component.html       (table + filters, ~250 lines)
    ├── tool-management.component.scss       (ADR-012 styles, ~100 lines)
    ├── tool-management.component.spec.ts    (unit tests, ~400 lines)
    ├── components/
    │   ├── tool-details-dialog/
    │   │   ├── tool-details-dialog.component.ts      (~150 lines)
    │   │   ├── tool-details-dialog.component.html    (~200 lines)
    │   │   └── tool-details-dialog.component.scss    (~50 lines)
    │   ├── tool-edit-dialog/
    │   │   ├── tool-edit-dialog.component.ts         (~200 lines)
    │   │   ├── tool-edit-dialog.component.html       (~150 lines)
    │   │   └── tool-edit-dialog.component.scss       (~50 lines)
    │   └── tool-delete-dialog/
    │       ├── tool-delete-dialog.component.ts       (~100 lines)
    │       ├── tool-delete-dialog.component.html     (~80 lines)
    │       └── tool-delete-dialog.component.scss     (~30 lines)
    └── models/
        └── tool-management.models.ts        (interfaces, ~50 lines)
```

**Service Location Note:** `ToolAdminService` follows the canonical pattern of placing API services in `src/frontend-angular/src/app/api/services/` (not page-local).

**Total Estimated:** ~2,500 lines

### 7.2 Component Responsibilities

**ToolManagementComponent:**

- Load tools on init
- Manage filters and search
- Handle enable/disable toggle
- Open dialogs (details, edit, delete)
- Navigate to registration wizard
- Refresh data on demand

**ToolDetailsDialogComponent:**

- Display complete tool configuration (read-only)
- Format MCP config for readability
- Show capabilities and parameters schema
- Provide navigation to health/analytics

**ToolEditDialogComponent:**

- Reactive form for editable fields
- Validation matching backend constraints
- Call update API on save
- Handle success/error states

**ToolDeleteDialogComponent:**

- Confirmation checkbox
- Tool ID confirmation input
- Call delete API on confirm
- Emit success event to parent

---

## 8. State Management

### 8.1 Component State

```typescript
export class ToolManagementComponent implements OnInit {
  tools: ToolListItem[] = [];
  filteredTools: ToolListItem[] = [];
  isLoading = false;
  error: string | null = null;

  filters: ToolFilters = {
    category: null,
    enabledOnly: false,
    healthyOnly: false,
    searchTerm: '',
  };

  // Pagination
  pageSize = 20;
  pageIndex = 0;
  totalTools = 0;

  displayedColumns = [
    'name',
    'tool_id',
    'category',
    'provider',
    'status',
    'health',
    'last_check',
    'actions',
  ];
}
```

### 8.2 Data Flow

1. **On Init:**
   - Set `isLoading = true`
   - Call `toolAdminService.listTools()`
   - Store in `tools`
   - Apply client-side filters → `filteredTools`
   - Set `isLoading = false`

2. **On Filter Change:**
   - Apply filters to `tools` → `filteredTools`
   - Reset pagination to page 0

3. **On Enable/Disable Toggle:**
   - Find tool in array
   - Optimistically update `tool.is_enabled`
   - Call `enableTool()` or `disableTool()`
   - On error: revert and show snackbar

4. **On Refresh:**
   - Reload tools from API
   - Preserve current filters

5. **On Edit Save:**
   - Update tool in backend
   - Refresh tools list
   - Close dialog

6. **On Delete:**
   - Remove from backend
   - Remove from `tools` array (client-side)
   - Close dialog

---

## 9. Behavior Details

### 9.1 Enable/Disable Toggle

**Optimistic Update Pattern (Pseudocode):**

```typescript
toggleToolStatus(tool: ToolListItem): void {
  const previousState = tool.is_enabled;
  tool.is_enabled = !tool.is_enabled; // Optimistic

  const operation$ = tool.is_enabled
    ? this.toolAdminService.enableTool(tool.id)
    : this.toolAdminService.disableTool(tool.id);

  operation$.subscribe({
    next: () => {
      this.snackBar.open(
        `Tool '${tool.name}' ${tool.is_enabled ? 'enabled' : 'disabled'}`,
        'Close',
        { duration: 3000 }
      );
    },
    error: (error: any) => {
      tool.is_enabled = previousState; // Revert
      this.snackBar.open(
        error.error?.detail || 'Failed to update tool status',
        'Close',
        { duration: 5000 }
      );
    },
  });
}
```

**Note:** Adapt observable handling to match project standards (subscribe, firstValueFrom, or async pipe).

### 9.2 Health Status Display

```typescript
getHealthIcon(tool: ToolListItem): string {
  if (!tool.is_enabled) return 'remove_circle_outline';
  if (tool.is_healthy) return 'check_circle';
  return 'error';
}

getHealthClass(tool: ToolListItem): string {
  if (!tool.is_enabled) return 'health-disabled';
  if (tool.is_healthy) return 'health-online';
  return 'health-offline';
}

getHealthTooltip(tool: ToolListItem): string {
  if (!tool.is_enabled) return 'Tool is disabled';
  if (!tool.last_health_check) return 'Never checked';
  return `Last checked: ${this.formatTimestamp(tool.last_health_check)}`;
}
```

**CSS Classes:**

```scss
.health-online {
  color: #4caf50; // Green
}

.health-offline {
  color: #f44336; // Red
}

.health-disabled {
  color: #9e9e9e; // Grey
}
```

### 9.3 Navigation from Registration Wizard

**Update `tool-registration-wizard.component.ts`:**

```typescript
async onReviewConfirm(): Promise<void> {
  // ... existing commit logic ...

  if (response?.tool_id) {
    this.draftStorage.clearDraft();
    this.snackBar.open(
      `Tool '${toolName}' registered successfully!`,
      'Close',
      { duration: 5000 }
    );
    // CHANGE THIS LINE:
    this.router.navigate(['/admin/tools']); // Was: ['/admin/tools'] but route didn't exist
  }
}
```

---

## 10. Pattern Reference

### 10.1 Copy From `provider-management.component`

The Provider Management page has nearly identical requirements:

- Table with enable/disable toggles
- Health indicators
- Edit/delete actions
- Filters

**Reuse:**

- Layout structure (header, filters, table, footer)
- Toggle behavior (optimistic updates)
- Dialog patterns (edit, delete)
- Service patterns (API client)

**Differences:**

- Tools have different metadata (MCP config vs provider config)
- Tools have capabilities/parameters schema
- Tools link to registration wizard

### 10.2 ADR-012 Compliance

**Layer 2: Page Header**

```html
<div class="page-header-layer">
  <div class="page-header-controls">
    <div class="header-left">
      <h1 class="page-title">Tool Management</h1>
      <p class="page-subtitle">Administer MCP tools, health, and availability</p>
    </div>
    <div class="header-actions">
      <button mat-raised-button color="primary" (click)="navigateToRegistration()">
        <mat-icon>add</mat-icon>
        Register New Tool
      </button>
      <button mat-icon-button (click)="refreshTools()" matTooltip="Refresh">
        <mat-icon>refresh</mat-icon>
      </button>
    </div>
  </div>

  <!-- Filters -->
  <div class="filters-container">
    <mat-form-field appearance="outline" class="filter-field">
      <mat-label>Category</mat-label>
      <mat-select [(ngModel)]="filters.category" (selectionChange)="applyFilters()">
        <mat-option [value]="null">All Categories</mat-option>
        <mat-option *ngFor="let cat of categories" [value]="cat">
          {{ getCategoryLabel(cat) }}
        </mat-option>
      </mat-select>
    </mat-form-field>

    <mat-slide-toggle
      [(ngModel)]="filters.enabledOnly"
      (change)="applyFilters()"
      class="filter-toggle"
    >
      Show enabled only
    </mat-slide-toggle>

    <mat-slide-toggle
      [(ngModel)]="filters.healthyOnly"
      (change)="applyFilters()"
      class="filter-toggle"
    >
      Show healthy only
    </mat-slide-toggle>

    <mat-form-field appearance="outline" class="search-field">
      <mat-label>Search</mat-label>
      <input matInput [(ngModel)]="filters.searchTerm" (ngModelChange)="applyFilters()"
             placeholder="Search by name or ID...">
      <mat-icon matSuffix>search</mat-icon>
    </mat-form-field>

    <span class="tool-count">
      {{ filteredTools.length }} of {{ tools.length }} tools
    </span>
  </div>
</div>
```

**Layer 3: Content**

```html
<div class="page-content-layer">
  <div class="content-card">
    <table mat-table [dataSource]="filteredTools" class="tools-table">
      <!-- Column definitions -->
    </table>

    <!-- Empty state -->
    <div *ngIf="!isLoading && filteredTools.length === 0" class="empty-state">
      <mat-icon>build</mat-icon>
      <h2>No tools found</h2>
      <p *ngIf="filters.searchTerm || filters.category || filters.enabledOnly || filters.healthyOnly">
        Try adjusting your filters.
      </p>
      <p *ngIf="!filters.searchTerm && !filters.category && !filters.enabledOnly && !filters.healthyOnly">
        No tools registered yet.
      </p>
      <button mat-raised-button color="primary" (click)="navigateToRegistration()">
        <mat-icon>add</mat-icon>
        Register Your First Tool
      </button>
    </div>
  </div>
</div>
```

**Layer 4: Footer**

```html
<div class="page-footer" *ngIf="filteredTools.length > 0">
  <mat-paginator
    [length]="filteredTools.length"
    [pageSize]="pageSize"
    [pageSizeOptions]="[10, 20, 50, 100]"
    (page)="onPageChange($event)"
  ></mat-paginator>
</div>
```

---

## 11. Testing Strategy

### 11.1 Unit Tests (`tool-management.component.spec.ts`)

**Test Coverage:**

- Component creation
- Tools loading on init
- Filter application (category, enabled, healthy, search)
- Enable/disable toggle (success and error paths)
- Dialog opening (details, edit, delete)
- Navigation to registration wizard
- Refresh functionality
- Empty state rendering
- Error state handling

**Mock Dependencies:**

- `ToolAdminService` (mock all methods)
- `MatDialog` (mock open, return mock dialog ref)
- `MatSnackBar` (mock open)
- `Router` (mock navigate)

**Target Coverage:** 80%+

### 11.2 Service Tests (`tool-admin.service.spec.ts`)

**Test Coverage:**

- HTTP calls with correct URLs and params
- Query parameter building
- Error handling
- Response mapping

**Target Coverage:** 90%+

### 11.3 Integration Tests (Future)

- E2E test navigating to `/admin/tools`
- Verify tools load from backend
- Toggle enable/disable and verify backend state
- Edit tool and verify changes persist
- Delete tool and verify removal

---

## 12. Accessibility Requirements

**WCAG 2.1 AA Compliance:**

- ✅ Semantic HTML (table, headings, buttons)
- ✅ ARIA labels on icon buttons
  - View: `aria-label="View details for {tool.name}"`
  - Edit: `aria-label="Edit {tool.name}"`
  - Delete: `aria-label="Delete {tool.name}"`
- ✅ Keyboard navigation (tab order, enter/space for actions)
- ✅ Focus management (dialog opens → focus first field)
- ✅ Color contrast (status indicators meet 4.5:1 ratio)
- ✅ Screen reader announcements (aria-live for status changes)

---

## 13. Performance Considerations

- **Initial Load:** < 1s for 100 tools
- **Filter Application:** < 100ms (client-side)
- **Toggle Enable/Disable:** < 500ms (optimistic UI)
- **Dialog Open:** < 200ms

**Optimizations:**

- Client-side filtering (no API calls on filter change)
- Debounced search (300ms)
- Paginated table (20 per page default)
- Lazy-load dialogs (loadComponent pattern)

---

## 14. Error Handling

**Scenarios:**

1. **Failed to Load Tools:**
   - Show error card with retry button
   - Message: "Failed to load tools. {error detail}"

2. **Failed to Enable/Disable:**
   - Revert toggle state
   - Show snackbar: "Failed to {enable/disable} tool: {error}"

3. **Failed to Update:**
   - Keep edit dialog open
   - Show inline error above form
   - Highlight invalid fields

4. **Failed to Delete:**
   - Show snackbar: "Failed to delete tool: {error}"
   - Keep dialog open

5. **Network Timeout:**
   - Show snackbar: "Request timed out. Please try again."

---

## 15. Acceptance Criteria

### 15.1 Functional Requirements

- [ ] Route `/admin/tools` accessible to admin users only
- [ ] Tools table displays all registered tools with correct metadata
- [ ] Enable/disable toggles work and reflect backend state
- [ ] Health indicators show correct status (online/offline/unknown)
- [ ] Category filter works (client-side)
- [ ] Enabled-only filter works (client-side)
- [ ] Healthy-only filter works (client-side)
- [ ] Search works (name and tool_id, case-insensitive)
- [ ] View details dialog shows complete configuration
- [ ] Edit dialog updates tool successfully
- [ ] Delete dialog removes tool with confirmation
- [ ] "Register New Tool" navigates to wizard
- [ ] Registration wizard success navigates to `/admin/tools`
- [ ] Pagination works correctly
- [ ] Empty state shows when no tools match filters
- [ ] Error states handled gracefully

### 15.2 Quality Requirements

- [ ] 80%+ unit test coverage for main component
- [ ] 90%+ unit test coverage for service
- [ ] All tests passing
- [ ] ADR-012 layout compliance verified
- [ ] WCAG 2.1 AA accessibility verified
- [ ] Clean compilation (0 TypeScript errors)
- [ ] Clean linting (0 ESLint errors)
- [ ] Performance: initial load < 1s, filters < 100ms

### 15.3 Integration Requirements

- [ ] Integrates with existing admin navigation
- [ ] Uses existing `tool.models.ts` types
- [ ] Follows provider-management component patterns
- [ ] Compatible with existing auth/RBAC
- [ ] Works with existing backend APIs (no backend changes needed)

---

## 16. Dependencies

### 16.1 Backend APIs (Already Exist)

✅ All required endpoints implemented in:

- `src/orchestrator/app/routers/tools_admin.py` (15 endpoints)
- `src/orchestrator/app/services/tool_service.py` (CRUD operations)

### 16.2 Frontend Dependencies

✅ Existing:

- Angular Material components
- `tool.models.ts` (types)
- Admin layout pattern (ADR-012)
- Auth guards

❌ Need to Create:

- `ToolAdminService`
- `ToolManagementComponent` and sub-components

---

## 17. Implementation Estimate

**Effort:** 3-4 days (1 developer)

**Breakdown:**

- Day 1: Service + main component + table (6-8 hours)
- Day 2: Details dialog + edit dialog (6-8 hours)
- Day 3: Delete dialog + integration + testing (6-8 hours)
- Day 4: Polish, accessibility, edge cases (4-6 hours)

**With AI Assist:** 2-3 days

---

## 18. Related Documentation

- **Architecture:** `docs/architecture/TOOLS_ARCHITECTURE_DIAGRAMS.md`
- **Backend API:** `src/orchestrator/app/routers/tools_admin.py`
- **Pattern Reference:** `src/frontend-angular/src/app/pages/admin/provider-management/`
- **User Guide:** `docs/user-guides/admin-tool-registration.md`
- **ADR-012:** Layered Page Layout Pattern
- **ADR-001:** Hybrid Tools Architecture

---

**Status:** Ready for implementation
**Priority:** 🔴 CRITICAL - Blocks Tools Track production use
**Next Step:** Create task document and begin implementation
