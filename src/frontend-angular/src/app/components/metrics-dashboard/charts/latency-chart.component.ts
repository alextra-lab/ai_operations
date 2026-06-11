/**
 * LatencyChartComponent
 *
 * Line chart showing latency trends over time using lazy-loaded Chart.js.
 *
 * Features:
 * - Lazy loads Chart.js on first render
 * - Updates in real-time as metrics arrive
 * - Responsive canvas sizing
 * - Accessible labels and tooltips
 *
 * Related: P4-TOOLS-07, P3-PERF-01 (lazy loading pattern)
 */

import { CommonModule } from '@angular/common';
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Input, OnChanges, OnDestroy, SimpleChanges, ViewChild, inject } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ExecutionMetrics } from '../../../api/models/query-config.models';
import { LibraryLoaderService } from '../../../services/library-loader.service';

@Component({
  selector: 'app-latency-chart',
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
        [attr.aria-label]="'Latency over time chart'"
      >
      </canvas>
    </div>
  `,
  styles: [
    `
      .chart-container {
        position: relative;
        width: 100%;
        height: 250px;
        min-height: 250px;
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
export class LatencyChartComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  @ViewChild('chartCanvas')
  canvasRef!: ElementRef<HTMLCanvasElement>;

  @Input() executionHistory: ExecutionMetrics[] = [];

  private chart: any;
  isLoading = true;

  constructor(private readonly libraryLoader: LibraryLoaderService) {}

  async ngAfterViewInit(): Promise<void> {
    await this.initializeChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (
      changes['executionHistory'] &&
      !changes['executionHistory'].firstChange
    ) {
      this.updateChart();
    }
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private async initializeChart(): Promise<void> {
    try {
      // Lazy load Chart.js
      await this.libraryLoader.loadChartJS();

      const Chart = (window as any).Chart;
      if (!Chart) {
        console.error('Chart.js failed to load');
        return;
      }

      const canvas = this.canvasRef.nativeElement;
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        console.error('Failed to get canvas context');
        return;
      }

      // Create chart
      this.chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Latency (ms)',
              data: [],
              borderColor: '#2196f3',
              backgroundColor: 'rgba(33, 150, 243, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 4,
              pointHoverRadius: 6,
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
                  return `Latency: ${context.parsed.y.toFixed(0)}ms`;
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
                text: 'Execution',
              },
            },
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false,
          },
        },
      });

      this.isLoading = false;
      queueMicrotask(() => this.cdr.detectChanges());

      // Initial data update
      this.updateChart();
    } catch (error) {
      console.error('Failed to initialize chart:', error);
      this.isLoading = false;
      queueMicrotask(() => this.cdr.detectChanges());
    }
  }

  private updateChart(): void {
    if (!this.chart || !this.executionHistory.length) {
      return;
    }

    // Prepare data
    const labels = this.executionHistory.map((_, i) => `#${i + 1}`);
    const data = this.executionHistory.map((m) => m.timing.total_time_ms);

    // Update chart
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = data;
    this.chart.update('none'); // Update without animation for performance
  }
}
