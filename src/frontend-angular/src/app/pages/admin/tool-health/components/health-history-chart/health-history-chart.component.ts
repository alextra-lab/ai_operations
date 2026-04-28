/**
 * Health History Chart Component
 *
 * Line chart showing tool health status and response times over time.
 * Uses lazy-loaded Chart.js following P4-TOOLS-07 and P3-PERF-01 patterns.
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LibraryLoaderService } from '../../../../../services/library-loader.service';
import { ToolHealthCheckRecord } from '../../models/tool-health.models';

@Component({
  selector: 'app-health-history-chart',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="chart-container">
      <div *ngIf="isLoading" class="loading-overlay">
        <mat-spinner diameter="40"></mat-spinner>
        <p class="loading-text">Loading chart...</p>
      </div>
      <div *ngIf="!isLoading && data.length === 0" class="empty-state">
        <p class="empty-text">No health data available for this time range</p>
      </div>
      <canvas
        #chartCanvas
        [hidden]="isLoading || data.length === 0"
        [attr.aria-label]="'Tool health history chart'"
        role="img"
      >
      </canvas>
    </div>
  `,
  styles: [
    `
      .chart-container {
        position: relative;
        width: 100%;
        height: 280px;
        min-height: 280px;
      }

      .loading-overlay,
      .empty-state {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.9);
        z-index: 10;
      }

      .loading-text,
      .empty-text {
        font-size: 14px;
        color: #757575;
        margin-top: 12px;
      }

      canvas {
        width: 100% !important;
        height: 100% !important;
      }
    `,
  ],
})
export class HealthHistoryChartComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @ViewChild('chartCanvas', { static: false })
  chartCanvas!: ElementRef<HTMLCanvasElement>;

  @Input() data: ToolHealthCheckRecord[] = [];
  @Input() toolName = '';

  isLoading = true;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private chart: any = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private Chart: any = null;

  private readonly libraryLoader = inject(LibraryLoaderService);

  async ngAfterViewInit(): Promise<void> {
    await this.loadChartLibrary();
    this.createChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && !changes['data'].firstChange && this.chart) {
      this.updateChart();
    }
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }

  private async loadChartLibrary(): Promise<void> {
    try {
      await this.libraryLoader.loadChartJS();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.Chart = (window as any).Chart;
      this.isLoading = false;
    } catch (error) {
      console.error('Failed to load Chart.js:', error);
      this.isLoading = false;
    }
  }

  private createChart(): void {
    if (!this.Chart || !this.chartCanvas || this.data.length === 0) {
      return;
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      return;
    }

    // Sort data by timestamp (oldest first for chronological display)
    const sortedData = [...this.data].sort(
      (a, b) =>
        new Date(a.checked_at).getTime() - new Date(b.checked_at).getTime()
    );

    const labels = sortedData.map((d) =>
      new Date(d.checked_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    );
    const healthValues = sortedData.map((d) => (d.status === 'online' ? 1 : 0));
    const responseTimes = sortedData.map((d) => d.response_time_ms ?? 0);

    this.chart = new this.Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Health Status',
            data: healthValues,
            borderColor: '#4caf50',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            yAxisID: 'y',
            stepped: true,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 5,
          },
          {
            label: 'Response Time (ms)',
            data: responseTimes,
            borderColor: '#2196f3',
            backgroundColor: 'rgba(33, 150, 243, 0.1)',
            yAxisID: 'y1',
            tension: 0.4,
            fill: false,
            pointRadius: 2,
            pointHoverRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              label: (context: any) => {
                const label = context.dataset.label || '';
                const value = context.parsed.y;
                if (label.includes('Health')) {
                  return `${label}: ${value === 1 ? 'Online' : 'Offline'}`;
                }
                return `${label}: ${value.toFixed(0)}ms`;
              },
            },
          },
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            min: 0,
            max: 1,
            title: {
              display: true,
              text: 'Status',
            },
            ticks: {
              stepSize: 1,
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              callback: (value: any) => (value === 1 ? 'Online' : 'Offline'),
            },
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            title: {
              display: true,
              text: 'Response Time (ms)',
            },
            grid: {
              drawOnChartArea: false,
            },
          },
          x: {
            title: {
              display: true,
              text: 'Time',
            },
          },
        },
      },
    });
  }

  private updateChart(): void {
    if (!this.chart) {
      this.createChart();
      return;
    }

    if (this.data.length === 0) {
      this.chart.destroy();
      this.chart = null;
      return;
    }

    // Sort data by timestamp
    const sortedData = [...this.data].sort(
      (a, b) =>
        new Date(a.checked_at).getTime() - new Date(b.checked_at).getTime()
    );

    const labels = sortedData.map((d) =>
      new Date(d.checked_at).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    );
    const healthValues = sortedData.map((d) => (d.status === 'online' ? 1 : 0));
    const responseTimes = sortedData.map((d) => d.response_time_ms ?? 0);

    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = healthValues;
    this.chart.data.datasets[1].data = responseTimes;
    this.chart.update();
  }
}
