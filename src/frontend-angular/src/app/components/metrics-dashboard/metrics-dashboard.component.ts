/**
 * MetricsDashboardComponent
 *
 * Expandable metrics panel for Query Developer Tools showing:
 * - Aggregate metrics (latency, tokens, cost, consistency)
 * - Performance recommendations
 * - Repeatability testing
 * - Export functionality
 *
 * Features:
 * - Expandable mat-expansion-panel in Layer 3
 * - Real-time metrics calculation
 * - Parameter recommendations
 * - CSV/JSON export
 * - ADR-012 compliant styling
 *
 * Related: P4-TOOLS-07, ADR-045, ADR-012
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';

import {
  ExecutionMetrics,
  QueryConfig,
} from '../../api/models/query-config.models';
import {
  AggregateMetrics,
  ParameterRecommendation,
  RepeatabilityTestResult,
} from '../../models/metrics.models';
import { MetricsService } from '../../services/metrics.service';
import { CostChartComponent } from './charts/cost-chart.component';
import { LatencyChartComponent } from './charts/latency-chart.component';
import { TokenUsageChartComponent } from './charts/token-usage-chart.component';

@Component({
  selector: 'app-metrics-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTabsModule,
    MatTooltipModule,
    LatencyChartComponent,
    TokenUsageChartComponent,
    CostChartComponent,
  ],
  templateUrl: './metrics-dashboard.component.html',
  styleUrls: ['./metrics-dashboard.component.scss'],
})
export class MetricsDashboardComponent implements OnInit, OnChanges, OnDestroy {
  @Input() currentConfig?: QueryConfig;
  @Input() onExecuteQuery?: (config: QueryConfig) => Promise<ExecutionMetrics>;

  // Metrics state
  aggregateMetrics: AggregateMetrics | null = null;
  recommendations: ParameterRecommendation[] = [];
  executionHistory: ExecutionMetrics[] = [];

  // Repeatability test state
  isRunningRepeatabilityTest = false;
  testIterations = 5;
  repeatabilityResult: RepeatabilityTestResult | null = null;

  // Panel state
  isPanelExpanded = false;

  // Cleanup
  private readonly destroy$ = new Subject<void>();

  constructor(
    private readonly metricsService: MetricsService,
    private readonly snackBar: MatSnackBar,
    private readonly dialog: MatDialog
  ) { }

  ngOnInit(): void {
    // Subscribe to metrics updates
    this.metricsService.executionHistory$
      .pipe(takeUntil(this.destroy$))
      .subscribe((history) => {
        this.executionHistory = history;
      });

    this.metricsService.aggregateMetrics$
      .pipe(takeUntil(this.destroy$))
      .subscribe((metrics) => {
        this.aggregateMetrics = metrics;
      });

    this.metricsService.recommendations$
      .pipe(takeUntil(this.destroy$))
      .subscribe((recs) => {
        this.recommendations = recs;
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Regenerate recommendations when config changes
    if (changes['currentConfig'] && this.currentConfig) {
      this.metricsService.generateRecommendationsFor(this.currentConfig);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Metrics Actions
  // ========================================================================

  /**
   * Clear all metrics and history
   */
  clearMetrics(): void {
    this.metricsService.clearHistory();
    this.repeatabilityResult = null;

    this.snackBar.open('Metrics cleared', 'Dismiss', { duration: 3000 });
  }

  /**
   * Export metrics as CSV
   */
  exportAsCSV(): void {
    const csv = this.metricsService.exportAsCSV();
    if (!csv) {
      this.snackBar.open('No metrics to export', 'Dismiss', { duration: 3000 });
      return;
    }

    const filename = `metrics_${this.getTimestampString()}.csv`;
    this.metricsService.downloadFile(csv, filename, 'text/csv');

    this.snackBar.open('Metrics exported as CSV', 'Dismiss', {
      duration: 3000,
    });
  }

  /**
   * Export metrics as JSON
   */
  exportAsJSON(): void {
    const json = this.metricsService.exportAsJSON();
    if (!json) {
      this.snackBar.open('No metrics to export', 'Dismiss', { duration: 3000 });
      return;
    }

    const filename = `metrics_${this.getTimestampString()}.json`;
    this.metricsService.downloadFile(json, filename, 'application/json');

    this.snackBar.open('Metrics exported as JSON', 'Dismiss', {
      duration: 3000,
    });
  }

  // ========================================================================
  // Repeatability Testing
  // ========================================================================

  /**
   * Run repeatability test
   */
  async runRepeatabilityTest(): Promise<void> {
    if (!this.currentConfig || !this.onExecuteQuery) {
      this.snackBar.open(
        'Cannot run test: missing configuration or execute function',
        'Dismiss',
        { duration: 5000 }
      );
      return;
    }

    // Get current query from config or prompt user
    const query = 'Test query'; // TODO: Get from parent component

    this.isRunningRepeatabilityTest = true;
    this.repeatabilityResult = null;

    const executions: ExecutionMetrics[] = [];

    try {
      // Run test iterations sequentially
      for (let i = 0; i < this.testIterations; i++) {
        const metrics = await this.onExecuteQuery(this.currentConfig);
        executions.push(metrics);

        // Update progress
      }

      // Analyze results
      this.repeatabilityResult = this.metricsService.analyzeRepeatability(
        query,
        this.currentConfig,
        executions
      );

      this.snackBar.open(
        `Repeatability test complete: ${this.testIterations} iterations`,
        'Dismiss',
        { duration: 5000 }
      );
    } catch (error) {
      console.error('Repeatability test failed:', error);
      this.snackBar.open(
        'Repeatability test failed. Check console for details.',
        'Dismiss',
        { duration: 5000 }
      );
    } finally {
      this.isRunningRepeatabilityTest = false;
    }
  }

  // ========================================================================
  // Recommendations
  // ========================================================================

  /**
   * Apply a parameter recommendation
   */
  applyRecommendation(rec: ParameterRecommendation): void {
    // Emit event to parent component to apply recommendation
    this.snackBar.open(`Applied recommendation: ${rec.parameter}`, 'Dismiss', {
      duration: 3000,
    });
  }

  /**
   * Get icon for recommendation type
   */
  getRecommendationIcon(type: string): string {
    switch (type) {
      case 'performance':
        return 'speed';
      case 'consistency':
        return 'check_circle';
      case 'cost':
        return 'attach_money';
      case 'quality':
        return 'star';
      default:
        return 'lightbulb';
    }
  }

  /**
   * Get color class for recommendation type
   */
  getRecommendationColor(type: string): string {
    switch (type) {
      case 'performance':
        return 'text-blue-600';
      case 'consistency':
        return 'text-green-600';
      case 'cost':
        return 'text-orange-600';
      case 'quality':
        return 'text-purple-600';
      default:
        return 'text-gray-600';
    }
  }

  // ========================================================================
  // Helpers
  // ========================================================================

  /**
   * Get formatted timestamp string for filenames
   */
  private getTimestampString(): string {
    const now = new Date();
    return now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  }

  /**
   * Get percentage string
   */
  getPercentage(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  /**
   * Format number with decimals
   */
  formatNumber(value: number, decimals = 0): string {
    return value.toFixed(decimals);
  }

  /**
   * Format currency
   */
  formatCurrency(value: number, currency = 'USD'): string {
    return `${currency} ${value.toFixed(4)}`;
  }
}
