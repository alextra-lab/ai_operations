/**
 * QueryResultsPanelComponent
 *
 * Reusable component for displaying query results in conversation style.
 *
 * Features:
 * - User/assistant message bubbles
 * - Streaming response support
 * - Source citations with similarity scores
 * - Inline execution metrics
 * - Auto-scroll during streaming
 *
 * Usage:
 * ```html
 * <app-query-results-panel
 *   [messages]="messages"
 *   [sources]="sources"
 *   [metrics]="metrics"
 *   [isStreaming]="isStreaming"
 *   [streamingContent]="streamingContent"
 *   (sourceClicked)="onSourceClick($event)">
 * </app-query-results-panel>
 * ```
 *
 * Related: P4-TOOLS-01, ADR-045
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';

// Angular Material imports
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

// RxJS imports
import { debounceTime, fromEvent, Subject, takeUntil } from 'rxjs';

// Internal imports
import {
  ExecutionMetrics,
  Message,
  MessageAction,
  SourceMetadata,
} from '../../api/models/query-config.models';
import { AutoScrollService } from '../../services/auto-scroll.service';
import { LLMContentRendererComponent } from '../llm-content-renderer/llm-content-renderer.component';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-query-results-panel',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    LLMContentRendererComponent,
  ],
  templateUrl: './query-results-panel.component.html',
  styleUrls: ['./query-results-panel.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QueryResultsPanelComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @ViewChild('resultsContainer')
  resultsContainer!: ElementRef<HTMLElement>;

  // ========================================================================
  // Inputs
  // ========================================================================

  @Input() messages: Message[] = [];
  @Input() sources: SourceMetadata[] = [];
  @Input() metrics: ExecutionMetrics | null = null;
  @Input() isStreaming = false;
  @Input() streamingContent = '';
  @Input() autoScrollEnabled = true;

  // ========================================================================
  // Outputs
  // ========================================================================

  @Output() sourceClicked = new EventEmitter<SourceMetadata>();
  @Output() messageAction = new EventEmitter<MessageAction>();

  // ========================================================================
  // Internal State
  // ========================================================================

  private isUserScrolling = false;
  private destroy$ = new Subject<void>();

  constructor(
    private autoScrollService: AutoScrollService,
    private cdr: ChangeDetectorRef
  ) {}

  // ========================================================================
  // Lifecycle Hooks
  // ========================================================================

  ngAfterViewInit(): void {
    this.setupScrollDetection();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isStreaming'] && this.isStreaming) {
      this.onStreamingStart();
    }
    if (changes['streamingContent'] && this.isStreaming) {
      this.onStreamingChunk();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Scroll Management
  // ========================================================================

  private setupScrollDetection(): void {
    if (!this.resultsContainer) {
      return;
    }

    fromEvent(this.resultsContainer.nativeElement, 'scroll')
      .pipe(debounceTime(100), takeUntil(this.destroy$))
      .subscribe(() => {
        const element = this.resultsContainer.nativeElement;
        const isAtBottom = this.autoScrollService.isScrolledToBottom(element);
        this.isUserScrolling = !isAtBottom;
      });
  }

  private onStreamingStart(): void {
    this.isUserScrolling = false;
    this.scrollToBottom();
  }

  private onStreamingChunk(): void {
    if (this.autoScrollEnabled && !this.isUserScrolling) {
      this.scrollToBottom();
    }
  }

  private scrollToBottom(): void {
    if (!this.resultsContainer) {
      return;
    }

    this.autoScrollService.scrollToBottom(this.resultsContainer.nativeElement, {
      behavior: 'smooth',
    });
  }

  // ========================================================================
  // Template Helpers
  // ========================================================================

  getRoleIcon(role: string): string {
    switch (role) {
      case 'user':
        return 'user';
      case 'assistant':
        return 'bot';
      case 'system':
        return 'settings';
      default:
        return 'circle-help';
    }
  }

  getRoleName(role: string): string {
    switch (role) {
      case 'user':
        return 'You';
      case 'assistant':
        return 'Assistant';
      case 'system':
        return 'System';
      default:
        return 'Unknown';
    }
  }

  formatTokens(tokens: number): string {
    if (tokens < 1000) {
      return tokens.toString();
    } else if (tokens < 1000000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    } else {
      return `${(tokens / 1000000).toFixed(1)}M`;
    }
  }

  formatDuration(ms: number): string {
    if (ms < 1000) {
      return `${ms}ms`;
    } else if (ms < 60000) {
      return `${(ms / 1000).toFixed(1)}s`;
    } else {
      const minutes = Math.floor(ms / 60000);
      const seconds = Math.floor((ms % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  }

  formatPercentage(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  formatCost(cost: number): string {
    return `$${cost.toFixed(4)}`;
  }

  // ========================================================================
  // Event Handlers
  // ========================================================================

  onSourceClick(source: SourceMetadata): void {
    this.sourceClicked.emit(source);
  }

  trackByMessage(index: number, message: Message): string | number {
    return message.id || index;
  }

  trackBySource(index: number, source: SourceMetadata): string {
    return source.document_id + source.chunk_index;
  }
}
