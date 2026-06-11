/**
 * Health Summary Cards Component
 *
 * Displays KPI cards for overall tool health status.
 * Shows total tools, online/offline counts, and health percentage.
 */

import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LucideAngularModule } from 'lucide-angular';
import { HealthSummary } from '../../models/tool-health.models';

@Component({
  selector: 'app-health-summary-cards',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './health-summary-cards.component.html',
  styleUrls: ['./health-summary-cards.component.scss'],
})
export class HealthSummaryCardsComponent {
  @Input() summary: HealthSummary | null = null;
  @Input() isLoading = false;

  /**
   * Get health percentage color class based on value
   */
  getHealthColor(): string {
    if (!this.summary) {
      return 'neutral';
    }
    const pct = this.summary.health_percentage;
    if (pct >= 80) {
      return 'healthy';
    }
    if (pct >= 50) {
      return 'warning';
    }
    return 'critical';
  }

  /**
   * Format last check timestamp for display
   */
  formatLastCheck(): string {
    if (!this.summary?.last_check) {
      return 'Never checked';
    }
    const date = new Date(this.summary.last_check);
    return date.toLocaleString();
  }
}
