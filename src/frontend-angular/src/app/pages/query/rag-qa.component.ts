import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject } from 'rxjs';
import { finalize, takeUntil } from 'rxjs/operators';

import {
  ExecutionMetrics,
  isHighEntropyConfig,
  Message,
  QueryConfig,
  SamplingPreset,
  SourceMetadata,
} from '../../api/models/query-config.models';
import {
  QueryError,
  RAGQAResponse,
  RAGQuestionRequest,
} from '../../api/models/query.models';
import { RagService } from '../../api/services/rag.service';
import { ParameterConfigPanelComponent } from '../../components/parameter-config-panel/parameter-config-panel.component';
import { QueryResultsPanelComponent } from '../../components/query-results-panel/query-results-panel.component';
import { EnterToExecuteDirective } from '../../directives/enter-to-execute.directive';
import { AutoScrollService } from '../../services/auto-scroll.service';

@Component({
  selector: 'app-rag-qa',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    ParameterConfigPanelComponent,
    QueryResultsPanelComponent,
    EnterToExecuteDirective,
  ],
  template: `
    <!-- Layer 2: Page Container - Tailwind utilities -->
    <div
      class="flex flex-col overflow-hidden
                    -my-4 -mr-4 -mb-4
                    md:-my-6 md:-mr-8 md:-mb-6
                    h-full
                    page-container"
    >
      <!-- Layer 2: Page Header + Controls -->
      <div
        class="flex-none z-[100] bg-white border-b border-gray-200
                        page-header-section"
      >
        <!-- Page Title -->
        <div class="px-4 pt-4 pb-3 md:px-6 md:pt-6 md:pb-4">
          <h1
            class="m-0 text-[28px] font-medium
                               flex items-center gap-3"
          >
            <mat-icon class="text-blue-600">quiz</mat-icon>
            RAG Q&A System
          </h1>
          <p class="m-0 mt-2 text-gray-600 text-sm">
            Test full RAG pipeline with LLM generation and sampling controls
          </p>
        </div>

        <!-- Question Input + Config Panel -->
        <div class="px-4 pb-4 md:px-6 md:pb-4">
          <div class="bg-gray-100 rounded-lg shadow-md p-5">
            <!-- Question Input -->
            <div class="question-input-section">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Ask a question</mat-label>
                <textarea
                  #questionInput
                  matInput
                  [(ngModel)]="currentQuery"
                  [appEnterToExecute]="enterToExecute"
                  (enterPressed)="askQuestion()"
                  placeholder="e.g., 'What are the main security threats in our policies?'"
                  rows="3"
                  maxlength="1000"
                  [disabled]="isAsking"
                >
                </textarea>
                <mat-icon matSuffix>quiz</mat-icon>
                <mat-hint>Ask specific questions about your documents</mat-hint>
                <mat-hint align="end"
                  >{{ currentQuery.length || 0 }}/1000</mat-hint
                >
              </mat-form-field>
            </div>

            <!-- Parameter Configuration Panel -->
            <app-parameter-config-panel
              [initialConfig]="currentConfig"
              [mode]="'rag'"
              [showAdvanced]="showAdvancedParams"
              (configChanged)="onConfigChanged($event)"
              (execute)="askQuestion()"
            >
            </app-parameter-config-panel>

            <!-- High-Entropy Warning -->
            <mat-card
              *ngIf="showHighEntropyWarning"
              class="mt-4 border-l-4 border-orange-500 warning-card"
              role="alert"
            >
              <mat-card-content>
                <div class="flex items-center gap-3 warning-content">
                  <mat-icon color="warn" aria-hidden="true">warning</mat-icon>
                  <span class="text-sm"
                    >High-entropy configuration detected (temp > 0.9 AND top_p >
                    0.97). This may cause inconsistent outputs.</span
                  >
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </div>
      </div>

      <!-- Layer 3: Results (SCROLLS) -->
      <div
        class="flex-1 overflow-y-auto overflow-x-hidden
                        px-4 py-4 md:px-6 md:py-6
                        min-h-0 bg-gray-50
                        content-area"
      >
        <app-query-results-panel
          [messages]="messages"
          [sources]="currentSources"
          [metrics]="currentMetrics"
          [isStreaming]="isAsking"
          [streamingContent]="streamingAnswer"
          [autoScrollEnabled]="true"
        >
        </app-query-results-panel>

        <!-- Empty State -->
        <div
          *ngIf="messages.length === 0 && !isAsking"
          class="flex flex-col items-center justify-center
                            text-center p-12 text-gray-500
                            empty-state"
        >
          <mat-icon class="!text-[80px] !w-20 !h-20 mb-4 text-gray-400"
            >quiz</mat-icon
          >
          <h3 class="text-xl font-medium mb-2 text-gray-700">
            Ready to Answer Questions
          </h3>
          <p class="mb-2">
            Enter a question above and press "Ask Question" or hit Enter to get
            started.
          </p>
          <p class="text-sm italic hint">
            Tip: Use the parameter panel to tune RAG retrieval and LLM
            generation settings.
          </p>
        </div>
      </div>

      <!-- Layer 4: Footer -->
      <div
        class="flex-none px-4 py-3 bg-white border-t border-gray-200
                        md:px-6 md:py-4
                        page-footer"
      >
        <div class="flex flex-wrap gap-3 mb-3 action-buttons">
          <button
            mat-raised-button
            color="primary"
            (click)="askQuestion()"
            [disabled]="!canAsk || isAsking"
            aria-label="Ask question"
          >
            <mat-icon>quiz</mat-icon>
            <span *ngIf="!isAsking">Ask Question</span>
            <span *ngIf="isAsking">Generating Answer...</span>
          </button>

          <button
            mat-button
            (click)="reset()"
            [disabled]="isAsking"
            aria-label="Reset conversation"
          >
            <mat-icon>refresh</mat-icon>
            Reset
          </button>

          <button
            mat-button
            (click)="exportConfiguration()"
            [disabled]="isAsking"
            aria-label="Export configuration"
          >
            <mat-icon>download</mat-icon>
            Export Config
          </button>
        </div>

        <div class="flex flex-wrap gap-4 items-center text-sm status-info">
          <mat-checkbox
            [(ngModel)]="enterToExecute"
            (change)="saveEnterToExecute()"
            aria-label="Enable Enter to execute"
          >
            Enter to Execute
          </mat-checkbox>

          <span
            *ngIf="lastExecutionTime"
            class="flex items-center gap-1 px-2 py-1 bg-blue-50
                                 rounded text-blue-700 metric-badge"
          >
            <mat-icon class="!text-base !w-4 !h-4" aria-hidden="true"
              >schedule</mat-icon
            >
            {{ lastExecutionTime }}ms
          </span>

          <span
            *ngIf="tokensUsed"
            class="flex items-center gap-1 px-2 py-1 bg-purple-50
                                 rounded text-purple-700 metric-badge"
          >
            <mat-icon class="!text-base !w-4 !h-4" aria-hidden="true"
              >token</mat-icon
            >
            {{ tokensUsed }} tokens
          </span>

          <span
            *ngIf="currentCost"
            class="flex items-center gap-1 px-2 py-1 bg-green-50
                                 rounded text-green-700 metric-badge"
          >
            <mat-icon class="!text-base !w-4 !h-4" aria-hidden="true"
              >attach_money</mat-icon
            >
            {{ currentCost | currency: 'USD' : 'symbol' : '1.4-4' }}
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      // ====================================================================
      // ADR-012 Compliant Styles - RAG Q&A
      // Tailwind: layout, spacing, colors, typography, responsive
      // SCSS: transitions, Material overrides, complex states only
      // ====================================================================

      // Smooth transitions for shadows (can't use Tailwind)
      .page-header-section {
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: box-shadow 0.2s ease-in-out;
      }

      .page-footer {
        box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
        transition: box-shadow 0.2s ease-in-out;
      }

      // Material icon sizing in titles
      h1 mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
      }

      // Ensure h1 font-size and font-weight (matches Semantic Search)
      h1.m-0 {
        font-size: 28px;
        font-weight: 500;
      }

      // Form field sizing (Material component override)
      .full-width {
        width: 100%;
      }

      // Ensure footer is always visible
      .page-footer {
        position: relative;
        z-index: 10;
      }

      // Page container should fill available height
      // CRITICAL: overflow: hidden prevents parent from scrolling
      .page-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden; // CRITICAL: Prevents parent scrolling
        min-height: 0;
      }

      // Layer 2: Page Header (NEVER SCROLLS)
      .page-header-section {
        flex: 0 0 auto; // Don't grow or shrink
      }

      // Layer 3: Content Area (SCROLLS)
      // This is the scrollable area for conversation results
      // CRITICAL: min-height: 0 allows flex child to shrink below content size
      .content-area {
        flex: 1 1 0% !important; // Take remaining space, allow shrinking
        overflow-y: auto !important; // Enable vertical scrolling
        overflow-x: hidden !important; // Prevent horizontal scroll
        min-height: 0 !important; // CRITICAL: Enables flex child scrolling
        -webkit-overflow-scrolling: touch; // Smooth scrolling on iOS
        position: relative;
        // Ensure proper height constraint
        max-height: 100%;
      }

      // Layer 4: Footer (NEVER SCROLLS)
      .page-footer {
        flex: 0 0 auto; // Don't grow or shrink
      }

      // Warning card background (complex pattern)
      .warning-card {
        background: #fff3e0;
      }

      // ====================================================================
      // Responsive Overrides (complex Material component sizing)
      // ====================================================================

      @media (max-width: 768px) {
        h1 mat-icon {
          font-size: 28px;
          width: 28px;
          height: 28px;
        }

      }

      // ====================================================================
      // Accessibility: Respect reduced motion preference
      // ====================================================================

      @media (prefers-reduced-motion: reduce) {
        .page-header-section,
        .page-footer {
          transition: none;
        }
      }
    `,
  ],
})
export class RagQaComponent implements OnInit, OnDestroy {
  // ========================================================================
  // Component Properties
  // ========================================================================

  // Query and configuration state
  currentQuery = '';
  currentConfig: QueryConfig | null = null;
  showAdvancedParams = true;
  enterToExecute = false;

  // Execution state
  isAsking = false;
  streamingAnswer = '';

  // Results
  messages: Message[] = [];
  currentSources: SourceMetadata[] = [];
  currentMetrics: ExecutionMetrics | null = null;

  // UI state
  showHighEntropyWarning = false;

  // Computed properties for footer display
  lastExecutionTime?: number;
  tokensUsed?: number;
  currentCost?: number;

  private destroy$ = new Subject<void>();
  private readonly STORAGE_KEY_ENTER = 'ragQaEnterToExecute';

  // ========================================================================
  // Constructor
  // ========================================================================

  constructor(
    private ragService: RagService,
    private autoScrollService: AutoScrollService,
    private snackBar: MatSnackBar
  ) { }

  // ========================================================================
  // Lifecycle Hooks
  // ========================================================================

  ngOnInit(): void {
    this.loadEnterToExecute();
    this.initializeDefaultConfig();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Computed Properties
  // ========================================================================

  get canAsk(): boolean {
    return this.currentQuery.trim().length > 0 && !this.isAsking;
  }

  // ========================================================================
  // Configuration Methods
  // ========================================================================

  private initializeDefaultConfig(): void {
    this.currentConfig = {
      llm_model: 'auto',
      sampling: {
        preset: SamplingPreset.BALANCED,
        temperature: 0.65,
        top_p: 0.95,
        max_tokens: 2048,
      },
      rag: {
        enabled: true,
        vector_collections: [],
        top_k: 5,
        similarity_threshold: 0.7,
      },
      query_type: 'rag',
    };
  }

  onConfigChanged(config: QueryConfig): void {
    this.currentConfig = config;
    this.checkHighEntropyConfig(config);
  }

  private checkHighEntropyConfig(config: QueryConfig): void {
    this.showHighEntropyWarning = isHighEntropyConfig(config.sampling);
  }

  // ========================================================================
  // Execution Methods
  // ========================================================================

  askQuestion(): void {
    if (!this.canAsk) {
      return;
    }

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: this.currentQuery,
      created_at: new Date().toISOString(),
    };
    this.messages = [...this.messages, userMessage];

    this.isAsking = true;
    this.streamingAnswer = '';
    this.currentSources = [];

    const startTime = Date.now();

    const request: RAGQuestionRequest = {
      question: this.currentQuery,
      include_sources: true,
      max_context_length: 4000,
      temperature: this.currentConfig?.sampling.temperature || 0.7,
      model_preference: this.currentConfig?.llm_model || 'auto',
    };

    this.ragService
      .askQuestion(request)
      .pipe(
        finalize(() => {
          this.isAsking = false;
          this.lastExecutionTime = Date.now() - startTime;
        }),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (response) => {
          this.handleSuccessfulResponse(response);
        },
        error: (error: QueryError) => {
          this.handleErrorResponse(error);
        },
      });
  }

  private handleSuccessfulResponse(response: RAGQAResponse): void {
    // Add assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: response.answer?.answer || 'No answer available',
      created_at: new Date().toISOString(),
      token_count: response.token_usage?.output_tokens,
      metadata: {
        confidence: response.answer?.confidence,
        message_id: response.answer?.message_id,
        model_used: response.model_used,
      },
    };
    this.messages = [...this.messages, assistantMessage];

    // Convert sources to SourceMetadata format
    this.currentSources = (response.answer?.sources || []).map((source) => ({
      document_id: source.document_id || '',
      title: source.title || 'Unknown Source',
      content_snippet: source.content_snippet || '',
      similarity_score: source.relevance_score || 0,
      relevance_score: source.relevance_score || 0,
      metadata: {
        chunk_index: source.chunk_index,
        page_number: source.page_number,
        ...source.metadata,
      },
    }));

    // Set metrics
    this.currentMetrics = {
      timing: {
        total_time_ms: response.processing_time_ms || 0,
      },
      tokens: {
        input_tokens: response.token_usage?.input_tokens || 0,
        output_tokens: response.token_usage?.output_tokens || 0,
        total_tokens: response.token_usage?.total_tokens || 0,
      },
      confidence_score: response.answer?.confidence,
      retrieval: {
        chunks_retrieved: response.context_retrieved?.total_chunks || 0,
        avg_similarity: this.calculateAvgSimilarity(
          response.answer?.sources || []
        ),
        collections_searched: [],
      },
    };

    this.tokensUsed = this.currentMetrics.tokens.total_tokens;

    this.snackBar.open('Answer generated successfully', 'Close', {
      duration: 3000,
    });
  }

  private handleErrorResponse(error: QueryError): void {
    const errorMessage: Message = {
      role: 'assistant',
      content: `Error: ${error.message}`,
      created_at: new Date().toISOString(),
      metadata: {
        error: true,
      },
    };
    this.messages = [...this.messages, errorMessage];

    this.snackBar.open('Failed to generate answer: ' + error.message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }

  reset(): void {
    this.currentQuery = '';
    this.messages = [];
    this.currentSources = [];
    this.currentMetrics = null;
    this.lastExecutionTime = undefined;
    this.tokensUsed = undefined;
    this.currentCost = undefined;
    this.showHighEntropyWarning = false;

    this.snackBar.open('Conversation reset', 'Close', {
      duration: 2000,
    });
  }

  // ========================================================================
  // Configuration Export
  // ========================================================================

  exportConfiguration(): void {
    if (!this.currentConfig) {
      this.snackBar.open('No configuration to export', 'Close', {
        duration: 2000,
      });
      return;
    }

    const exportData = {
      timestamp: new Date().toISOString(),
      query_type: 'rag',
      configuration: this.currentConfig,
      last_query: this.currentQuery || null,
      execution_metrics: this.currentMetrics || null,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `rag-qa-config-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    this.snackBar.open('Configuration exported', 'Close', {
      duration: 2000,
    });
  }

  // ========================================================================
  // Enter-to-Execute Preference
  // ========================================================================

  private loadEnterToExecute(): void {
    const saved = localStorage.getItem(this.STORAGE_KEY_ENTER);
    this.enterToExecute = saved === 'true';
  }

  saveEnterToExecute(): void {
    localStorage.setItem(
      this.STORAGE_KEY_ENTER,
      this.enterToExecute.toString()
    );
  }

  // ========================================================================
  // Helper Methods
  // ========================================================================

  private calculateAvgSimilarity(sources: any[]): number {
    if (!sources || sources.length === 0) return 0;
    const sum = sources.reduce(
      (acc, src) => acc + (src.relevance_score || 0),
      0
    );
    return sum / sources.length;
  }
}
