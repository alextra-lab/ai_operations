import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LucideAngularModule } from 'lucide-angular';
import {
  ChunkingStrategy,
  PreflightReport,
  StrategyBenchmarkResult,
} from '../../api/models/preflight.models';

/**
 * Preflight Report Component
 *
 * Displays preflight analysis results for document chunking strategy selection.
 * Shows structure signals, strategy comparisons, and recommendations.
 *
 * Follows ADR-012 (Hybrid CSS Strategy):
 * - Material for UI primitives (cards, buttons, chips)
 * - Tailwind for layout and spacing
 * - Component SCSS for complex styling
 *
 * Follows WCAG 2.1 AA accessibility guidelines
 */
@Component({
  selector: 'app-preflight-report',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-card class="preflight-report">
      <mat-card-header>
        <mat-card-title class="flex items-center gap-2">
          <lucide-icon aria-hidden="true" name="chart-column"></lucide-icon>
          <span>Preflight Analysis Report</span>
        </mat-card-title>
        <mat-card-subtitle>
          {{ report.document_name }} ({{
            formatBytes(report.document_size_bytes)
          }})
        </mat-card-subtitle>
      </mat-card-header>

      <mat-card-content class="space-y-6">
        <!-- Document Info -->
        <section aria-labelledby="doc-info-heading">
          <h3 id="doc-info-heading" class="text-base font-medium mb-2">
            Document Information
          </h3>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <span class="text-sm text-gray-600">Type:</span>
              <span class="ml-2 font-medium">{{ report.document_type }}</span>
            </div>
            <div>
              <span class="text-sm text-gray-600">Sample Analyzed:</span>
              <span class="ml-2 font-medium"
                >{{ report.sample_size_tokens }} tokens</span
              >
            </div>
            <div>
              <span class="text-sm text-gray-600">Analysis Time:</span>
              <span class="ml-2 font-medium">{{
                formatMs(report.analysis_time_ms)
              }}</span>
            </div>
            <div *ngIf="report.test_suite_id">
              <span class="text-sm text-gray-600">Test Suite:</span>
              <lucide-icon
                class="align-middle text-green-600"
                matTooltip="Retrieval metrics available"
                name="circle-check"
              ></lucide-icon>
            </div>
          </div>
        </section>

        <!-- Structure Signals -->
        <section aria-labelledby="structure-heading">
          <h3 id="structure-heading" class="text-base font-medium mb-3">
            Document Structure
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div class="flex flex-col">
              <span class="text-sm text-gray-600 mb-1">Heading Density</span>
              <mat-progress-bar
                mode="determinate"
                [value]="report.structure_signals.heading_density * 100"
                [attr.aria-label]="
                  'Heading density: ' +
                  (report.structure_signals.heading_density * 100).toFixed(1) +
                  '%'
                "
              >
              </mat-progress-bar>
              <span class="text-xs mt-1"
                >{{
                  (report.structure_signals.heading_density * 100).toFixed(1)
                }}%</span
              >
            </div>
            <div class="flex flex-col">
              <span class="text-sm text-gray-600 mb-1">Table Ratio</span>
              <mat-progress-bar
                mode="determinate"
                [value]="report.structure_signals.table_ratio * 100"
                [attr.aria-label]="
                  'Table ratio: ' +
                  (report.structure_signals.table_ratio * 100).toFixed(1) +
                  '%'
                "
              >
              </mat-progress-bar>
              <span class="text-xs mt-1"
                >{{
                  (report.structure_signals.table_ratio * 100).toFixed(1)
                }}%</span
              >
            </div>
            <div class="flex flex-col">
              <span class="text-sm text-gray-600 mb-1">List Ratio</span>
              <mat-progress-bar
                mode="determinate"
                [value]="report.structure_signals.list_ratio * 100"
                [attr.aria-label]="
                  'List ratio: ' +
                  (report.structure_signals.list_ratio * 100).toFixed(1) +
                  '%'
                "
              >
              </mat-progress-bar>
              <span class="text-xs mt-1"
                >{{
                  (report.structure_signals.list_ratio * 100).toFixed(1)
                }}%</span
              >
            </div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div>
              <span class="text-sm text-gray-600">Avg Paragraph</span>
              <p class="font-medium">
                {{ report.structure_signals.avg_paragraph_length.toFixed(0) }}
                tokens
              </p>
            </div>
            <div>
              <span class="text-sm text-gray-600">Sentences</span>
              <p class="font-medium">
                {{ report.structure_signals.sentence_count }}
              </p>
            </div>
            <div *ngIf="report.structure_signals.has_code_blocks">
              <mat-chip
                selected
                color="primary"
                aria-label="Contains code blocks"
              >
                <mat-icon matChipAvatar>code</mat-icon>
                Code Blocks
              </mat-chip>
            </div>
            <div *ngIf="report.structure_signals.has_equations">
              <mat-chip
                selected
                color="primary"
                aria-label="Contains equations"
              >
                <mat-icon matChipAvatar>functions</mat-icon>
                Equations
              </mat-chip>
            </div>
          </div>
        </section>

        <!-- Recommendation -->
        <section
          aria-labelledby="recommendation-heading"
          class="bg-blue-50 p-4 rounded-lg"
        >
          <h3
            id="recommendation-heading"
            class="text-base font-medium mb-3 flex items-center gap-2"
          >
            <lucide-icon
              class="text-blue-600"
              aria-hidden="true"
              name="thumbs-up"
            ></lucide-icon>
            Recommended Strategy
          </h3>
          <div class="mb-3">
            <mat-chip selected color="accent" class="text-lg px-4 py-2">
              {{ formatStrategyName(report.recommendation.strategy) }}
            </mat-chip>
            <span class="ml-3 text-sm text-gray-600">
              Confidence:
              <strong
                >{{
                  (report.recommendation.confidence * 100).toFixed(0)
                }}%</strong
              >
            </span>
          </div>
          <div class="space-y-1">
            <p class="text-sm font-medium text-gray-700">Reasoning:</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-600">
              <li *ngFor="let reason of report.recommendation.reasoning">
                {{ reason }}
              </li>
            </ul>
          </div>
          <div
            *ngIf="report.recommendation.alternative_strategies.length > 0"
            class="mt-3"
          >
            <p class="text-sm font-medium text-gray-700 mb-1">Alternatives:</p>
            <div class="flex flex-wrap gap-2">
              <mat-chip
                *ngFor="
                  let strategy of report.recommendation.alternative_strategies
                "
                (click)="onStrategyOverride(strategy)"
                [attr.aria-label]="
                  'Alternative strategy: ' + formatStrategyName(strategy)
                "
              >
                {{ formatStrategyName(strategy) }}
              </mat-chip>
            </div>
          </div>
        </section>

        <!-- Strategy Comparison (show top 3) -->
        <section aria-labelledby="comparison-heading">
          <h3 id="comparison-heading" class="text-base font-medium mb-3">
            Strategy Comparison
          </h3>
          <div class="space-y-2">
            <div
              *ngFor="let result of getTopStrategies()"
              class="flex items-center gap-3 p-3 border rounded-lg hover:bg-gray-50 transition-colors"
              [class.border-blue-500]="
                result.strategy === report.recommendation.strategy
              "
            >
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-medium">{{
                    formatStrategyName(result.strategy)
                  }}</span>
                  <mat-chip *ngIf="result.rank" size="small"
                    >Rank #{{ result.rank }}</mat-chip
                  >
                </div>
                <div class="text-sm text-gray-600 mt-1">
                  {{ result.chunk_count }} chunks · Avg
                  {{ result.avg_chunk_size.toFixed(0) }} tokens ·
                  {{ result.processing_time_ms }}ms
                </div>
              </div>
              <div class="text-right">
                <div class="text-lg font-medium">
                  {{ (result.score * 100).toFixed(0) }}%
                </div>
                <div class="text-xs text-gray-600">score</div>
              </div>
            </div>
          </div>
          <button
            *ngIf="report.strategy_results.length > 3"
            mat-button
            color="primary"
            (click)="onViewDetails()"
            class="mt-2"
            aria-label="View detailed strategy comparison"
          >
            View All Strategies
          </button>
        </section>
      </mat-card-content>

      <mat-card-actions class="flex gap-2 justify-end">
        <button
          mat-button
          (click)="onOverride()"
          aria-label="Override recommendation with custom configuration"
        >
          Override
        </button>
        <button
          mat-raised-button
          color="primary"
          (click)="onAccept()"
          aria-label="Accept recommended strategy"
        >
          Accept Recommendation
        </button>
      </mat-card-actions>
    </mat-card>
  `,
  styles: [
    `
      .preflight-report {
        max-width: 800px;
        margin: 0 auto;
      }

      mat-progress-bar {
        height: 8px;
        border-radius: 4px;
      }

      mat-chip {
        cursor: pointer;
      }

      .border-blue-500 {
        border-width: 2px;
      }

      /* Ensure proper focus indicators for accessibility */
      button:focus-visible,
      mat-chip:focus-visible {
        outline: 2px solid var(--mat-primary);
        outline-offset: 2px;
      }
    `,
  ],
})
export class PreflightReportComponent {
  @Input() report!: PreflightReport;
  @Output() accept = new EventEmitter<ChunkingStrategy>();
  @Output() override = new EventEmitter<void>();
  @Output() viewDetails = new EventEmitter<void>();
  @Output() strategyOverride = new EventEmitter<ChunkingStrategy>();

  /**
   * Format bytes to human-readable format
   */
  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
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
   * Get top 3 strategies by score
   */
  getTopStrategies(): StrategyBenchmarkResult[] {
    return [...this.report.strategy_results]
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);
  }

  /**
   * Handle accept recommendation
   */
  onAccept(): void {
    this.accept.emit(this.report.recommendation.strategy);
  }

  /**
   * Handle override request
   */
  onOverride(): void {
    this.override.emit();
  }

  /**
   * Handle view details request
   */
  onViewDetails(): void {
    this.viewDetails.emit();
  }

  /**
   * Handle strategy override selection
   */
  onStrategyOverride(strategy: ChunkingStrategy): void {
    this.strategyOverride.emit(strategy);
  }
}
