import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { PerformanceMetrics, WidgetConfig } from '../models/dashboard.models';

@Component({
  selector: 'app-performance-metrics-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="performance-metrics-widget">
      <div class="header">
        <div class="title">
          <mat-icon aria-hidden="true">speed</mat-icon>
          <div>
            <p>Performance Metrics</p>
            <small>Realtime backend health</small>
          </div>
        </div>
        <mat-chip
          class="status-chip"
          [class.good]="isHealthy"
          [class.bad]="!isHealthy"
        >
          {{ isHealthy ? 'Stable' : 'Degraded' }}
        </mat-chip>
      </div>

      <div *ngIf="metrics; else emptyState" class="metrics-grid">
        <div class="metric-card">
          <div class="label">
            <mat-icon aria-hidden="true">timer</mat-icon>
            <span>Response Time</span>
          </div>
          <div class="value">
            {{ metrics.response_time | number: '1.0-0' }} ms
          </div>
        </div>

        <div class="metric-card">
          <div class="label">
            <mat-icon aria-hidden="true">swap_horiz</mat-icon>
            <span>Throughput</span>
          </div>
          <div class="value">
            {{ metrics.throughput | number: '1.0-0' }} rps
          </div>
        </div>

        <div class="metric-card">
          <div class="label">
            <mat-icon aria-hidden="true">error_outline</mat-icon>
            <span>Error Rate</span>
          </div>
          <div class="value">{{ metrics.error_rate | number: '1.1-1' }}%</div>
        </div>

        <div class="bar-item">
          <div class="bar-label">
            <mat-icon aria-hidden="true">memory</mat-icon>
            <span>CPU</span>
          </div>
          <mat-progress-bar
            [value]="metrics.cpu_usage"
            [class]="usageClass(metrics.cpu_usage)"
          ></mat-progress-bar>
          <span class="bar-value"
            >{{ metrics.cpu_usage | number: '1.0-0' }}%</span
          >
        </div>

        <div class="bar-item">
          <div class="bar-label">
            <mat-icon aria-hidden="true">storage</mat-icon>
            <span>Memory</span>
          </div>
          <mat-progress-bar
            [value]="metrics.memory_usage"
            [class]="usageClass(metrics.memory_usage)"
          ></mat-progress-bar>
          <span class="bar-value">
            {{ metrics.memory_usage | number: '1.0-0' }}%
          </span>
        </div>

        <div class="bar-item">
          <div class="bar-label">
            <mat-icon aria-hidden="true">lan</mat-icon>
            <span>Connections</span>
          </div>
          <mat-progress-bar
            [value]="connectionsPercent"
            class="usage-medium"
          ></mat-progress-bar>
          <span class="bar-value">{{ metrics.active_connections }} active</span>
        </div>
      </div>

      <ng-template #emptyState>
        <div class="empty-state">
          <mat-icon aria-hidden="true">speed</mat-icon>
          <p>No performance data</p>
          <small>Data will appear when metrics stream begins</small>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .performance-metrics-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .title {
        display: flex;
        gap: 10px;
        align-items: center;
      }

      .title p {
        margin: 0;
        font-weight: 600;
      }

      .title small {
        color: var(--mat-on-surface-variant-color);
      }

      .status-chip {
        color: white;
      }

      .status-chip.good {
        background: #4caf50;
      }

      .status-chip.bad {
        background: #f57c00;
      }

      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
      }

      .metric-card {
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--mat-surface-color);
        border: 1px solid var(--mat-outline-variant-color);
      }

      .label {
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--mat-on-surface-variant-color);
      }

      .value {
        font-size: 18px;
        font-weight: 600;
        margin-top: 6px;
      }

      .bar-item {
        display: grid;
        grid-template-columns: 1fr;
        gap: 6px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--mat-surface-color);
        border: 1px solid var(--mat-outline-variant-color);
      }

      .bar-label {
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--mat-on-surface-variant-color);
      }

      .bar-value {
        font-weight: 600;
      }

      mat-progress-bar.usage-low ::ng-deep .mat-progress-bar-fill::after {
        background-color: #4caf50;
      }

      mat-progress-bar.usage-medium ::ng-deep .mat-progress-bar-fill::after {
        background-color: #fbc02d;
      }

      mat-progress-bar.usage-high ::ng-deep .mat-progress-bar-fill::after {
        background-color: #f57c00;
      }

      mat-progress-bar.usage-critical ::ng-deep .mat-progress-bar-fill::after {
        background-color: #d32f2f;
      }

      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--mat-on-surface-variant-color);
        gap: 4px;
      }

      .empty-state mat-icon {
        opacity: 0.5;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PerformanceMetricsWidgetComponent {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  get metrics(): PerformanceMetrics | null {
    return this.data.performance_metrics || null;
  }

  get isHealthy(): boolean {
    if (!this.metrics) return false;
    return (
      this.metrics.response_time < 250 &&
      this.metrics.error_rate < 2 &&
      this.metrics.cpu_usage < 85
    );
  }

  get connectionsPercent(): number {
    if (!this.metrics) return 0;
    return Math.min((this.metrics.active_connections / 100) * 100, 100);
  }

  usageClass(value: number): string {
    if (value >= 90) return 'usage-critical';
    if (value >= 75) return 'usage-high';
    if (value >= 50) return 'usage-medium';
    return 'usage-low';
  }
}
