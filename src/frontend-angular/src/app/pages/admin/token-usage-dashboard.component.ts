/**
 * Token Usage Dashboard Component
 *
 * Admin-only dashboard for monitoring token usage, costs, and analytics
 * across centers, users, and models.
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import type { ChartConfiguration, ChartOptions } from 'chart.js/auto';
import { LucideAngularModule } from 'lucide-angular';
import { BaseChartDirective } from 'ng2-charts';
import { Subject, interval, takeUntil } from 'rxjs';
import {
  AllCentersUsageSummaryResponse,
  CenterUsageSummaryResponse,
  TokenUsageFilters,
  TokenUsageSummary,
} from '../../api/models/token-usage.models';
import { AdminAnalyticsService } from '../../api/services/admin-analytics.service';

@Component({
  selector: 'app-token-usage-dashboard',
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
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatTooltipModule,
    BaseChartDirective,
  ],
  template: `
    <div class="token-usage-dashboard">
      <!-- Header -->
      <div class="dashboard-header">
        <h1>Token Usage Dashboard</h1>
        <div class="header-controls">
          <mat-form-field appearance="outline" class="date-range-field">
            <mat-label>Start Date</mat-label>
            <input
              matInput
              [matDatepicker]="startPicker"
              [(ngModel)]="filters.startDate"
              (dateChange)="onDateChange()"
            />
            <mat-datepicker-toggle
              matSuffix
              [for]="startPicker"
            ></mat-datepicker-toggle>
            <mat-datepicker #startPicker></mat-datepicker>
          </mat-form-field>

          <mat-form-field appearance="outline" class="date-range-field">
            <mat-label>End Date</mat-label>
            <input
              matInput
              [matDatepicker]="endPicker"
              [(ngModel)]="filters.endDate"
              (dateChange)="onDateChange()"
            />
            <mat-datepicker-toggle
              matSuffix
              [for]="endPicker"
            ></mat-datepicker-toggle>
            <mat-datepicker #endPicker></mat-datepicker>
          </mat-form-field>

          <mat-form-field appearance="outline" class="center-select">
            <mat-label>Center</mat-label>
            <mat-select
              [(ngModel)]="filters.centerId"
              (selectionChange)="onFiltersChange()"
            >
              <mat-option [value]="undefined">All Centers</mat-option>
              <mat-option
                *ngFor="let center of availableCenters"
                [value]="center"
              >
                {{ center }}
              </mat-option>
            </mat-select>
          </mat-form-field>

          <button
            mat-raised-button
            color="primary"
            (click)="refreshData()"
            [disabled]="isLoading"
            matTooltip="Refresh Data"
          >
            <lucide-icon name="refresh-cw"></lucide-icon>
            Refresh
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading" class="loading-overlay">
        <mat-spinner diameter="50"></mat-spinner>
        <p>Loading token usage data...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="!isLoading && errorMessage" class="error-message">
        <lucide-icon color="warn" name="circle-alert"></lucide-icon>
        <p>{{ errorMessage }}</p>
        <button mat-button (click)="refreshData()">Try Again</button>
      </div>

      <!-- Dashboard Content -->
      <div
        *ngIf="!isLoading && !errorMessage && (usageData || centerData)"
        class="dashboard-content"
      >
        <!-- Summary Cards -->
        <div class="summary-cards">
          <mat-card class="summary-card">
            <mat-card-header>
              <mat-card-title>Total Tokens</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <p class="metric-value">{{ formatNumber(getTotalTokens()) }}</p>
              <p class="metric-subtitle">
                {{ formatNumber(getTotalTokensIn()) }} in /
                {{ formatNumber(getTotalTokensOut()) }} out
              </p>
            </mat-card-content>
          </mat-card>

          <mat-card class="summary-card">
            <mat-card-header>
              <mat-card-title>Total Requests</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <p class="metric-value">{{ formatNumber(getTotalRequests()) }}</p>
              <p class="metric-subtitle">{{ getUniqueUsers() }} unique users</p>
            </mat-card-content>
          </mat-card>

          <mat-card class="summary-card">
            <mat-card-header>
              <mat-card-title>Total Cost</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <p class="metric-value">{{ formatCurrency(getTotalCost()) }}</p>
              <p class="metric-subtitle">
                Avg: {{ formatCurrency(getAvgTokensPerRequest()) }} per request
              </p>
            </mat-card-content>
          </mat-card>

          <mat-card class="summary-card">
            <mat-card-header>
              <mat-card-title>Active Centers</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <p class="metric-value">{{ getCentersCount() }}</p>
              <p class="metric-subtitle">
                {{ getActiveCentersCount() }} with usage
              </p>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Charts and Tables -->
        <mat-tab-group class="dashboard-tabs">
          <!-- Centers Overview Tab -->
          <mat-tab label="Centers Overview">
            <div class="tab-content">
              <!-- Token Usage by Center Chart -->
              <mat-card class="chart-card">
                <mat-card-header>
                  <mat-card-title>Token Usage by Center</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="chart-container">
                    <canvas
                      baseChart
                      [data]="centersTokenChartData"
                      [options]="chartOptions"
                      [type]="'bar'"
                    >
                    </canvas>
                  </div>
                </mat-card-content>
              </mat-card>

              <!-- Cost by Center Chart -->
              <mat-card class="chart-card" *ngIf="hasCostData()">
                <mat-card-header>
                  <mat-card-title>Cost by Center</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="chart-container">
                    <canvas
                      baseChart
                      [data]="centersCostChartData"
                      [options]="chartOptions"
                      [type]="'bar'"
                    >
                    </canvas>
                  </div>
                </mat-card-content>
              </mat-card>

              <!-- Centers Table -->
              <mat-card class="table-card">
                <mat-card-header>
                  <mat-card-title>Centers Summary</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <table
                    mat-table
                    [dataSource]="getCentersTableData()"
                    class="full-width"
                  >
                    <!-- Center ID Column -->
                    <ng-container matColumnDef="center_id">
                      <th mat-header-cell *matHeaderCellDef>Center ID</th>
                      <td mat-cell *matCellDef="let element">
                        {{ element.center_id || 'Unknown' }}
                      </td>
                    </ng-container>

                    <!-- Total Tokens Column -->
                    <ng-container matColumnDef="total_tokens">
                      <th mat-header-cell *matHeaderCellDef>Total Tokens</th>
                      <td mat-cell *matCellDef="let element">
                        {{ formatNumber(element.total_tokens) }}
                      </td>
                    </ng-container>

                    <!-- Total Requests Column -->
                    <ng-container matColumnDef="total_requests">
                      <th mat-header-cell *matHeaderCellDef>Requests</th>
                      <td mat-cell *matCellDef="let element">
                        {{ formatNumber(element.total_requests) }}
                      </td>
                    </ng-container>

                    <!-- Unique Users Column -->
                    <ng-container matColumnDef="unique_users">
                      <th mat-header-cell *matHeaderCellDef>Users</th>
                      <td mat-cell *matCellDef="let element">
                        {{ element.unique_users || 0 }}
                      </td>
                    </ng-container>

                    <!-- Total Cost Column -->
                    <ng-container matColumnDef="total_cost">
                      <th mat-header-cell *matHeaderCellDef>Cost</th>
                      <td mat-cell *matCellDef="let element">
                        {{ formatCurrency(element.total_cost) }}
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                    <tr
                      mat-row
                      *matRowDef="let row; columns: displayedColumns"
                    ></tr>

                    <!-- Row shown when there is no matching data. -->
                    <tr class="mat-row" *matNoDataRow>
                      <td class="mat-cell" colspan="5">
                        No center data available for the selected period.
                      </td>
                    </tr>
                  </table>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Model Usage Tab -->
          <mat-tab label="Model Usage">
            <div class="tab-content">
              <!-- Top Models Chart -->
              <mat-card class="chart-card">
                <mat-card-header>
                  <mat-card-title>Top Models by Usage</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="chart-container">
                    <canvas
                      baseChart
                      [data]="modelsChartData"
                      [options]="chartOptions"
                      [type]="'doughnut'"
                    >
                    </canvas>
                  </div>
                </mat-card-content>
              </mat-card>

              <!-- Models Table -->
              <mat-card class="table-card">
                <mat-card-header>
                  <mat-card-title>Model Usage Summary</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <table
                    mat-table
                    [dataSource]="getModelsTableData()"
                    class="full-width"
                  >
                    <!-- Model Column -->
                    <ng-container matColumnDef="model">
                      <th mat-header-cell *matHeaderCellDef>Model</th>
                      <td mat-cell *matCellDef="let element">
                        {{ element.model }}
                      </td>
                    </ng-container>

                    <!-- Requests Column -->
                    <ng-container matColumnDef="requests">
                      <th mat-header-cell *matHeaderCellDef>Requests</th>
                      <td mat-cell *matCellDef="let element">
                        {{ element.requests }}
                      </td>
                    </ng-container>

                    <!-- Percentage Column -->
                    <ng-container matColumnDef="percentage">
                      <th mat-header-cell *matHeaderCellDef>Usage %</th>
                      <td mat-cell *matCellDef="let element">
                        {{ element.percentage }}%
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="modelColumns"></tr>
                    <tr
                      mat-row
                      *matRowDef="let row; columns: modelColumns"
                    ></tr>

                    <!-- Row shown when there is no matching data. -->
                    <tr class="mat-row" *matNoDataRow>
                      <td class="mat-cell" colspan="3">
                        No model usage data available.
                      </td>
                    </tr>
                  </table>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>
    </div>
  `,
  styles: [
    `
      .token-usage-dashboard {
        padding: 24px;
        max-width: 1400px;
        margin: 0 auto;
      }

      .dashboard-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        flex-wrap: wrap;
        gap: 16px;
      }

      .dashboard-header h1 {
        margin: 0;
        font-size: 28px;
        font-weight: 500;
      }

      .header-controls {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }

      .date-range-field {
        width: 150px;
      }

      .center-select {
        width: 200px;
      }

      .loading-overlay,
      .error-message {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 50px;
        gap: 16px;
        color: #666;
      }

      .error-message mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
      }

      .summary-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 24px;
        margin-bottom: 24px;
      }

      .summary-card {
        text-align: center;
      }

      .summary-card mat-card-title {
        font-size: 1.1em;
        color: #555;
      }

      .metric-value {
        font-size: 2.5em;
        font-weight: 600;
        color: #3f51b5;
        margin: 10px 0 5px 0;
      }

      .metric-subtitle {
        font-size: 0.9em;
        color: #666;
        margin: 0;
      }

      .dashboard-tabs {
        margin-top: 24px;
      }

      .tab-content {
        padding: 24px 0;
      }

      .chart-card,
      .table-card {
        margin-bottom: 24px;
      }

      .chart-container {
        position: relative;
        height: 400px;
        width: 100%;
      }

      .full-width {
        width: 100%;
      }

      table {
        width: 100%;
      }

      .mat-column-center_id {
        width: 200px;
      }

      .mat-column-total_tokens {
        width: 150px;
      }

      .mat-column-total_requests {
        width: 120px;
      }

      .mat-column-unique_users {
        width: 100px;
      }

      .mat-column-total_cost {
        width: 120px;
      }

      .mat-column-model {
        width: 300px;
      }

      .mat-column-requests {
        width: 120px;
      }

      .mat-column-percentage {
        width: 100px;
      }

      @media (max-width: 768px) {
        .dashboard-header {
          flex-direction: column;
          align-items: stretch;
        }

        .header-controls {
          justify-content: center;
        }

        .summary-cards {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class TokenUsageDashboardComponent implements OnInit, OnDestroy {
  private adminAnalyticsService = inject(AdminAnalyticsService);
  private destroy$ = new Subject<void>();

  // Component state
  isLoading = true;
  errorMessage: string | null = null;
  usageData: AllCentersUsageSummaryResponse | null = null;
  centerData: CenterUsageSummaryResponse | null = null;

  // Filters
  filters: TokenUsageFilters = {};
  availableCenters: string[] = [];

  // Table configurations
  displayedColumns: string[] = [
    'center_id',
    'total_tokens',
    'total_requests',
    'unique_users',
    'total_cost',
  ];
  modelColumns: string[] = ['model', 'requests', 'percentage'];

  // Chart configurations
  public chartOptions: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Center',
        },
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Tokens',
        },
      },
    },
  };

  // Chart data
  public centersTokenChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [
      {
        data: [],
        label: 'Total Tokens',
        backgroundColor: 'rgba(63, 81, 181, 0.6)',
        borderColor: 'rgba(63, 81, 181, 1)',
        borderWidth: 1,
      },
    ],
  };

  public centersCostChartData: ChartConfiguration<'bar'>['data'] = {
    labels: [],
    datasets: [
      {
        data: [],
        label: 'Total Cost ($)',
        backgroundColor: 'rgba(76, 175, 80, 0.6)',
        borderColor: 'rgba(76, 175, 80, 1)',
        borderWidth: 1,
      },
    ],
  };

  public modelsChartData: ChartConfiguration<'doughnut'>['data'] = {
    labels: [],
    datasets: [
      {
        data: [],
        backgroundColor: [
          'rgba(63, 81, 181, 0.6)',
          'rgba(76, 175, 80, 0.6)',
          'rgba(255, 152, 0, 0.6)',
          'rgba(244, 67, 54, 0.6)',
          'rgba(156, 39, 176, 0.6)',
          'rgba(0, 188, 212, 0.6)',
          'rgba(255, 193, 7, 0.6)',
          'rgba(96, 125, 139, 0.6)',
        ],
        borderColor: [
          'rgba(63, 81, 181, 1)',
          'rgba(76, 175, 80, 1)',
          'rgba(255, 152, 0, 1)',
          'rgba(244, 67, 54, 1)',
          'rgba(156, 39, 176, 1)',
          'rgba(0, 188, 212, 1)',
          'rgba(255, 193, 7, 1)',
          'rgba(96, 125, 139, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  ngOnInit(): void {
    this.initializeFilters();
    this.refreshData();

    // Auto-refresh every 5 minutes
    interval(300000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.refreshData());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeFilters(): void {
    // Set default date range to last 30 days
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    this.filters = {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
  }

  onDateChange(): void {
    this.onFiltersChange();
  }

  onFiltersChange(): void {
    this.refreshData();
  }

  refreshData(): void {
    this.isLoading = true;
    this.errorMessage = null;

    // If filtering by center, get center-specific data
    if (this.filters.centerId) {
      this.adminAnalyticsService
        .getCenterTokenUsage(
          this.filters.centerId,
          this.filters.startDate,
          this.filters.endDate
        )
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (data) => {
            this.centerData = data;
            this.usageData = null;
            this.updateAvailableCenters();
            this.updateCharts();
            this.isLoading = false;
          },
          error: (err) => {
            console.error('Error fetching center token usage data:', err);
            this.errorMessage =
              err.message ||
              'Failed to load center token usage data. Please try again.';
            this.isLoading = false;
          },
        });
    } else {
      // Get all centers data
      this.adminAnalyticsService
        .getAllCentersTokenUsage(this.filters.startDate, this.filters.endDate)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (data) => {
            this.usageData = data;
            this.centerData = null;
            this.updateAvailableCenters();
            this.updateCharts();
            this.isLoading = false;
          },
          error: (err) => {
            console.error('Error fetching token usage data:', err);
            this.errorMessage =
              err.message ||
              'Failed to load token usage data. Please try again.';
            this.isLoading = false;
          },
        });
    }
  }

  private updateAvailableCenters(): void {
    if (this.usageData) {
      this.availableCenters = this.usageData.centers
        .map((center) => center.center_id)
        .filter((id): id is string => id !== undefined && id !== null)
        .sort();
    } else if (this.centerData) {
      // For center-specific view, we still need to populate available centers
      // This would typically come from a separate endpoint, but for now we'll use the current center
      this.availableCenters = this.centerData.center_id
        ? [this.centerData.center_id]
        : [];
    }
  }

  private updateCharts(): void {
    if (this.usageData) {
      // Update centers token chart
      this.centersTokenChartData.labels = this.usageData.centers.map(
        (c) => c.center_id || 'Unknown'
      );
      this.centersTokenChartData.datasets[0].data = this.usageData.centers.map(
        (c) => c.total_tokens
      );

      // Update centers cost chart
      this.centersCostChartData.labels = this.usageData.centers.map(
        (c) => c.center_id || 'Unknown'
      );
      this.centersCostChartData.datasets[0].data = this.usageData.centers.map(
        (c) => c.total_cost || 0
      );

      // Update models chart
      const modelData = this.getModelsChartData();
      this.modelsChartData.labels = modelData.labels;
      this.modelsChartData.datasets[0].data = modelData.data;
    } else if (this.centerData) {
      // For center-specific view, show single center data
      this.centersTokenChartData.labels = [this.centerData.center_id];
      this.centersTokenChartData.datasets[0].data = [
        this.centerData.summary.total_tokens,
      ];

      this.centersCostChartData.labels = [this.centerData.center_id];
      this.centersCostChartData.datasets[0].data = [
        this.centerData.summary.total_cost || 0,
      ];

      // Update models chart for center
      const modelData = this.getCenterModelsChartData();
      this.modelsChartData.labels = modelData.labels;
      this.modelsChartData.datasets[0].data = modelData.data;
    }

    // Trigger chart updates
    this.centersTokenChartData = { ...this.centersTokenChartData };
    this.centersCostChartData = { ...this.centersCostChartData };
    this.modelsChartData = { ...this.modelsChartData };
  }

  private getModelsChartData(): { labels: string[]; data: number[] } {
    if (!this.usageData?.grand_total?.top_models) {
      return { labels: [], data: [] };
    }

    const models = Object.entries(this.usageData.grand_total.top_models)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8); // Top 8 models

    return {
      labels: models.map(([model]) => model),
      data: models.map(([, count]) => count),
    };
  }

  private getCenterModelsChartData(): { labels: string[]; data: number[] } {
    if (!this.centerData?.summary?.top_models) {
      return { labels: [], data: [] };
    }

    const models = Object.entries(this.centerData.summary.top_models)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8); // Top 8 models

    return {
      labels: models.map(([model]) => model),
      data: models.map(([, count]) => count),
    };
  }

  getModelsTableData(): {
    model: string;
    requests: number;
    percentage: number;
  }[] {
    const topModels =
      this.usageData?.grand_total?.top_models ||
      this.centerData?.summary?.top_models;
    const totalRequests = this.getTotalRequests();

    if (!topModels || totalRequests === 0) {
      return [];
    }

    return Object.entries(topModels)
      .map(([model, requests]) => ({
        model,
        requests,
        percentage: Math.round((requests / totalRequests) * 100),
      }))
      .sort((a, b) => b.requests - a.requests);
  }

  getCentersTableData(): TokenUsageSummary[] {
    if (this.usageData) {
      return this.usageData.centers;
    } else if (this.centerData) {
      return [this.centerData.summary];
    }
    return [];
  }

  getTotalTokens(): number {
    return (
      this.usageData?.grand_total?.total_tokens ||
      this.centerData?.summary?.total_tokens ||
      0
    );
  }

  getTotalTokensIn(): number {
    return (
      this.usageData?.grand_total?.total_tokens_in ||
      this.centerData?.summary?.total_tokens_in ||
      0
    );
  }

  getTotalTokensOut(): number {
    return (
      this.usageData?.grand_total?.total_tokens_out ||
      this.centerData?.summary?.total_tokens_out ||
      0
    );
  }

  getTotalRequests(): number {
    return (
      this.usageData?.grand_total?.total_requests ||
      this.centerData?.summary?.total_requests ||
      0
    );
  }

  getUniqueUsers(): number {
    return (
      this.usageData?.grand_total?.unique_users ||
      this.centerData?.summary?.unique_users ||
      0
    );
  }

  getTotalCost(): number | undefined {
    return (
      this.usageData?.grand_total?.total_cost ||
      this.centerData?.summary?.total_cost
    );
  }

  getAvgTokensPerRequest(): number | undefined {
    return (
      this.usageData?.grand_total?.avg_tokens_per_request ||
      this.centerData?.summary?.avg_tokens_per_request
    );
  }

  getCentersCount(): number {
    if (this.usageData) {
      return this.usageData.centers.length;
    } else if (this.centerData) {
      return 1;
    }
    return 0;
  }

  getActiveCentersCount(): number {
    if (this.usageData) {
      return this.usageData.centers.filter((c) => c.total_requests > 0).length;
    } else if (this.centerData) {
      return this.centerData.summary.total_requests > 0 ? 1 : 0;
    }
    return 0;
  }

  hasCostData(): boolean {
    if (this.usageData) {
      return this.usageData.centers.some(
        (c) => c.total_cost && c.total_cost > 0
      );
    } else if (this.centerData) {
      return (this.centerData.summary.total_cost || 0) > 0;
    }
    return false;
  }

  formatNumber(value: number | undefined): string {
    if (value === undefined || value === null) return '0';
    return new Intl.NumberFormat().format(value);
  }

  formatCurrency(value: number | undefined): string {
    if (value === undefined || value === null) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  }
}
