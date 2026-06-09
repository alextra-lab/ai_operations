import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  ChunkingStrategy,
  StrategyBenchmarkResult,
} from '../../api/models/preflight.models';
import { LucideAngularModule } from 'lucide-angular';

/**
 * Strategy Comparison Component
 *
 * Displays detailed side-by-side comparison of chunking strategies with
 * sortable columns and retrieval metrics visualization.
 *
 * Follows ADR-012 (Hybrid CSS Strategy) and WCAG 2.1 AA guidelines.
 */
@Component({
  selector: 'app-strategy-comparison',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatTooltipModule,
    MatChipsModule,
    MatSortModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="strategy-comparison">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-medium">Strategy Comparison</h2>
        <button
          mat-icon-button
          (click)="onClose()"
          aria-label="Close comparison"
        >
          <lucide-icon name="x"></lucide-icon>
        </button>
      </div>

      <div class="overflow-x-auto">
        <table
          mat-table
          [dataSource]="sortedResults"
          matSort
          (matSortChange)="onSort($event)"
          class="w-full"
          aria-label="Chunking strategy comparison table"
        >
          <!-- Rank Column -->
          <ng-container matColumnDef="rank">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Rank</th>
            <td mat-cell *matCellDef="let result">
              <mat-chip
                *ngIf="result.rank"
                [color]="result.rank === 1 ? 'primary' : 'basic'"
              >
                #{{ result.rank }}
              </mat-chip>
            </td>
          </ng-container>

          <!-- Strategy Column -->
          <ng-container matColumnDef="strategy">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Strategy</th>
            <td mat-cell *matCellDef="let result">
              <strong>{{ formatStrategyName(result.strategy) }}</strong>
            </td>
          </ng-container>

          <!-- Score Column -->
          <ng-container matColumnDef="score">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>
              Score
              <lucide-icon
                class="text-sm ml-1 align-middle"
                matTooltip="Overall quality score (0-100%)" name="info"></lucide-icon>
            </th>
            <td mat-cell *matCellDef="let result">
              <span [class]="getScoreClass(result.score)">
                {{ (result.score * 100).toFixed(1) }}%
              </span>
            </td>
          </ng-container>

          <!-- Chunk Count Column -->
          <ng-container matColumnDef="chunk_count">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Chunks</th>
            <td mat-cell *matCellDef="let result">{{ result.chunk_count }}</td>
          </ng-container>

          <!-- Avg Size Column -->
          <ng-container matColumnDef="avg_chunk_size">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Avg Size</th>
            <td mat-cell *matCellDef="let result">
              {{ result.avg_chunk_size.toFixed(0) }} tokens
            </td>
          </ng-container>

          <!-- Std Dev Column -->
          <ng-container matColumnDef="std_chunk_size">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>
              Std Dev
              <lucide-icon
                class="text-sm ml-1 align-middle"
                matTooltip="Lower is more consistent" name="info"></lucide-icon>
            </th>
            <td mat-cell *matCellDef="let result">
              {{ result.std_chunk_size.toFixed(0) }}
            </td>
          </ng-container>

          <!-- Processing Time Column -->
          <ng-container matColumnDef="processing_time_ms">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Time</th>
            <td mat-cell *matCellDef="let result">
              {{ formatMs(result.processing_time_ms) }}
            </td>
          </ng-container>

          <!-- Hit@K Column (optional) -->
          <ng-container matColumnDef="hit_at_k">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>
              Hit&#64;K
              <lucide-icon
                class="text-sm ml-1 align-middle"
                matTooltip="Retrieval accuracy metric" name="info"></lucide-icon>
            </th>
            <td mat-cell *matCellDef="let result">
              <span *ngIf="result.hit_at_k !== undefined">
                {{ (result.hit_at_k * 100).toFixed(1) }}%
              </span>
              <span *ngIf="result.hit_at_k === undefined" class="text-gray-400"
                >N/A</span
              >
            </td>
          </ng-container>

          <!-- MRR Column (optional) -->
          <ng-container matColumnDef="mrr">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>
              MRR
              <lucide-icon
                class="text-sm ml-1 align-middle"
                matTooltip="Mean Reciprocal Rank" name="info"></lucide-icon>
            </th>
            <td mat-cell *matCellDef="let result">
              <span *ngIf="result.mrr !== undefined">
                {{ result.mrr.toFixed(3) }}
              </span>
              <span *ngIf="result.mrr === undefined" class="text-gray-400"
                >N/A</span
              >
            </td>
          </ng-container>

          <!-- nDCG Column (optional) -->
          <ng-container matColumnDef="ndcg">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>
              nDCG
              <lucide-icon
                class="text-sm ml-1 align-middle"
                matTooltip="Normalized Discounted Cumulative Gain" name="info"></lucide-icon>
            </th>
            <td mat-cell *matCellDef="let result">
              <span *ngIf="result.ndcg !== undefined">
                {{ result.ndcg.toFixed(3) }}
              </span>
              <span *ngIf="result.ndcg === undefined" class="text-gray-400"
                >N/A</span
              >
            </td>
          </ng-container>

          <!-- Actions Column -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let result">
              <button
                mat-icon-button
                (click)="onSelect(result.strategy)"
                [attr.aria-label]="
                  'Select ' + formatStrategyName(result.strategy) + ' strategy'
                "
                matTooltip="Select this strategy"
              >
                <lucide-icon name="circle-check"></lucide-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr
            mat-row
            *matRowDef="let row; columns: displayedColumns"
            [class.highlighted-row]="isRecommended(row.strategy)"
          ></tr>
        </table>
      </div>

      <div class="mt-4 text-sm text-gray-600" *ngIf="hasRetrievalMetrics">
        <lucide-icon class="text-sm align-middle mr-1" name="info"></lucide-icon>
        Retrieval metrics are available for this analysis
      </div>
    </div>
  `,
  styles: [
    `
      .strategy-comparison {
        padding: 16px;
      }

      table {
        width: 100%;
      }

      .highlighted-row {
        background-color: rgba(33, 150, 243, 0.1);
        font-weight: 500;
      }

      .mat-column-rank {
        max-width: 80px;
      }

      .mat-column-actions {
        max-width: 80px;
        text-align: center;
      }

      th.mat-header-cell {
        font-weight: 600;
        color: rgba(0, 0, 0, 0.87);
      }

      /* Ensure proper focus indicators */
      button:focus-visible {
        outline: 2px solid var(--mat-primary);
        outline-offset: 2px;
      }
    `,
  ],
})
export class StrategyComparisonComponent implements OnInit, OnChanges {
  @Input() results: StrategyBenchmarkResult[] = [];
  @Input() recommendedStrategy?: ChunkingStrategy;
  @Output() select = new EventEmitter<ChunkingStrategy>();
  @Output() close = new EventEmitter<void>();

  sortedResults: StrategyBenchmarkResult[] = [];
  displayedColumns: string[] = [];
  hasRetrievalMetrics = false;

  ngOnInit(): void {
    this.sortedResults = [...this.results].sort(
      (a, b) => (b.rank || 999) - (a.rank || 999)
    );
    this.updateDisplayedColumns();
  }

  ngOnChanges(): void {
    this.sortedResults = [...this.results];
    this.updateDisplayedColumns();
  }

  private updateDisplayedColumns(): void {
    // Base columns
    this.displayedColumns = [
      'rank',
      'strategy',
      'score',
      'chunk_count',
      'avg_chunk_size',
      'std_chunk_size',
      'processing_time_ms',
    ];

    // Add retrieval metrics if available
    if (this.results.some((r) => r.hit_at_k !== undefined)) {
      this.hasRetrievalMetrics = true;
      this.displayedColumns.push('hit_at_k', 'mrr', 'ndcg');
    }

    // Actions column
    this.displayedColumns.push('actions');
  }

  /**
   * Format strategy enum to human-readable name
   */
  formatStrategyName(strategy: ChunkingStrategy): string {
    const names: Record<ChunkingStrategy, string> = {
      [ChunkingStrategy.FIXED_TOKEN]: 'Fixed Token',
      [ChunkingStrategy.SLIDING_TOKEN]: 'Sliding Token',
      [ChunkingStrategy.HEADING_AWARE]: 'Heading Aware',
      [ChunkingStrategy.SENTENCE_PARAGRAPH]: 'Sentence/Paragraph',
      [ChunkingStrategy.TABLE_AWARE]: 'Table Aware',
      [ChunkingStrategy.SEMANTIC_ADAPTIVE]: 'Semantic Adaptive',
      [ChunkingStrategy.PAGE_BLOCK]: 'Page Block',
      [ChunkingStrategy.RECURSIVE]: 'Recursive',
    };
    return names[strategy] || strategy;
  }

  /**
   * Format milliseconds to readable format
   */
  formatMs(ms: number): string {
    if (ms < 1000) {
      return `${ms}ms`;
    }
    return `${(ms / 1000).toFixed(1)}s`;
  }

  /**
   * Get CSS class for score visualization
   */
  getScoreClass(score: number): string {
    if (score >= 0.8) return 'text-green-600 font-semibold';
    if (score >= 0.6) return 'text-blue-600 font-medium';
    if (score >= 0.4) return 'text-orange-600';
    return 'text-red-600';
  }

  /**
   * Check if strategy is recommended
   */
  isRecommended(strategy: ChunkingStrategy): boolean {
    return strategy === this.recommendedStrategy;
  }

  /**
   * Handle sort change
   */
  onSort(sort: Sort): void {
    const data = [...this.results];

    if (!sort.active || sort.direction === '') {
      this.sortedResults = data;
      return;
    }

    this.sortedResults = data.sort((a, b) => {
      const isAsc = sort.direction === 'asc';
      const aVal = (a as any)[sort.active];
      const bVal = (b as any)[sort.active];

      if (aVal === undefined) return 1;
      if (bVal === undefined) return -1;

      return (aVal < bVal ? -1 : 1) * (isAsc ? 1 : -1);
    });
  }

  /**
   * Handle strategy selection
   */
  onSelect(strategy: ChunkingStrategy): void {
    this.select.emit(strategy);
  }

  /**
   * Handle close
   */
  onClose(): void {
    this.close.emit();
  }
}
