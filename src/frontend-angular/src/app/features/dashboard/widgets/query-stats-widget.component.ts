import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';

import {
  QueryStats,
  RecentQuery,
  TopQuery,
  WidgetConfig,
} from '../models/dashboard.models';

@Component({
  selector: 'app-query-stats-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTableModule,
  ],
  template: `
    <div class="query-stats-widget">
      <!-- Loading State -->
      <div *ngIf="isLoading" class="loading-container">
        <mat-spinner diameter="30"></mat-spinner>
        <p>Loading query statistics...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="hasError" class="error-container">
        <mat-icon color="warn">error</mat-icon>
        <p>Failed to load query statistics</p>
        <button mat-button (click)="refresh()">Retry</button>
      </div>

      <!-- Content -->
      <div *ngIf="!isLoading && !hasError" class="query-stats-content">
        <!-- Summary Stats -->
        <div class="summary-stats">
          <div class="stat-card">
            <div class="stat-icon">
              <mat-icon>search</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{
                queryStats?.total_queries || 0
              }}</span>
              <span class="stat-label">Total Queries</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon success">
              <mat-icon>check_circle</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{
                queryStats?.successful_queries || 0
              }}</span>
              <span class="stat-label">Successful</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon error">
              <mat-icon>error</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{
                queryStats?.failed_queries || 0
              }}</span>
              <span class="stat-label">Failed</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon">
              <mat-icon>speed</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{
                formatResponseTime(queryStats?.average_response_time)
              }}</span>
              <span class="stat-label">Avg Response</span>
            </div>
          </div>
        </div>

        <!-- Performance Metrics -->
        <div class="performance-metrics">
          <div class="metric-item">
            <div class="metric-label">
              <mat-icon>trending_up</mat-icon>
              <span>Queries per Hour</span>
            </div>
            <div class="metric-value">
              <span class="value">{{ queryStats?.queries_per_hour || 0 }}</span>
              <mat-chip class="trend-chip positive">
                <mat-icon>trending_up</mat-icon>
                +12%
              </mat-chip>
            </div>
          </div>

          <div class="metric-item">
            <div class="metric-label">
              <mat-icon>percent</mat-icon>
              <span>Success Rate</span>
            </div>
            <div class="metric-value">
              <span class="value">{{ getSuccessRate() }}%</span>
              <mat-chip [class]="'rate-chip ' + getSuccessRateClass()">
                {{ getSuccessRateText() }}
              </mat-chip>
            </div>
          </div>
        </div>

        <!-- Top Queries -->
        <div class="top-queries" *ngIf="queryStats?.top_queries?.length">
          <h4>Top Queries</h4>
          <div class="queries-list">
            <div
              *ngFor="
                let query of (queryStats?.top_queries || []).slice(0, 5);
                trackBy: trackByQueryText
              "
              class="query-item"
            >
              <div class="query-info">
                <div class="query-text">
                  <mat-icon>search</mat-icon>
                  <span [matTooltip]="query.query">{{
                    truncateText(query.query, 50)
                  }}</span>
                </div>
                <div class="query-stats">
                  <span class="count">{{ query.count }} times</span>
                  <span class="response-time">{{
                    formatResponseTime(query.avg_response_time)
                  }}</span>
                </div>
              </div>

              <div class="query-metrics">
                <mat-chip
                  [class]="
                    'success-rate ' + getSuccessRateClass(query.success_rate)
                  "
                >
                  {{ query.success_rate }}%
                </mat-chip>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Queries -->
        <div class="recent-queries" *ngIf="queryStats?.recent_queries?.length">
          <h4>Recent Queries</h4>
          <div class="queries-table">
            <div class="table-header">
              <span>Query</span>
              <span>User</span>
              <span>Status</span>
              <span>Time</span>
            </div>

            <div
              *ngFor="
                let query of (queryStats?.recent_queries || []).slice(0, 5);
                trackBy: trackByQueryId
              "
              class="table-row"
            >
              <div class="query-cell">
                <mat-icon>search</mat-icon>
                <span [matTooltip]="query.query">{{
                  truncateText(query.query, 30)
                }}</span>
              </div>

              <div class="user-cell">
                <mat-icon>person</mat-icon>
                <span>{{ query.user }}</span>
              </div>

              <div class="status-cell">
                <mat-chip [class]="'status-' + query.status">
                  <mat-icon>{{ getStatusIcon(query.status) }}</mat-icon>
                  {{ query.status.toUpperCase() }}
                </mat-chip>
              </div>

              <div class="time-cell">
                <span>{{ formatTimestamp(query.timestamp) }}</span>
                <span *ngIf="query.response_time" class="response-time">
                  {{ formatResponseTime(query.response_time) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div *ngIf="!queryStats?.total_queries" class="empty-state">
          <mat-icon>search_off</mat-icon>
          <p>No queries executed yet</p>
          <small>Query statistics will appear here</small>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .query-stats-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      .loading-container,
      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        gap: 16px;
        color: var(--mat-on-surface-variant-color);

        p {
          margin: 0;
          text-align: center;
        }
      }

      .error-container {
        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          color: var(--mat-warn-color);
        }
      }

      .query-stats-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .summary-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
      }

      .stat-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--mat-surface-variant-color);
        border-radius: 8px;

        .stat-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: var(--mat-primary-color);
          color: var(--mat-on-primary-color);

          &.success {
            background: #4caf50;
          }

          &.error {
            background: #f44336;
          }

          mat-icon {
            font-size: 20px;
            width: 20px;
            height: 20px;
          }
        }

        .stat-info {
          display: flex;
          flex-direction: column;

          .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: var(--mat-on-surface-color);
          }

          .stat-label {
            font-size: 12px;
            color: var(--mat-on-surface-variant-color);
          }
        }
      }

      .performance-metrics {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .metric-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px;
          background: var(--mat-surface-color);
          border-radius: 8px;
          border: 1px solid var(--mat-outline-variant-color);

          .metric-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;

            mat-icon {
              font-size: 18px;
              width: 18px;
              height: 18px;
              color: var(--mat-primary-color);
            }
          }

          .metric-value {
            display: flex;
            align-items: center;
            gap: 8px;

            .value {
              font-size: 16px;
              font-weight: 500;
            }
          }
        }
      }

      .top-queries,
      .recent-queries {
        h4 {
          margin: 0 0 12px 0;
          font-size: 14px;
          font-weight: 500;
          color: var(--mat-on-surface-color);
        }
      }

      .queries-list {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .query-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: var(--mat-surface-color);
          border-radius: 6px;
          border: 1px solid var(--mat-outline-variant-color);

          .query-info {
            flex: 1;

            .query-text {
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 4px;

              mat-icon {
                font-size: 16px;
                width: 16px;
                height: 16px;
                color: var(--mat-primary-color);
              }

              span {
                font-size: 13px;
                font-weight: 500;
              }
            }

            .query-stats {
              display: flex;
              gap: 12px;
              font-size: 12px;
              color: var(--mat-on-surface-variant-color);

              .count {
                font-weight: 500;
              }
            }
          }

          .query-metrics {
            display: flex;
            align-items: center;
          }
        }
      }

      .queries-table {
        .table-header {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 12px;
          padding: 8px 12px;
          background: var(--mat-surface-variant-color);
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
          color: var(--mat-on-surface-variant-color);
        }

        .table-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 12px;
          padding: 8px 12px;
          border-bottom: 1px solid var(--mat-outline-variant-color);

          &:last-child {
            border-bottom: none;
          }

          .query-cell,
          .user-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;

            mat-icon {
              font-size: 16px;
              width: 16px;
              height: 16px;
              color: var(--mat-primary-color);
            }
          }

          .status-cell {
            display: flex;
            align-items: center;
          }

          .time-cell {
            display: flex;
            flex-direction: column;
            gap: 2px;
            font-size: 12px;

            .response-time {
              color: var(--mat-on-surface-variant-color);
            }
          }
        }
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: var(--mat-on-surface-variant-color);
        text-align: center;

        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          margin-bottom: 16px;
          opacity: 0.5;
        }

        p {
          margin: 0 0 4px 0;
          font-weight: 500;
        }

        small {
          font-size: 12px;
          opacity: 0.7;
        }
      }

      .trend-chip {
        &.positive {
          background: #4caf50;
          color: white;
        }

        &.negative {
          background: #f44336;
          color: white;
        }
      }

      .rate-chip {
        &.excellent {
          background: #4caf50;
          color: white;
        }

        &.good {
          background: #8bc34a;
          color: white;
        }

        &.fair {
          background: #ffc107;
          color: black;
        }

        &.poor {
          background: #ff9800;
          color: white;
        }

        &.critical {
          background: #f44336;
          color: white;
        }
      }

      .success-rate {
        &.excellent {
          background: #4caf50;
          color: white;
        }

        &.good {
          background: #8bc34a;
          color: white;
        }

        &.fair {
          background: #ffc107;
          color: black;
        }

        &.poor {
          background: #ff9800;
          color: white;
        }

        &.critical {
          background: #f44336;
          color: white;
        }
      }

      .status-success {
        background: #4caf50;
        color: white;
      }

      .status-failed {
        background: #f44336;
        color: white;
      }

      .status-processing {
        background: #ff9800;
        color: white;
      }

      @media (max-width: 768px) {
        .summary-stats {
          grid-template-columns: repeat(2, 1fr);
        }

        .queries-table {
          .table-header,
          .table-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QueryStatsWidgetComponent implements OnInit, OnDestroy {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  private readonly destroy$ = new Subject<void>();

  queryStats: QueryStats | null = null;
  isLoading = false;
  hasError = false;

  ngOnInit(): void {
    this.loadQueryStats();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load query stats from data
   */
  private loadQueryStats(): void {
    this.isLoading = true;
    this.hasError = false;

    // Simulate loading delay
    setTimeout(() => {
      this.queryStats = this.data.query_stats || this.getDefaultQueryStats();
      this.isLoading = false;
    }, 500);
  }

  /**
   * Refresh query stats
   */
  refresh(): void {
    this.loadQueryStats();
  }

  /**
   * Get success rate percentage
   */
  getSuccessRate(): number {
    if (!this.queryStats?.total_queries) return 0;
    return Math.round(
      (this.queryStats.successful_queries / this.queryStats.total_queries) * 100
    );
  }

  /**
   * Get success rate class
   */
  getSuccessRateClass(rate?: number): string {
    const successRate = rate ?? this.getSuccessRate();

    if (successRate >= 95) return 'excellent';
    if (successRate >= 90) return 'good';
    if (successRate >= 80) return 'fair';
    if (successRate >= 70) return 'poor';
    return 'critical';
  }

  /**
   * Get success rate text
   */
  getSuccessRateText(): string {
    const rate = this.getSuccessRate();
    const classType = this.getSuccessRateClass(rate);

    const textMap: Record<string, string> = {
      excellent: 'Excellent',
      good: 'Good',
      fair: 'Fair',
      poor: 'Poor',
      critical: 'Critical',
    };

    return textMap[classType] || 'Unknown';
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: string): string {
    const iconMap: Record<string, string> = {
      success: 'check_circle',
      failed: 'error',
      processing: 'hourglass_empty',
    };

    return iconMap[status] || 'help';
  }

  /**
   * Format response time
   */
  formatResponseTime(time?: number): string {
    if (!time) return '0ms';

    if (time < 1000) {
      return `${Math.round(time)}ms`;
    } else {
      return `${(time / 1000).toFixed(1)}s`;
    }
  }

  /**
   * Format timestamp
   */
  formatTimestamp(timestamp: Date): string {
    const now = new Date();
    const diff = now.getTime() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) {
      return 'Just now';
    } else if (minutes < 60) {
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else {
      return `${days}d ago`;
    }
  }

  /**
   * Truncate text to specified length
   */
  truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }

  /**
   * Track by function for queries
   */
  trackByQueryText(index: number, query: TopQuery): string {
    return query.query;
  }

  /**
   * Track by function for recent queries
   */
  trackByQueryId(index: number, query: RecentQuery): string {
    return query.id;
  }

  /**
   * Get default query stats
   */
  private getDefaultQueryStats(): QueryStats {
    return {
      total_queries: 0,
      successful_queries: 0,
      failed_queries: 0,
      average_response_time: 0,
      queries_per_hour: 0,
      top_queries: [],
      recent_queries: [],
    };
  }
}
