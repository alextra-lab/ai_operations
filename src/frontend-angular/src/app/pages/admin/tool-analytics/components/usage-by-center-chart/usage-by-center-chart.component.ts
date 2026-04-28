/**
 * Usage By Center Chart Component
 *
 * Bar chart showing tool usage aggregated by center.
 * Uses lazy-loaded Chart.js following P3-PERF-01 patterns.
 * Part of T6-F3 Tool Analytics Dashboard.
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LibraryLoaderService } from '../../../../../services/library-loader.service';
import { CenterUsage } from '../../models/tool-analytics.models';

export type ChartMetric = 'calls' | 'cost';

@Component({
  selector: 'app-usage-by-center-chart',
  standalone: true,
  imports: [CommonModule, MatButtonToggleModule, MatProgressSpinnerModule],
  templateUrl: './usage-by-center-chart.component.html',
  styleUrls: ['./usage-by-center-chart.component.scss'],
})
export class UsageByCenterChartComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @ViewChild('chartCanvas', { static: false })
  chartCanvas!: ElementRef<HTMLCanvasElement>;

  @Input() data: CenterUsage[] = [];
  @Input() metric: ChartMetric = 'calls';
  @Output() metricChange = new EventEmitter<ChartMetric>();

  isLoading = true;
  // Chart.js dynamically loaded - types not available
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
    if (
      (changes['data'] || changes['metric']) &&
      !changes['data']?.firstChange &&
      this.chart
    ) {
      this.updateChart();
    }
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }

  onMetricChange(value: ChartMetric): void {
    this.metric = value;
    this.metricChange.emit(value);
    if (this.chart) {
      this.updateChart();
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
    if (!this.Chart || !this.chartCanvas) {
      return;
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      return;
    }

    const { labels, values, label, color } = this.getChartData();

    this.chart = new this.Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label,
            data: values,
            backgroundColor: color,
            borderColor: this.darkenColor(color),
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y', // Horizontal bar chart
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
                const value = context.parsed.x;
                if (this.metric === 'cost') {
                  return `Cost: €${value.toFixed(4)}`;
                }
                return `Calls: ${value.toLocaleString()}`;
              },
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            title: {
              display: true,
              text: this.metric === 'calls' ? 'Total Calls' : 'Total Cost (€)',
            },
          },
          y: {
            title: {
              display: true,
              text: 'Center',
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

    const { labels, values, label, color } = this.getChartData();

    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = values;
    this.chart.data.datasets[0].label = label;
    this.chart.data.datasets[0].backgroundColor = color;
    this.chart.data.datasets[0].borderColor = this.darkenColor(color);
    this.chart.options.scales.x.title.text =
      this.metric === 'calls' ? 'Total Calls' : 'Total Cost (€)';
    this.chart.update();
  }

  private getChartData(): {
    labels: string[];
    values: number[];
    label: string;
    color: string;
  } {
    // Sort by metric value descending
    const sorted = [...this.data].sort((a, b) => {
      const valA = this.metric === 'calls' ? a.total_calls : a.total_cost;
      const valB = this.metric === 'calls' ? b.total_calls : b.total_cost;
      return valB - valA;
    });

    const labels = sorted.map((d) => d.center_id || 'Unknown');
    const values = sorted.map((d) =>
      this.metric === 'calls' ? d.total_calls : d.total_cost
    );

    return {
      labels,
      values,
      label: this.metric === 'calls' ? 'Total Calls' : 'Total Cost (€)',
      color: this.metric === 'calls' ? '#2196F3' : '#9C27B0',
    };
  }

  private darkenColor(hex: string): string {
    // Simple color darkening
    const colorMap: Record<string, string> = {
      '#2196F3': '#1976D2',
      '#9C27B0': '#7B1FA2',
    };
    return colorMap[hex] || hex;
  }
}
