/**
 * Performance Metrics Component
 *
 * Displays system performance metrics with visualizations:
 * - Query response times
 * - Retrieval performance
 * - System resource usage
 * - Detailed performance breakdowns
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import type { ChartConfiguration, ChartOptions } from 'chart.js/auto';
import { BaseChartDirective } from 'ng2-charts';
import { Subject, interval, takeUntil } from 'rxjs';
import { UsageStatsResponse } from '../../api/models/analytics.models';
import { AnalyticsService } from '../../api/services/analytics.service';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-performance-metrics',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    BaseChartDirective,
  ],
  template: `
    <div class="performance-metrics-container">
      <!-- Header -->
      <div class="metrics-header">
        <h1>
          <lucide-icon name="gauge"></lucide-icon>
          Corpus Performance
        </h1>
        <div class="header-actions">
          <mat-form-field appearance="outline" class="time-range-selector">
            <mat-label>Time Range</mat-label>
            <mat-select
              [(ngModel)]="selectedTimeRange"
              (selectionChange)="onTimeRangeChange()"
            >
              <mat-option
                *ngFor="let range of timeRanges"
                [value]="range.value"
              >
                {{ range.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <button
            mat-raised-button
            color="primary"
            (click)="refreshData()"
            [disabled]="isLoading"
          >
            <lucide-icon name="refresh-cw"></lucide-icon>
            Refresh
          </button>
        </div>
      </div>

      <!-- Loading Indicator -->
      <div *ngIf="isLoading" class="loading-container">
        <mat-spinner diameter="40"></mat-spinner>
        <p>Loading metrics...</p>
      </div>

      <!-- Error Message -->
      <mat-card *ngIf="errorMessage && !isLoading" class="error-card">
        <lucide-icon color="warn" name="circle-alert"></lucide-icon>
        <p>{{ errorMessage }}</p>
        <button mat-button (click)="refreshData()">Retry</button>
      </mat-card>

      <!-- Metrics Content -->
      <div *ngIf="!isLoading && !errorMessage" class="metrics-content">
        <!-- Performance Stats -->
        <div class="stats-grid" *ngIf="performanceStats">
          <mat-card class="stat-card">
            <div class="stat-icon" style="background-color: #e1f5fe;">
              <lucide-icon style="color: #0277bd;" name="zap"></lucide-icon>
            </div>
            <div class="stat-content">
              <h3>
                {{ formatNumber(performanceStats.avg_chunks_per_retrieval) }}
              </h3>
              <p>Avg Chunks/Query</p>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon" style="background-color: #f3e5f5;">
              <lucide-icon style="color: #6a1b9a;" name="chart-column"></lucide-icon>
            </div>
            <div class="stat-content">
              <h3>{{ formatPercent(performanceStats.avg_relevancy_score) }}</h3>
              <p>Avg Relevancy Score</p>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon" style="background-color: #e8f5e9;">
              <lucide-icon style="color: #2e7d32;" name="trending-up"></lucide-icon>
            </div>
            <div class="stat-content">
              <h3>{{ performanceStats.total_retrievals }}</h3>
              <p>Total Retrievals</p>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon" style="background-color: #fff8e1;">
              <lucide-icon style="color: #f57f17;" name="database"></lucide-icon>
            </div>
            <div class="stat-content">
              <h3>{{ performanceStats.unique_documents_accessed }}</h3>
              <p>Documents Accessed</p>
            </div>
          </mat-card>
        </div>

        <!-- Charts -->
        <div class="charts-container">
          <!-- Relevancy Trends Chart -->
          <mat-card class="chart-card">
            <mat-card-header>
              <mat-card-title>Relevancy Score Trends</mat-card-title>
              <mat-card-subtitle
                >Average relevancy scores over time</mat-card-subtitle
              >
            </mat-card-header>
            <mat-card-content>
              <div class="chart-wrapper" *ngIf="relevancyChartData">
                <canvas
                  baseChart
                  [data]="relevancyChartData"
                  [options]="relevancyChartOptions"
                  [type]="'line'"
                >
                </canvas>
              </div>
              <div *ngIf="!relevancyChartData" class="no-data">
                <lucide-icon name="info"></lucide-icon>
                <p>No data available</p>
              </div>
            </mat-card-content>
          </mat-card>

          <!-- Performance Distribution Chart -->
          <mat-card class="chart-card">
            <mat-card-header>
              <mat-card-title>Query Volume Distribution</mat-card-title>
              <mat-card-subtitle>Daily query counts</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <div class="chart-wrapper" *ngIf="volumeChartData">
                <canvas
                  baseChart
                  [data]="volumeChartData"
                  [options]="volumeChartOptions"
                  [type]="'bar'"
                >
                </canvas>
              </div>
              <div *ngIf="!volumeChartData" class="no-data">
                <lucide-icon name="info"></lucide-icon>
                <p>No data available</p>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Top Performers Table -->
        <mat-card class="table-card" *ngIf="performanceStats">
          <mat-card-header>
            <mat-card-title>Top Performing Documents</mat-card-title>
            <mat-card-subtitle
              >Documents with highest relevancy scores</mat-card-subtitle
            >
          </mat-card-header>
          <mat-card-content>
            <table
              mat-table
              [dataSource]="performanceStats.top_relevancy_documents"
              class="performance-table"
            >
              <ng-container matColumnDef="title">
                <th mat-header-cell *matHeaderCellDef>Document</th>
                <td mat-cell *matCellDef="let doc">{{ doc.title }}</td>
              </ng-container>

              <ng-container matColumnDef="avg_relevancy_score">
                <th mat-header-cell *matHeaderCellDef>Avg Relevancy</th>
                <td mat-cell *matCellDef="let doc">
                  <div
                    class="score-badge"
                    [class.high]="doc.avg_relevancy_score > 0.8"
                  >
                    {{ formatPercent(doc.avg_relevancy_score) }}
                  </div>
                </td>
              </ng-container>

              <ng-container matColumnDef="access_count">
                <th mat-header-cell *matHeaderCellDef>Access Count</th>
                <td mat-cell *matCellDef="let doc">{{ doc.access_count }}</td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    `
      .performance-metrics-container {
        padding: 24px;
        max-width: 1600px;
        margin: 0 auto;
      }

      .metrics-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;

        h1 {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 0;
          font-size: 28px;
          font-weight: 500;

          mat-icon {
            font-size: 32px;
            width: 32px;
            height: 32px;
          }
        }

        .header-actions {
          display: flex;
          gap: 16px;
          align-items: center;

          .time-range-selector {
            min-width: 200px;
            margin-bottom: -1.25em;
          }
        }
      }

      .loading-container,
      .error-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px;
        gap: 16px;
      }

      .metrics-content {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 16px;
      }

      .stat-card {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px;

        .stat-icon {
          width: 56px;
          height: 56px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;

          mat-icon {
            font-size: 28px;
            width: 28px;
            height: 28px;
          }
        }

        .stat-content {
          flex: 1;

          h3 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
          }

          p {
            margin: 4px 0 0;
            font-size: 14px;
            color: #666;
          }
        }
      }

      .charts-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        gap: 24px;
      }

      .chart-card {
        .chart-wrapper {
          height: 300px;
          position: relative;
        }

        .no-data {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 300px;
          color: #999;

          mat-icon {
            font-size: 48px;
            width: 48px;
            height: 48px;
          }
        }
      }

      .table-card {
        .performance-table {
          width: 100%;

          .score-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            background-color: #e0e0e0;
            font-weight: 500;

            &.high {
              background-color: #c8e6c9;
              color: #2e7d32;
            }
          }
        }
      }

      @media (max-width: 768px) {
        .metrics-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 16px;

          .header-actions {
            width: 100%;
            flex-direction: column;
          }
        }

        .charts-container {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class PerformanceMetricsComponent implements OnInit, OnDestroy {
  private analyticsService = inject(AnalyticsService);
  private destroy$ = new Subject<void>();

  isLoading = false;
  selectedTimeRange = 24;
  timeRanges = [
    { value: 24, label: 'Last 24 Hours' },
    { value: 168, label: 'Last 7 Days' },
    { value: 720, label: 'Last 30 Days' },
  ];

  performanceStats: UsageStatsResponse | null = null;
  errorMessage: string | null = null;

  displayedColumns: string[] = ['title', 'avg_relevancy_score', 'access_count'];

  relevancyChartData: ChartConfiguration<'line'>['data'] | null = null;
  relevancyChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 1.0,
        title: {
          display: true,
          text: 'Relevancy Score',
        },
      },
    },
  };

  volumeChartData: ChartConfiguration<'bar'>['data'] | null = null;
  volumeChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Query Count',
        },
      },
    },
  };

  ngOnInit(): void {
    this.loadMetrics();

    // Auto-refresh every 5 minutes
    interval(300000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.loadMetrics());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadMetrics(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.analyticsService
      .getUsageStats({ hours: this.selectedTimeRange })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (stats) => {
          this.performanceStats = stats;
          this.updateCharts();
          this.isLoading = false;
        },
        error: (error) => {
          this.errorMessage = error.message;
          this.isLoading = false;
        },
      });
  }

  onTimeRangeChange(): void {
    this.loadMetrics();
  }

  refreshData(): void {
    this.loadMetrics();
  }

  private updateCharts(): void {
    if (!this.performanceStats) return;

    const sortedTrends = [...this.performanceStats.daily_trends].reverse();

    // Relevancy trends
    this.relevancyChartData = {
      labels: sortedTrends.map((t) => t.date),
      datasets: [
        {
          label: 'Avg Relevancy',
          data: sortedTrends.map((t) => t.avg_relevancy),
          borderColor: '#3f51b5',
          backgroundColor: 'rgba(63, 81, 181, 0.2)',
          tension: 0.4,
          fill: true,
        },
      ],
    };

    // Volume distribution
    this.volumeChartData = {
      labels: sortedTrends.map((t) => t.date),
      datasets: [
        {
          label: 'Queries',
          data: sortedTrends.map((t) => t.queries),
          backgroundColor: '#4caf50',
        },
      ],
    };
  }

  formatNumber(num: number): string {
    return num.toFixed(2);
  }

  formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }
}
