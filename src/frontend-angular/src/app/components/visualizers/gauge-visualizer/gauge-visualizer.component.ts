/**
 * Gauge Visualizer Component
 *
 * Renders a gauge (semicircular meter) with threshold-based coloring.
 * Uses HTML5 Canvas for rendering.
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  ViewChild,
} from '@angular/core';
import {
  GaugeConfig,
  GaugeThreshold,
} from '../../../models/output-format.model';

@Component({
  selector: 'app-gauge-visualizer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="gauge-visualizer-container">
      <h3 *ngIf="title" class="visualizer-title">{{ title }}</h3>
      <div class="gauge-wrapper">
        <canvas
          #gaugeCanvas
          width="300"
          height="200"
          aria-label="Gauge visualization"
          [attr.aria-valuenow]="value"
          [attr.aria-valuemin]="config.min"
          [attr.aria-valuemax]="config.max"
        >
        </canvas>
        <div class="gauge-label">
          <span class="value">{{ displayValue }}</span>
          <span class="label" *ngIf="currentThreshold">
            {{ currentThreshold.label }}
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .gauge-visualizer-container {
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
        text-align: center;
      }

      .gauge-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
      }

      canvas {
        display: block;
      }

      .gauge-label {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }

      .value {
        font-size: 2rem;
        font-weight: 600;
        color: rgba(0, 0, 0, 0.87);
      }

      .label {
        font-size: 1rem;
        font-weight: 500;
        padding: 4px 12px;
        border-radius: 4px;
        background-color: rgba(0, 0, 0, 0.08);
      }
    `,
  ],
})
export class GaugeVisualizerComponent implements AfterViewInit {
  @Input() value = 0;
  @Input() config!: GaugeConfig;
  @Input() title = '';

  @ViewChild('gaugeCanvas') canvasRef?: ElementRef<HTMLCanvasElement>;

  displayValue = '';
  currentThreshold?: GaugeThreshold;

  ngAfterViewInit(): void {
    this.displayValue = this.formatValue(this.value);
    this.currentThreshold = this.getThreshold(this.value);
    this.drawGauge();
  }

  /**
   * Draw the gauge on canvas
   */
  private drawGauge(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    const centerX = canvas.width / 2;
    const centerY = canvas.height - 30;
    const radius = 100;
    const lineWidth = 20;

    const min = this.config.min || 0;
    const max = this.config.max || 1;
    const range = max - min;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw arc for each threshold
    const thresholds = this.config.thresholds;

    for (let i = 0; i < thresholds.length; i++) {
      const threshold = thresholds[i];
      const prevValue = i > 0 ? thresholds[i - 1].value : min;

      const startAngle = Math.PI + ((prevValue - min) / range) * Math.PI;
      const endAngle = Math.PI + ((threshold.value - min) / range) * Math.PI;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.lineWidth = lineWidth;
      ctx.strokeStyle = threshold.color;
      ctx.stroke();
    }

    // Draw needle
    const needleAngle = Math.PI + ((this.value - min) / range) * Math.PI;
    const needleLength = radius * 0.75;

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(
      centerX + needleLength * Math.cos(needleAngle),
      centerY + needleLength * Math.sin(needleAngle)
    );
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#333';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw center dot
    ctx.beginPath();
    ctx.arc(centerX, centerY, 6, 0, 2 * Math.PI);
    ctx.fillStyle = '#333';
    ctx.fill();

    // Draw min/max labels
    ctx.font = '12px sans-serif';
    ctx.fillStyle = '#666';
    ctx.textAlign = 'left';
    ctx.fillText(String(min), centerX - radius - 20, centerY + 15);
    ctx.textAlign = 'right';
    ctx.fillText(String(max), centerX + radius + 20, centerY + 15);
  }

  /**
   * Get threshold for current value
   */
  private getThreshold(value: number): GaugeThreshold | undefined {
    const thresholds = this.config.thresholds;

    for (let i = thresholds.length - 1; i >= 0; i--) {
      if (value >= thresholds[i].value) {
        return thresholds[i];
      }
    }

    return thresholds[0];
  }

  /**
   * Format value for display
   */
  private formatValue(value: number): string {
    if (this.config.format === 'percent') {
      return `${(value * 100).toFixed(0)}%`;
    }

    return value.toFixed(2);
  }
}
