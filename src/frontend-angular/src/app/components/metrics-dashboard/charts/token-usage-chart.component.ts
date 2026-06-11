/**
 * TokenUsageChartComponent
 *
 * Stacked bar chart showing input/output token distribution using lazy-loaded Chart.js.
 *
 * Features:
 * - Lazy loads Chart.js on first render
 * - Stacked bars for input/output tokens
 * - Updates in real-time as metrics arrive
 * - Responsive canvas sizing
 *
 * Related: P4-TOOLS-07, P3-PERF-01 (lazy loading pattern)
 */

import { CommonModule } from '@angular/common';
import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, Input, OnChanges, OnDestroy, SimpleChanges, ViewChild, inject } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ExecutionMetrics } from '../../../api/models/query-config.models';
import { LibraryLoaderService } from '../../../services/library-loader.service';

@Component({
  selector: 'app-token-usage-chart',
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
        [attr.aria-label]="'Token usage distribution chart'"
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
export class TokenUsageChartComponent
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
        type: 'bar',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Input Tokens',
              data: [],
              backgroundColor: '#4caf50',
              borderColor: '#388e3c',
              borderWidth: 1,
            },
            {
              label: 'Output Tokens',
              data: [],
              backgroundColor: '#2196f3',
              borderColor: '#1976d2',
              borderWidth: 1,
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
                footer: (tooltipItems: any[]) => {
                  const total = tooltipItems.reduce(
                    (sum, item) => sum + item.parsed.y,
                    0
                  );
                  return `Total: ${total} tokens`;
                },
              },
            },
          },
          scales: {
            y: {
              stacked: true,
              beginAtZero: true,
              title: {
                display: true,
                text: 'Tokens',
              },
            },
            x: {
              stacked: true,
              title: {
                display: true,
                text: 'Execution',
              },
            },
          },
          interaction: {
            mode: 'index',
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
    const inputTokens = this.executionHistory.map((m) => m.tokens.input_tokens);
    const outputTokens = this.executionHistory.map(
      (m) => m.tokens.output_tokens
    );

    // Update chart
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = inputTokens;
    this.chart.data.datasets[1].data = outputTokens;
    this.chart.update('none'); // Update without animation for performance
  }
}
