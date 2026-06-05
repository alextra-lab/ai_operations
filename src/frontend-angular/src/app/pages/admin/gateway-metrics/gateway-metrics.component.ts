/**
 * Gateway Metrics Dashboard Component
 *
 * Admin interface for viewing Inference Gateway metrics and analytics.
 * Follows ADR-012 Layered Page Layout Pattern.
 *
 * Related: P3-T2, Phase 4.5 Inference Gateway
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { Subject, forkJoin, takeUntil } from 'rxjs';

import { GatewayCostChartComponent } from './components/charts/gateway-cost-chart.component';
import { GatewayLatencyChartComponent } from './components/charts/gateway-latency-chart.component';
import { GatewayTokenChartComponent } from './components/charts/gateway-token-chart.component';
import {
  GatewayMetrics,
  MetricsFilters,
  ModelMetrics,
  ProviderMetrics,
  TIME_RANGE_OPTIONS,
  TimeRange,
  TimeSeriesData,
} from './models/gateway-metrics.models';
import { GatewayMetricsService } from './services/gateway-metrics.service';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-gateway-metrics',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTableModule,
    MatTabsModule,
    GatewayLatencyChartComponent,
    GatewayTokenChartComponent,
    GatewayCostChartComponent,
  ],
  templateUrl: './gateway-metrics.component.html',
  styleUrls: ['./gateway-metrics.component.scss'],
})
export class GatewayMetricsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Data
  aggregateMetrics: GatewayMetrics | null = null;
  timeSeriesData: TimeSeriesData | null = null;
  providerMetrics: ProviderMetrics[] = [];
  modelMetrics: ModelMetrics[] = [];

  // UI State
  isLoading = false;
  error: string | null = null;
  selectedTimeRange: TimeRange = '24h';
  timeRangeOptions = TIME_RANGE_OPTIONS;

  // Table columns
  providerColumns = [
    'provider_name',
    'request_count',
    'success_rate',
    'avg_latency_ms',
    'total_cost_eur',
  ];
  modelColumns = [
    'model_name',
    'request_count',
    'total_tokens',
    'total_cost_eur',
    'avg_latency_ms',
  ];

  constructor(
    private metricsService: GatewayMetricsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load all metrics data
   */
  loadMetrics(): void {
    this.isLoading = true;
    this.error = null;

    const selectedOption = this.timeRangeOptions.find(
      (opt) => opt.value === this.selectedTimeRange
    );
    const hours = selectedOption?.hours || 24;

    const filters: MetricsFilters = {
      hours,
    };

    forkJoin({
      aggregate: this.metricsService.getAggregateMetrics(filters),
      timeseries: this.metricsService.getTimeSeriesData(filters),
      providers: this.metricsService.getMetricsByProvider(hours),
      models: this.metricsService.getMetricsByModel(hours),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (results) => {
          this.aggregateMetrics = results.aggregate;
          this.timeSeriesData = results.timeseries;
          this.providerMetrics = results.providers;
          this.modelMetrics = results.models;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading metrics:', error);
          this.error = 'Failed to load metrics. Please try again.';
          this.isLoading = false;
          this.snackBar.open('Failed to load metrics', 'Close', {
            duration: 5000,
          });
        },
      });
  }

  /**
   * Handle time range change
   */
  onTimeRangeChange(): void {
    this.loadMetrics();
  }

  /**
   * Refresh metrics
   */
  refreshMetrics(): void {
    this.loadMetrics();
  }

  /**
   * Export metrics as CSV
   */
  exportCSV(): void {
    if (!this.aggregateMetrics || !this.providerMetrics || !this.modelMetrics) {
      this.snackBar.open('No data to export', 'Close', { duration: 3000 });
      return;
    }

    const lines: string[] = [];

    // Aggregate metrics section
    lines.push('Aggregate Metrics');
    lines.push('Metric,Value');
    lines.push(`Total Requests,${this.aggregateMetrics.total_requests}`);
    lines.push(
      `Successful Requests,${this.aggregateMetrics.successful_requests}`
    );
    lines.push(`Failed Requests,${this.aggregateMetrics.failed_requests}`);
    lines.push(`Success Rate,${this.aggregateMetrics.success_rate}%`);
    lines.push(
      `Total Input Tokens,${this.aggregateMetrics.total_input_tokens}`
    );
    lines.push(
      `Total Output Tokens,${this.aggregateMetrics.total_output_tokens}`
    );
    lines.push(
      `Total Tokens,${this.aggregateMetrics.total_input_tokens + this.aggregateMetrics.total_output_tokens}`
    );
    lines.push(`Total Cost (EUR),${this.aggregateMetrics.total_cost_eur}`);
    lines.push(`Average Latency (ms),${this.aggregateMetrics.avg_latency_ms}`);
    lines.push('');

    // Provider metrics section
    lines.push('Provider Metrics');
    lines.push(
      'Provider,Requests,Success Rate,Avg Latency (ms),Total Cost (EUR),Total Tokens'
    );
    this.providerMetrics.forEach((p) => {
      lines.push(
        `${p.provider_name},${p.request_count},${p.success_rate}%,${p.avg_latency_ms},${p.total_cost_eur},${p.total_tokens}`
      );
    });
    lines.push('');

    // Model metrics section
    lines.push('Model Metrics');
    lines.push('Model,Requests,Total Tokens,Total Cost (EUR),Avg Latency (ms)');
    this.modelMetrics.forEach((m) => {
      lines.push(
        `${m.model_name},${m.request_count},${m.total_tokens},${m.total_cost_eur},${m.avg_latency_ms}`
      );
    });

    const csv = lines.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gateway-metrics-${this.selectedTimeRange}-${new Date().toISOString()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);

    this.snackBar.open('Metrics exported successfully', 'Close', {
      duration: 3000,
    });
  }

  /**
   * Export metrics as JSON
   */
  exportJSON(): void {
    if (
      !this.aggregateMetrics ||
      !this.timeSeriesData ||
      !this.providerMetrics ||
      !this.modelMetrics
    ) {
      this.snackBar.open('No data to export', 'Close', { duration: 3000 });
      return;
    }

    const data = {
      exported_at: new Date().toISOString(),
      time_range: this.selectedTimeRange,
      aggregate: this.aggregateMetrics,
      timeseries: this.timeSeriesData,
      providers: this.providerMetrics,
      models: this.modelMetrics,
    };

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gateway-metrics-${this.selectedTimeRange}-${new Date().toISOString()}.json`;
    a.click();
    window.URL.revokeObjectURL(url);

    this.snackBar.open('Metrics exported successfully', 'Close', {
      duration: 3000,
    });
  }

  /**
   * Format numbers with commas
   */
  formatNumber(num: number): string {
    return num.toLocaleString();
  }

  /**
   * Format percentage
   */
  formatPercent(num: number): string {
    return `${num.toFixed(2)}%`;
  }

  /**
   * Format cost in EUR
   */
  formatCost(num: number): string {
    return `€${num.toFixed(6)}`;
  }
}
