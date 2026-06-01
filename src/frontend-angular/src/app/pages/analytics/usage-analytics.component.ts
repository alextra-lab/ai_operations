/**
 * Usage Analytics Component
 *
 * Displays usage analytics with interactive charts including:
 * - Hot documents
 * - Daily query trends
 * - Top relevancy documents
 * - Overall usage statistics
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import type { ChartConfiguration, ChartOptions } from 'chart.js/auto';
import { BaseChartDirective } from 'ng2-charts';
import { Subject, interval, takeUntil } from 'rxjs';
import {
  HotDocumentsResponse,
  UsageStatsResponse,
} from '../../api/models/analytics.models';
import { AnalyticsService } from '../../api/services/analytics.service';

@Component({
  selector: 'app-usage-analytics',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    BaseChartDirective,
  ],
  templateUrl: './usage-analytics.component.html',
  styleUrls: ['./usage-analytics.component.scss'],
})
export class UsageAnalyticsComponent implements OnInit, OnDestroy {
  private analyticsService = inject(AnalyticsService);
  private destroy$ = new Subject<void>();

  isLoading = false;
  selectedTimeRange = 24; // hours
  timeRanges = [
    { value: 24, label: 'Last 24 Hours' },
    { value: 168, label: 'Last 7 Days' },
    { value: 720, label: 'Last 30 Days' },
  ];

  usageStats: UsageStatsResponse | null = null;
  hotDocuments: HotDocumentsResponse | null = null;
  errorMessage: string | null = null;

  // Chart data
  dailyTrendsChartData: ChartConfiguration<'line'>['data'] | null = null;
  dailyTrendsChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      title: {
        display: true,
        text: 'Daily Query Trends',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Queries',
        },
      },
      y1: {
        beginAtZero: true,
        position: 'right',
        max: 1.0,
        title: {
          display: true,
          text: 'Avg Relevancy',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  topDocumentsChartData: ChartConfiguration<'bar'>['data'] | null = null;
  topDocumentsChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: 'Top Documents by Relevancy',
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        max: 1.0,
        title: {
          display: true,
          text: 'Relevancy Score',
        },
      },
    },
  };

  // Table columns for hot documents
  hotDocsColumns: string[] = [
    'title',
    'access_count',
    'unique_users',
    'last_accessed',
  ];

  ngOnInit(): void {
    this.loadAnalytics();

    // Auto-refresh every 5 minutes
    interval(300000)
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.loadAnalytics());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadAnalytics(): void {
    this.isLoading = true;
    this.errorMessage = null;

    // Load usage stats
    this.analyticsService
      .getUsageStats({ hours: this.selectedTimeRange })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (stats) => {
          this.usageStats = stats;
          this.updateCharts();
        },
        error: (error) => {
          this.errorMessage = error.message;
          this.isLoading = false;
        },
      });

    // Load hot documents
    this.analyticsService
      .getHotDocuments({ hours: this.selectedTimeRange, limit: 10 })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (docs) => {
          this.hotDocuments = docs;
          this.isLoading = false;
        },
        error: (error) => {
          this.errorMessage = error.message;
          this.isLoading = false;
        },
      });
  }

  onTimeRangeChange(): void {
    this.loadAnalytics();
  }

  refreshData(): void {
    this.loadAnalytics();
  }

  private updateCharts(): void {
    if (!this.usageStats) return;

    // Update daily trends chart
    const sortedTrends = [...this.usageStats.daily_trends].reverse();
    this.dailyTrendsChartData = {
      labels: sortedTrends.map((t) => t.date),
      datasets: [
        {
          label: 'Queries',
          data: sortedTrends.map((t) => t.queries),
          borderColor: '#3f51b5',
          backgroundColor: 'rgba(63, 81, 181, 0.2)',
          yAxisID: 'y',
          tension: 0.4,
        },
        {
          label: 'Avg Relevancy',
          data: sortedTrends.map((t) => t.avg_relevancy),
          borderColor: '#4caf50',
          backgroundColor: 'rgba(76, 175, 80, 0.2)',
          yAxisID: 'y1',
          tension: 0.4,
        },
      ],
    };

    // Update top documents chart
    const topDocs = this.usageStats.top_relevancy_documents.slice(0, 5);
    this.topDocumentsChartData = {
      labels: topDocs.map((d) => this.truncateTitle(d.title, 30)),
      datasets: [
        {
          label: 'Relevancy Score',
          data: topDocs.map((d) => d.avg_relevancy_score),
          backgroundColor: '#2196f3',
        },
      ],
    };
  }

  private truncateTitle(title: string, maxLength: number): string {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString();
  }

  formatNumber(num: number): string {
    return this.analyticsService.formatNumber(num);
  }

  formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }
}
