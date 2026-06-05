/**
 * Usage By Tool Table Component
 *
 * Displays per-tool usage statistics in a sortable table.
 * Part of T6-F3 Tool Analytics Dashboard.
 */

import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { MatSort, MatSortModule, Sort } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  formatCost,
  formatDuration,
  getSuccessRateClass,
  ToolUsageSummary,
} from '../../models/tool-analytics.models';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-usage-by-tool-table',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatSortModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './usage-by-tool-table.component.html',
  styleUrls: ['./usage-by-tool-table.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsageByToolTableComponent implements OnChanges {
  @Input() data: ToolUsageSummary[] = [];

  @ViewChild(MatSort) sort!: MatSort;

  dataSource = new MatTableDataSource<ToolUsageSummary>();

  displayedColumns = [
    'tool_name',
    'total_calls',
    'successful_calls',
    'success_rate',
    'avg_duration_ms',
    'total_cost',
  ];

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data']) {
      this.dataSource.data = this.data;
      if (this.sort) {
        this.dataSource.sort = this.sort;
      }
    }
  }

  /**
   * Handle sort change
   */
  onSortChange(sortState: Sort): void {
    if (!sortState.active || sortState.direction === '') {
      this.dataSource.data = [...this.data];
      return;
    }

    const sorted = [...this.data].sort((a, b) => {
      const isAsc = sortState.direction === 'asc';
      switch (sortState.active) {
        case 'tool_name':
          return this.compare(
            a.tool_name || a.tool_id,
            b.tool_name || b.tool_id,
            isAsc
          );
        case 'total_calls':
          return this.compare(a.total_calls, b.total_calls, isAsc);
        case 'successful_calls':
          return this.compare(a.successful_calls, b.successful_calls, isAsc);
        case 'success_rate':
          return this.compare(a.success_rate, b.success_rate, isAsc);
        case 'avg_duration_ms':
          return this.compare(a.avg_duration_ms, b.avg_duration_ms, isAsc);
        case 'total_cost':
          return this.compare(a.total_cost, b.total_cost, isAsc);
        default:
          return 0;
      }
    });

    this.dataSource.data = sorted;
  }

  private compare(
    a: string | number,
    b: string | number,
    isAsc: boolean
  ): number {
    return (a < b ? -1 : a > b ? 1 : 0) * (isAsc ? 1 : -1);
  }

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
   * Get success rate CSS class
   */
  getSuccessClass(rate: number): string {
    return getSuccessRateClass(rate);
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
   * Get tool display name
   */
  getToolName(item: ToolUsageSummary): string {
    return item.tool_name || item.tool_id;
  }

  /**
   * Get truncated tool ID for tooltip
   */
  getToolIdShort(id: string): string {
    return id.length > 8 ? id.substring(0, 8) + '...' : id;
  }
}
