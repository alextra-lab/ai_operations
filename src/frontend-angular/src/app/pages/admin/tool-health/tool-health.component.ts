/**
 * Tool Health Dashboard Component
 *
 * T6-F2: Admin-facing health monitoring dashboard for MCP tools.
 * Displays overall health summary, tool health table, and history charts.
 * Follows ADR-012 Layered Page Layout Pattern.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  inject,
  OnDestroy,
  OnInit,
  signal,
  WritableSignal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { forkJoin, interval, Subject, takeUntil } from 'rxjs';

import { ToolAdminService } from '../tool-management/services/tool-admin.service';
import { HealthHistoryChartComponent } from './components/health-history-chart/health-history-chart.component';
import { HealthSummaryCardsComponent } from './components/health-summary-cards/health-summary-cards.component';
import {
  getHealthDisplayStatus,
  HealthDisplayStatus,
  HealthSummary,
  TimeRangeOption,
  ToolHealthCheckRecord,
  ToolHealthListItem,
} from './models/tool-health.models';
import { ToolHealthService } from './services/tool-health.service';

@Component({
  selector: 'app-tool-health',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatSortModule,
    MatTableModule,
    MatTooltipModule,
    HealthSummaryCardsComponent,
    HealthHistoryChartComponent,
  ],
  templateUrl: './tool-health.component.html',
  styleUrls: ['./tool-health.component.scss'],
})
export class ToolHealthComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private autoRefreshStop$ = new Subject<void>();

  // Data signals
  summary: WritableSignal<HealthSummary | null> = signal(null);
  tools: WritableSignal<ToolHealthListItem[]> = signal([]);
  sortedTools: WritableSignal<ToolHealthListItem[]> = signal([]);
  selectedTool: WritableSignal<ToolHealthListItem | null> = signal(null);
  healthHistory: WritableSignal<ToolHealthCheckRecord[]> = signal([]);

  // UI state
  isLoading = true;
  isLoadingHistory = false;
  checkingToolIds = new Set<string>();
  autoRefreshEnabled = false;
  selectedTimeRange = 24;

  // Table columns
  displayedColumns = ['name', 'status', 'lastCheck', 'responseTime', 'actions'];

  // Time range options
  timeRangeOptions: TimeRangeOption[] = [
    { value: 1, label: '1 hour' },
    { value: 6, label: '6 hours' },
    { value: 24, label: '24 hours' },
    { value: 72, label: '3 days' },
    { value: 168, label: '7 days' },
  ];

  private readonly healthService = inject(ToolHealthService);
  private readonly toolAdminService = inject(ToolAdminService);
  private readonly snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    this.autoRefreshStop$.next();
    this.autoRefreshStop$.complete();
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load summary and tool list data
   */
  loadData(): void {
    this.isLoading = true;

    forkJoin({
      summary: this.healthService.getOverallStatus(),
      tools: this.toolAdminService.listTools(),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: ({ summary, tools }) => {
          this.summary.set(summary);

          // Map to health list items
          const healthTools: ToolHealthListItem[] = tools.map((t) => ({
            id: t.id,
            tool_id: t.tool_id,
            name: t.name,
            description: t.description,
            is_enabled: t.is_enabled,
            is_healthy: t.is_healthy,
            last_health_check: null, // Not in list response
            response_time_ms: null,
          }));

          this.tools.set(healthTools);
          this.sortedTools.set([...healthTools]);
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading health data:', error);
          this.snackBar.open('Failed to load health data', 'Close', {
            duration: 5000,
          });
          this.isLoading = false;
        },
      });
  }

  /**
   * Refresh all data
   */
  onRefresh(): void {
    this.loadData();
    if (this.selectedTool()) {
      this.loadToolHistory(this.selectedTool()!);
    }
  }

  /**
   * Toggle auto-refresh
   */
  onAutoRefreshChange(): void {
    // Stop any existing interval first
    this.autoRefreshStop$.next();

    if (this.autoRefreshEnabled) {
      interval(30000)
        .pipe(takeUntil(this.autoRefreshStop$), takeUntil(this.destroy$))
        .subscribe(() => {
          this.loadData();
          if (this.selectedTool()) {
            this.loadToolHistory(this.selectedTool()!);
          }
        });
    }
  }

  /**
   * Handle tool row selection
   */
  onToolSelect(tool: ToolHealthListItem): void {
    this.selectedTool.set(tool);
    this.loadToolHistory(tool);
  }

  /**
   * Load health history for a tool
   */
  loadToolHistory(tool: ToolHealthListItem): void {
    this.isLoadingHistory = true;

    this.healthService
      .getToolHistory(tool.id, this.selectedTimeRange)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (history) => {
          this.healthHistory.set(history);
          this.isLoadingHistory = false;
        },
        error: (error) => {
          console.error('Error loading tool history:', error);
          this.snackBar.open('Failed to load tool history', 'Close', {
            duration: 5000,
          });
          this.isLoadingHistory = false;
        },
      });
  }

  /**
   * Handle time range change
   */
  onTimeRangeChange(): void {
    if (this.selectedTool()) {
      this.loadToolHistory(this.selectedTool()!);
    }
  }

  /**
   * Trigger manual health check for a tool
   */
  onTriggerCheck(tool: ToolHealthListItem, event: Event): void {
    event.stopPropagation();
    this.checkingToolIds.add(tool.id);

    this.healthService
      .triggerHealthCheck(tool.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.checkingToolIds.delete(tool.id);

          // Update tool in list
          const currentTools = this.tools();
          const updatedTools = currentTools.map((t) =>
            t.id === tool.id
              ? {
                  ...t,
                  is_healthy: result.status === 'online',
                  response_time_ms: result.response_time_ms,
                }
              : t
          );
          this.tools.set(updatedTools);
          this.sortedTools.set([...updatedTools]);

          // Refresh summary
          this.healthService.getOverallStatus().subscribe((s) => {
            this.summary.set(s);
          });

          // If this tool is selected, refresh history
          if (this.selectedTool()?.id === tool.id) {
            this.loadToolHistory(tool);
          }

          this.snackBar.open(
            `Health check completed for ${tool.name}`,
            'Close',
            { duration: 3000 }
          );
        },
        error: (error) => {
          this.checkingToolIds.delete(tool.id);
          console.error('Error triggering health check:', error);
          this.snackBar.open(`Health check failed: ${error.message}`, 'Close', {
            duration: 5000,
          });
        },
      });
  }

  /**
   * Check if a tool is currently being checked
   */
  isChecking(toolId: string): boolean {
    return this.checkingToolIds.has(toolId);
  }

  /**
   * Get health display status for a tool
   */
  getStatus(tool: ToolHealthListItem): HealthDisplayStatus {
    return getHealthDisplayStatus(
      tool.is_enabled,
      tool.is_healthy,
      tool.last_health_check
    );
  }

  /**
   * Get status icon for a tool
   */
  getStatusIcon(tool: ToolHealthListItem): string {
    const status = this.getStatus(tool);
    switch (status) {
      case 'online':
        return 'check_circle';
      case 'offline':
        return 'error';
      case 'disabled':
        return 'power_off';
      default:
        return 'help_outline';
    }
  }

  /**
   * Get status class for styling
   */
  getStatusClass(tool: ToolHealthListItem): string {
    return this.getStatus(tool);
  }

  /**
   * Format relative time for last check
   */
  formatLastCheck(timestamp: string | null): string {
    if (!timestamp) {
      return 'Never';
    }
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) {
      return 'Just now';
    }
    if (diffMins < 60) {
      return `${diffMins}m ago`;
    }
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) {
      return `${diffHours}h ago`;
    }
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  /**
   * Handle table sorting
   */
  onSort(sortState: Sort): void {
    const data = [...this.tools()];

    if (!sortState.active || sortState.direction === '') {
      this.sortedTools.set(data);
      return;
    }

    const sorted = data.sort((a, b) => {
      const isAsc = sortState.direction === 'asc';
      switch (sortState.active) {
        case 'name':
          return this.compare(a.name, b.name, isAsc);
        case 'status':
          return this.compare(
            a.is_healthy ? 1 : 0,
            b.is_healthy ? 1 : 0,
            isAsc
          );
        case 'responseTime':
          return this.compare(
            a.response_time_ms ?? 0,
            b.response_time_ms ?? 0,
            isAsc
          );
        default:
          return 0;
      }
    });

    this.sortedTools.set(sorted);
  }

  private compare(
    a: string | number,
    b: string | number,
    isAsc: boolean
  ): number {
    return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
  }

  /**
   * Get latest check details from history
   */
  getLatestCheck(): ToolHealthCheckRecord | null {
    const history = this.healthHistory();
    if (history.length === 0) {
      return null;
    }
    return history[0]; // Already sorted by most recent first
  }
}
