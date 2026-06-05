/**
 * Usage Summary Cards Component
 *
 * Displays aggregated analytics summary in metric cards.
 * Part of T6-F3 Tool Analytics Dashboard.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  AggregateAnalytics,
  formatCost,
  formatDuration,
  getSuccessRateClass,
} from '../../models/tool-analytics.models';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-usage-summary-cards',
  standalone: true,
  imports: [
    LucideAngularModule,CommonModule, MatCardModule, MatTooltipModule],
  templateUrl: './usage-summary-cards.component.html',
  styleUrls: ['./usage-summary-cards.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsageSummaryCardsComponent {
  @Input() aggregates: AggregateAnalytics | null = null;

  /**
   * Format number with locale string
   */
  formatNumber(value: number): string {
    return value.toLocaleString();
  }

  /**
   * Format percentage value
   */
  formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
  }

  /**
   * Get success rate color class
   */
  getSuccessClass(): string {
    if (!this.aggregates) {
      return '';
    }
    return getSuccessRateClass(this.aggregates.average_success_rate);
  }

  /**
   * Format cost for display
   */
  formatCostValue(value: number): string {
    return formatCost(value);
  }

  /**
   * Format duration for display
   */
  formatDurationValue(value: number): string {
    return formatDuration(value);
  }

  /**
   * Get most used tool display text
   */
  getMostUsedToolText(): string {
    if (!this.aggregates?.most_used_tool) {
      return 'N/A';
    }
    const name = this.aggregates.most_used_tool;
    // Truncate long names
    return name.length > 20 ? name.substring(0, 17) + '...' : name;
  }

  /**
   * Get most used tool tooltip
   */
  getMostUsedToolTooltip(): string {
    if (!this.aggregates?.most_used_tool) {
      return 'No tools used';
    }
    return `${this.aggregates.most_used_tool} (${this.formatNumber(this.aggregates.most_used_tool_calls)} calls)`;
  }
}
