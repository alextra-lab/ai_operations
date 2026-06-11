/**
 * Gateway Latency Chart Component
 *
 * Line chart showing latency trends for Gateway requests using lazy-loaded Chart.js.
 * Follows P4-TOOLS-07 and P3-PERF-01 patterns.
 */

import { CommonModule } from '@angular/common';
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Input, OnChanges, OnDestroy, SimpleChanges, ViewChild, inject } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LibraryLoaderService } from '../../../../../services/library-loader.service';
import { TimeSeriesPoint } from '../../models/gateway-metrics.models';

@Component({
  selector: 'app-gateway-latency-chart',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="chart-container">
      <div *ngIf="isLoading" class="loading-overlay">
        <mat-spinner diameter="40"></mat-spinner>
        <p class="text-sm text-gray-600 mt-2">Loading chart...</p>
      </div>
      <canvas
        #chartCanvas
        [hidden]="isLoading"
        [attr.aria-label]="'Gateway latency over time chart'"
      >
      </canvas>
    </div>
  `,
  styles: [
    `
      .chart-container {
        position: relative;
        width: 100%;
        height: 300px;
        min-height: 300px;
      }

      .loading-overlay {
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

      canvas {
        width: 100% !important;
        height: 100% !important;
      }
    `,
  ],
})
export class GatewayLatencyChartComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  @ViewChild('chartCanvas', { static: false })
  chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() data: TimeSeriesPoint[] = [];

  isLoading = true;
  private chart: any = null;
  private Chart: any = null;
  private resizeObserver: ResizeObserver | null = null;

  constructor(private libraryLoader: LibraryLoaderService) {}

  async ngAfterViewInit(): Promise<void> {
    await this.loadChartLibrary();
    this.createChart();
    this.observeResize();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && !changes['data'].firstChange && this.chart) {
      this.updateChart();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }

  private observeResize(): void {
    if (!this.chartCanvas?.nativeElement || !this.chart) {
      return;
    }
    this.resizeObserver = new ResizeObserver(() => {
      this.chart?.resize();
    });
    this.resizeObserver.observe(this.chartCanvas.nativeElement);
  }

  private async loadChartLibrary(): Promise<void> {
    try {
      await this.libraryLoader.loadChartJS();
      this.Chart = (window as unknown as { Chart: unknown }).Chart;
      this.isLoading = false;
      queueMicrotask(() => this.cdr.detectChanges());
    } catch (error) {
      console.error('Failed to load Chart.js:', error);
      this.isLoading = false;
      queueMicrotask(() => this.cdr.detectChanges());
    }
  }

  private createChart(): void {
    if (!this.Chart || !this.chartCanvas) {
      return;
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      return;
    }

    const labels = this.data.map((d) => new Date(d.timestamp).toLocaleString());
    const values = this.data.map((d) => d.value);

    this.chart = new this.Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Latency (ms)',
            data: values,
            borderColor: '#2196F3',
            backgroundColor: 'rgba(33, 150, 243, 0.1)',
            tension: 0.4,
            fill: true,
          },
        ],
      },
      options: {
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
            callbacks: {
              label: (context: any) => {
                return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}ms`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Latency (ms)',
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
      return;
    }

    const labels = this.data.map((d) => new Date(d.timestamp).toLocaleString());
    const values = this.data.map((d) => d.value);

    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = values;
    this.chart.update();
  }
}
