/**
 * Tool Analytics Dashboard Component
 *
 * T6-F3: Admin-facing analytics dashboard for MCP tool usage.
 * Displays usage summaries, per-tool statistics, and center aggregations.
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
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { RouterLink } from '@angular/router';
import { forkJoin, Subject, takeUntil } from 'rxjs';

import { ToolAnalyticsService } from '../../../api/services/tool-analytics.service';
import { ToolAdminService } from '../tool-management/services/tool-admin.service';
import {
  ChartMetric,
  UsageByCenterChartComponent,
} from './components/usage-by-center-chart/usage-by-center-chart.component';
import { UsageByToolTableComponent } from './components/usage-by-tool-table/usage-by-tool-table.component';
import { UsageSummaryCardsComponent } from './components/usage-summary-cards/usage-summary-cards.component';
import {
  AggregateAnalytics,
  calculateAggregates,
  CenterUsage,
  DateRangePreset,
  TIME_RANGE_OPTIONS,
  ToolUsageSummary,
} from './models/tool-analytics.models';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-tool-analytics',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTabsModule,
    UsageSummaryCardsComponent,
    UsageByToolTableComponent,
    UsageByCenterChartComponent,
  ],
  templateUrl: './tool-analytics.component.html',
  styleUrls: ['./tool-analytics.component.scss'],
})
export class ToolAnalyticsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Data signals
  usageSummary: WritableSignal<ToolUsageSummary[]> = signal([]);
  usageByCenter: WritableSignal<CenterUsage[]> = signal([]);
  aggregates: WritableSignal<AggregateAnalytics | null> = signal(null);
  toolNames: WritableSignal<Map<string, string>> = signal(new Map());

  // UI state
  isLoading = true;
  error: string | null = null;
  selectedTimeRange: DateRangePreset = DateRangePreset.MONTH;
  chartMetric: ChartMetric = 'calls';

  // Options
  timeRangeOptions = TIME_RANGE_OPTIONS;

  private readonly analyticsService = inject(ToolAnalyticsService);
  private readonly toolAdminService = inject(ToolAdminService);
  private readonly snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load all analytics data
   */
  loadData(): void {
    this.isLoading = true;
    this.error = null;

    const days = this.getSelectedDays();

    forkJoin({
      summary: this.analyticsService.getUsageSummaryByDays(days),
      byCenter: this.analyticsService.getUsageByCenter(days),
      tools: this.toolAdminService.listTools(),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: ({ summary, byCenter, tools }) => {
          // Build tool name lookup map using tool_id as key
          const nameMap = new Map<string, string>();
          tools.forEach((t) => {
            nameMap.set(t.tool_id, t.name);
          });
          this.toolNames.set(nameMap);

          // Enrich summary with tool names
          const enrichedSummary = summary.map((s) => ({
            ...s,
            tool_name: nameMap.get(s.tool_id) || s.tool_id,
          }));

          this.usageSummary.set(enrichedSummary);
          this.usageByCenter.set(byCenter);

          // Calculate aggregates
          const agg = calculateAggregates(enrichedSummary);
          this.aggregates.set(agg);

          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error loading analytics:', err);
          this.error = 'Failed to load analytics data. Please try again.';
          this.isLoading = false;
          this.snackBar.open('Failed to load analytics', 'Close', {
            duration: 5000,
          });
        },
      });
  }

  /**
   * Handle time range change
   */
  onTimeRangeChange(): void {
    this.loadData();
  }

  /**
   * Refresh data
   */
  onRefresh(): void {
    this.loadData();
    this.snackBar.open('Refreshing analytics...', '', { duration: 1500 });
  }

  /**
   * Export data as CSV
   */
  exportCSV(): void {
    const summary = this.usageSummary();
    const byCenter = this.usageByCenter();
    const agg = this.aggregates();

    if (summary.length === 0) {
      this.snackBar.open('No data to export', 'Close', { duration: 3000 });
      return;
    }

    const lines: string[] = [];

    // Aggregate section
    if (agg) {
      lines.push('Aggregate Analytics');
      lines.push('Metric,Value');
      lines.push(`Total Invocations,${agg.total_invocations}`);
      lines.push(`Successful Invocations,${agg.total_successful}`);
      lines.push(
        `Average Success Rate,${agg.average_success_rate.toFixed(2)}%`
      );
      lines.push(`Total Cost,€${agg.total_cost.toFixed(4)}`);
      lines.push(`Average Duration,${agg.average_duration_ms.toFixed(2)}ms`);
      lines.push(`Most Used Tool,${agg.most_used_tool || 'N/A'}`);
      lines.push('');
    }

    // Tool usage section
    lines.push('Tool Usage Summary');
    lines.push(
      'Tool Name,Tool ID,Total Calls,Successful Calls,Success Rate,Avg Duration (ms),Total Cost'
    );
    summary.forEach((s) => {
      lines.push(
        `${s.tool_name || s.tool_id},${s.tool_id},${s.total_calls},` +
          `${s.successful_calls},${s.success_rate.toFixed(2)}%,` +
          `${s.avg_duration_ms.toFixed(2)},€${s.total_cost.toFixed(4)}`
      );
    });
    lines.push('');

    // Center usage section
    if (byCenter.length > 0) {
      lines.push('Usage by Center');
      lines.push('Center ID,Total Calls,Total Cost');
      byCenter.forEach((c) => {
        lines.push(
          `${c.center_id},${c.total_calls},€${c.total_cost.toFixed(4)}`
        );
      });
    }

    const csv = lines.join('\n');
    this.downloadFile(
      csv,
      `tool-analytics-${this.getDateString()}.csv`,
      'text/csv'
    );

    this.snackBar.open('Analytics exported to CSV', 'Close', {
      duration: 3000,
    });
  }

  /**
   * Export data as JSON
   */
  exportJSON(): void {
    const data = {
      exported_at: new Date().toISOString(),
      time_range: this.selectedTimeRange,
      days: this.getSelectedDays(),
      aggregates: this.aggregates(),
      usage_summary: this.usageSummary(),
      usage_by_center: this.usageByCenter(),
    };

    const json = JSON.stringify(data, null, 2);
    this.downloadFile(
      json,
      `tool-analytics-${this.getDateString()}.json`,
      'application/json'
    );

    this.snackBar.open('Analytics exported to JSON', 'Close', {
      duration: 3000,
    });
  }

  /**
   * Handle chart metric change
   */
  onChartMetricChange(metric: ChartMetric): void {
    this.chartMetric = metric;
  }

  /**
   * Get selected days from time range
   */
  private getSelectedDays(): number {
    const option = this.timeRangeOptions.find(
      (o) => o.value === this.selectedTimeRange
    );
    return option?.days || 30;
  }

  /**
   * Get current date string for file names
   */
  private getDateString(): string {
    return new Date().toISOString().split('T')[0];
  }

  /**
   * Download file helper
   */
  private downloadFile(
    content: string,
    filename: string,
    mimeType: string
  ): void {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * Get time range label for display
   */
  getTimeRangeLabel(): string {
    const option = this.timeRangeOptions.find(
      (o) => o.value === this.selectedTimeRange
    );
    return option?.label || 'Last 30 days';
  }
}
