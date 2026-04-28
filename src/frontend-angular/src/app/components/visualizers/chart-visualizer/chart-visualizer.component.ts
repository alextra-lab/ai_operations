/**
 * Chart Visualizer Component
 *
 * Renders data as Chart.js charts (bar, line, pie, doughnut, radar, scatter).
 * Provides a wrapper around Chart.js with Angular integration.
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { Chart, type ChartConfiguration, type ChartType } from 'chart.js/auto';
import { ChartConfig } from '../../../models/output-format.model';

interface ChartDataPoint {
  label?: string;
  value?: number;
  [key: string]: unknown;
}

@Component({
  selector: 'app-chart-visualizer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="chart-visualizer-container">
      <h3 *ngIf="title" class="visualizer-title">{{ title }}</h3>
      <div class="chart-wrapper">
        <canvas #chartCanvas></canvas>
      </div>
    </div>
  `,
  styles: [
    `
      .chart-visualizer-container {
        width: 100%;
        padding: 16px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      .visualizer-title {
        margin: 0 0 16px 0;
        font-size: 1.25rem;
        font-weight: 500;
        color: rgba(0, 0, 0, 0.87);
      }

      .chart-wrapper {
        position: relative;
        width: 100%;
        height: 400px;
      }

      canvas {
        max-width: 100%;
        max-height: 100%;
      }
    `,
  ],
})
export class ChartVisualizerComponent implements AfterViewInit, OnDestroy {
  @Input() data!: unknown;
  @Input() config!: ChartConfig;
  @Input() title = '';

  @ViewChild('chartCanvas') canvasRef?: ElementRef<HTMLCanvasElement>;

  private chart?: Chart;

  ngAfterViewInit(): void {
    this.renderChart();
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  /**
   * Render the chart
   */
  private renderChart(): void {
    if (!this.canvasRef) {
      return;
    }

    const ctx = this.canvasRef.nativeElement.getContext('2d');
    if (!ctx) {
      return;
    }

    // Parse data
    const { labels, datasets } = this.parseData(this.data);

    // Build chart configuration
    const chartConfig: ChartConfiguration = {
      type: this.config.chart_type as ChartType,
      data: {
        labels: labels,
        datasets: [
          {
            label: this.config.label || 'Data',
            data: datasets[0],
            backgroundColor:
              this.config.colors || this.generateColors(labels.length),
            borderColor:
              this.config.colors?.map((c) => c) ||
              this.generateColors(labels.length),
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: this.config.show_legend !== false,
            position: this.config.legend_position || 'top',
          },
          tooltip: {
            enabled: true,
          },
        },
        ...this.config.chart_options,
      },
    };

    // Create chart
    this.chart = new Chart(ctx, chartConfig);
  }

  /**
   * Parse data into labels and datasets
   */
  private parseData(data: unknown): {
    labels: string[];
    datasets: number[][];
  } {
    // Handle array of objects with label/value
    if (Array.isArray(data)) {
      const points = data as ChartDataPoint[];
      const labels = points.map((p) => String(p.label || p['x'] || ''));
      const values = points.map((p) => Number(p.value || p['y'] || 0));

      return { labels, datasets: [values] };
    }

    // Handle object with labels and values arrays
    if (typeof data === 'object' && data !== null) {
      const obj = data as Record<string, unknown>;

      if (Array.isArray(obj['labels']) && Array.isArray(obj['values'])) {
        return {
          labels: obj['labels'].map((l) => String(l)),
          datasets: [obj['values'].map((v) => Number(v))],
        };
      }

      if (Array.isArray(obj['data'])) {
        return this.parseData(obj['data']);
      }
    }

    // Fallback
    return { labels: [], datasets: [[]] };
  }

  /**
   * Generate color palette
   */
  private generateColors(count: number): string[] {
    const colors = [
      '#2196F3', // Blue
      '#4CAF50', // Green
      '#FF9800', // Orange
      '#F44336', // Red
      '#9C27B0', // Purple
      '#00BCD4', // Cyan
      '#FFEB3B', // Yellow
      '#795548', // Brown
    ];

    return Array(count)
      .fill(0)
      .map((_, i) => colors[i % colors.length]);
  }
}
