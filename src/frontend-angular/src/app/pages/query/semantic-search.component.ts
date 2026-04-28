import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { BehaviorSubject, Observable, of, Subject } from 'rxjs';
import {
  debounceTime,
  distinctUntilChanged,
  finalize,
  switchMap,
  takeUntil,
} from 'rxjs/operators';

import {
  ExecutionMetrics,
  getDefaultQueryConfig,
  Message,
  QueryConfig,
} from '../../api/models/query-config.models';
import {
  QueryError,
  QueryType,
  SearchResult,
  SearchSort,
  SemanticSearchRequest,
  SemanticSearchResponse,
  SortOrder,
} from '../../api/models/query.models';
import {
  LifecycleState,
  UseCaseResponse,
} from '../../api/models/use-case-management.models';
import { DocumentService } from '../../api/services/document.service';
import { QueryService } from '../../api/services/query.service';
import { UseCaseManagementService } from '../../api/services/use-case-management.service';
import { ChunkDetailsDialogComponent } from '../../components/chunk-details-dialog/chunk-details-dialog.component';
import { DocumentViewerDialogComponent } from '../../components/document-viewer-dialog/document-viewer-dialog.component';
import { ParameterConfigPanelComponent } from '../../components/parameter-config-panel/parameter-config-panel.component';
import { QueryResultsPanelComponent } from '../../components/query-results-panel/query-results-panel.component';
import { AuthService } from '../../core/auth/auth.service';
import { SecureStorageService } from '../../core/services/secure-storage.service';
import { EnterToExecuteDirective } from '../../directives/enter-to-execute.directive';

@Component({
  selector: 'app-semantic-search',
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
    MatAutocompleteModule,
    MatExpansionModule,
    MatDialogModule,
    MatSnackBarModule,
    QueryResultsPanelComponent,
    ParameterConfigPanelComponent,
    EnterToExecuteDirective,
  ],
  template: `
    <!-- Layer 2: Page Container - Tailwind utilities -->
    <div
      class="flex flex-col overflow-hidden
                    -my-4 -mr-4 -mb-4
                    md:-my-6 md:-mr-8 md:-mb-6
                    h-[calc(100vh-150px)]
                    md:h-[calc(100vh-200px)]
                    page-container"
    >
      <!-- Layer 2: Configuration Header -->
      <div
        class="flex-none z-[100] bg-white border-b border-gray-200
                        page-header-section"
      >
        <!-- Page Title -->
        <div class="px-4 pt-4 pb-3 md:px-6 md:pt-6 md:pb-4">
          <h1
            class="m-0 text-[28px] md:text-[28px] font-medium
                               flex items-center gap-3"
          >
            <mat-icon class="text-blue-600">search</mat-icon>
            Semantic Search
          </h1>
          <p class="m-0 mt-2 text-gray-600 text-sm">
            Test vector retrieval and chunking strategies
          </p>
        </div>

        <!-- Query input + config panel -->
        <div class="px-4 pb-4 md:px-6 md:pb-4">
          <div class="bg-gray-100 rounded-lg shadow-md p-5">
            <mat-form-field appearance="outline" class="search-input-field">
              <mat-label>Enter your search query</mat-label>
              <textarea
                matInput
                [appEnterToExecute]="true"
                [disabled]="isSearching"
                (executeTriggered)="onSearch()"
                [(ngModel)]="currentQuery"
                placeholder="e.g., 'security vulnerabilities in network protocols'"
              >
              </textarea>
              <mat-icon matSuffix>search</mat-icon>
              <mat-hint
                >Press Enter to search, Shift+Enter for newline</mat-hint
              >
            </mat-form-field>

            <app-parameter-config-panel
              mode="semantic"
              [showAdvanced]="true"
              [initialConfig]="currentConfig"
              (configChanged)="onConfigChanged($event)"
              (execute)="onSearch()"
            >
            </app-parameter-config-panel>
          </div>
        </div>
      </div>

      <!-- Layer 3: Results -->
      <div
        class="flex-1 overflow-y-auto overflow-x-hidden
                        px-4 py-4 md:px-6 md:py-6
                        min-h-0 bg-gray-50
                        content-area"
      >
        <app-query-results-panel
          [messages]="messages"
          [sources]="[]"
          [metrics]="metrics"
          [isStreaming]="isSearching"
          [autoScrollEnabled]="true"
        >
        </app-query-results-panel>

        <!-- Error Display -->
        <mat-card *ngIf="errorMessage" class="error-card">
          <mat-card-content>
            <div class="error-content">
              <mat-icon color="warn">error</mat-icon>
              <h3>Search Error</h3>
              <p>{{ errorMessage }}</p>
              <button mat-button (click)="clearError()">Dismiss</button>
            </div>
          </mat-card-content>
        </mat-card>
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
            (click)="onSearch()"
            [disabled]="!canSearch || isSearching"
          >
            <mat-icon>search</mat-icon>
            {{ isSearching ? 'Searching...' : 'Search' }}
          </button>
          <button mat-button (click)="reset()">
            <mat-icon>refresh</mat-icon>
            Reset
          </button>
          <button mat-button (click)="exportConfiguration()">
            <mat-icon>download</mat-icon>
            Export Config
          </button>
        </div>

        <div class="flex gap-4 mb-3 text-gray-600 text-sm status-info">
          <span *ngIf="lastSearchTimeMs" class="flex items-center gap-1">
            <mat-icon class="!text-base !w-4 !h-4">schedule</mat-icon>
            {{ lastSearchTimeMs }}ms
          </span>
          <span *ngIf="resultCount !== null" class="flex items-center gap-1">
            <mat-icon class="!text-base !w-4 !h-4">description</mat-icon>
            {{ resultCount }} results
          </span>
        </div>

        <div class="flex gap-3 items-start md:items-center apply-to-uc">
          <mat-form-field appearance="outline" class="flex-1 max-w-xs">
            <mat-label>Apply to Use Case</mat-label>
            <mat-select [(value)]="selectedUseCaseId">
              <mat-option *ngFor="let uc of editableUseCases" [value]="uc.id">
                {{ uc.name }} ({{ uc.lifecycle_state }})
              </mat-option>
            </mat-select>
          </mat-form-field>
          <button
            mat-stroked-button
            (click)="applyToUseCase()"
            [disabled]="!selectedUseCaseId"
            class="flex-none"
          >
            <mat-icon>playlist_add</mat-icon>
            Apply
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      // ====================================================================
      // ADR-012 Compliant Styles - Semantic Search
      // Tailwind: layout, spacing, colors, typography, responsive
      // SCSS: transitions, Material overrides, complex states only
      // ====================================================================

      // Smooth transitions for shadows (can't use Tailwind)
      .page-header-section {
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: box-shadow 0.2s ease-in-out;
      }

      .page-footer {
        box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
        transition: box-shadow 0.2s ease-in-out;
      }

      // Material icon sizing in titles
      h1 mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
      }

      // Ensure h1 font-weight is 500 and font-size is 28px
      h1.m-0 {
        font-weight: 500;
        font-size: 28px;
      }

      // Form field sizing (Material component override)
      .search-input-field {
        width: 100%;
      }

      // Error card styling (complex border-left pattern)
      .error-card {
        margin-top: 24px;
        border-left: 4px solid #f44336;
      }

      .error-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        text-align: center;

        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
        }
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
export class SemanticSearchComponent implements OnInit, OnDestroy {
  // Legacy form retained for compatibility where needed
  searchForm: FormGroup;
  searchResults$ = new BehaviorSubject<SemanticSearchResponse | null>(null);
  searchSuggestions$: Observable<string[]> = of([]);

  // New state for shared components
  currentQuery = '';
  currentConfig: QueryConfig = {
    ...getDefaultQueryConfig(),
    query_type: 'semantic',
  };
  messages: Message[] = [];
  metrics: ExecutionMetrics | null = null;

  isSearching = false;
  errorMessage = '';
  currentPage = 1;

  // Footer/status
  lastSearchTimeMs: number | null = null;
  resultCount: number | null = null;

  // Apply-to-UC state
  editableUseCases: UseCaseResponse[] = [];
  selectedUseCaseId: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private queryService: QueryService,
    private documentService: DocumentService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private storage: SecureStorageService,
    private authService: AuthService,
    private useCaseService: UseCaseManagementService
  ) {
    this.searchForm = this.createSearchForm();
  }

  ngOnInit(): void {
    this.setupFormSubscriptions();
    this.loadDefaultFilters();
    this.loadEditableUseCases();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createSearchForm(): FormGroup {
    return this.fb.group({
      query_text: ['', [Validators.required, Validators.minLength(2)]],
      search_type: ['SEMANTIC_SEARCH'],
      limit: [25],
      sort_field: ['relevance'],
      sort_order: ['RELEVANCE'],
      include_snippets: [true],
      highlight_matches: [true],
    });
  }

  private setupFormSubscriptions(): void {
    // Search suggestions based on query text
    this.searchForm
      .get('query_text')
      ?.valueChanges.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((query) => {
          if (query && query.length >= 2) {
            return this.queryService.searchSuggestions(query);
          }
          return of([]);
        }),
        takeUntil(this.destroy$)
      )
      .subscribe((suggestions) => {
        this.searchSuggestions$ = of(suggestions);
      });
  }

  private loadDefaultFilters(): void {
    this.queryService
      .getQueryConfiguration()
      .pipe(takeUntil(this.destroy$))
      .subscribe((config) => {
        if (config) {
          this.searchForm.patchValue({
            search_type: config.default_search_type,
            limit: config.default_limit,
          });
        }
      });
  }

  private loadEditableUseCases(): void {
    this.useCaseService
      .listUseCases({ lifecycle_state: LifecycleState.DRAFT })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (resp) => {
          this.editableUseCases = (resp?.use_cases || []).filter(
            (uc) => uc.lifecycle_state === LifecycleState.DRAFT
          );
        },
        error: () => {
          this.editableUseCases = [];
        },
      });
  }

  onSearch(): void {
    if (!this.currentQuery || this.isSearching) {
      return;
    }

    this.isSearching = true;
    this.errorMessage = '';
    this.currentPage = 1;
    this.lastSearchTimeMs = null;
    this.resultCount = null;

    const startedAt = performance.now();

    const searchRequest: SemanticSearchRequest = {
      query: this.currentQuery,
      limit: this.currentConfig?.rag?.top_k ?? 10,
      threshold: this.currentConfig?.rag?.similarity_threshold,
      include_snippets: true,
      highlight_matches: true,
      search_type: 'SEMANTIC_SEARCH',
    };

    this.queryService
      .search(searchRequest)
      .pipe(
        finalize(() => (this.isSearching = false)),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (response) => {
          this.searchResults$.next(response);

          // Update status/footer
          this.lastSearchTimeMs = Math.max(
            Math.round(performance.now() - startedAt),
            response.processing_time_ms || 0
          );
          this.resultCount = response.total_count;

          // Populate results panel messages minimally
          this.messages = [
            {
              role: 'user',
              content: this.currentQuery,
              created_at: new Date().toISOString(),
            },
            {
              role: 'assistant',
              content: `Found ${response.total_count} results.`,
              created_at: new Date().toISOString(),
            },
          ];

          // ADR-030: History is now recorded by orchestrator pipeline,
          // not via direct frontend API calls (stateless architecture)

          this.snackBar.open(`Found ${response.total_count} results`, 'Close', {
            duration: 3000,
          });
        },
        error: (error: QueryError) => {
          this.errorMessage = error.message;
          this.snackBar.open('Search failed: ' + error.message, 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  onConfigChanged(config: QueryConfig): void {
    this.currentConfig = { ...config, query_type: 'semantic' };
  }

  private buildSearchRequest(): SemanticSearchRequest {
    // Kept for backward compatibility with legacy form
    const formValue = this.searchForm.value;

    const sort: SearchSort = {
      field: formValue.sort_field,
      order: formValue.sort_order as SortOrder,
    };

    return {
      query: formValue.query_text,
      sort,
      limit: formValue.limit,
      offset: (this.currentPage - 1) * formValue.limit,
      include_snippets: formValue.include_snippets,
      highlight_matches: formValue.highlight_matches,
      search_type: formValue.search_type as QueryType,
    };
  }

  // ADR-030: saveSearchToHistory() removed - history is now recorded by
  // the orchestrator pipeline, not via direct frontend API calls.

  onSuggestionSelected(event: any): void {
    this.searchForm.patchValue({
      query_text: event.option.value,
    });
  }

  clearForm(): void {
    this.searchForm.reset();
    this.searchForm.patchValue({
      search_type: 'SEMANTIC_SEARCH',
      limit: 25,
      include_snippets: true,
      highlight_matches: true,
    });
    this.searchResults$.next(null);
    this.errorMessage = '';
  }

  // ADR-030: saveAsFavorite() removed - history write operations are disabled
  // in Core Edition. Future: implement client-side favorites using localStorage.

  getResultTypeIcon(sourceType: string): string {
    switch (sourceType) {
      case 'DOCUMENT':
        return 'description';
      case 'CHUNK':
        return 'text_snippet';
      case 'METADATA':
        return 'info';
      case 'SUMMARY':
        return 'summarize';
      default:
        return 'description';
    }
  }

  viewChunkDetails(result: SearchResult): void {
    // Open chunk details dialog
    const dialogRef = this.dialog.open(ChunkDetailsDialogComponent, {
      width: '80vw',
      height: '70vh',
      maxWidth: '1000px',
      data: {
        chunk: result,
        chunkIndex: result.chunk_index,
        documentId: result.document_id,
        title: result.title,
      },
    });

    dialogRef.afterClosed().subscribe((dialogResult) => {
      if (dialogResult) {
        // Handle actions from chunk details dialog
        if (dialogResult.action === 'viewDocument') {
          this.viewFullDocument({
            ...result,
            document_id: dialogResult.documentId,
          });
        } else if (dialogResult.action === 'downloadDocument') {
          this.downloadDocument({
            ...result,
            document_id: dialogResult.documentId,
          });
        }
      }
    });
  }

  viewFullDocument(result: SearchResult): void {
    if (!result.document_id) {
      this.snackBar.open('Document ID not available', 'Close', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    // Open full document viewer dialog
    const dialogRef = this.dialog.open(DocumentViewerDialogComponent, {
      width: '90vw',
      height: '90vh',
      maxWidth: '1200px',
      data: {
        documentId: result.document_id,
        title: result.title,
        sourceType: result.source_type,
      },
    });
  }

  downloadDocument(result: SearchResult): void {
    if (!result.document_id) {
      this.snackBar.open('Document ID not available', 'Close', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    // Show loading message
    this.snackBar.open('Preparing download...', 'Close', {
      duration: 2000,
    });

    // Download the document
    this.documentService
      .downloadDocument(result.document_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (blob: Blob) => {
          // Create download link
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;

          // Use the result title as filename, fallback to document_id
          const filename = result.title
            ? `${result.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`
            : `document_${result.document_id}.pdf`;

          link.download = filename;
          document.body.appendChild(link);
          link.click();

          // Cleanup
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);

          this.snackBar.open('Download completed successfully', 'Close', {
            duration: 3000,
          });
        },
        error: (error) => {
          console.error('Download failed:', error);
          this.snackBar.open(
            'Download failed: ' + (error.message || 'Unknown error'),
            'Close',
            {
              duration: 5000,
              panelClass: ['error-snackbar'],
            }
          );
        },
      });
  }

  shareResult(result: SearchResult): void {
    this.snackBar.open('Sharing result...', 'Close', {
      duration: 2000,
    });
  }

  clearError(): void {
    this.errorMessage = '';
  }

  // Footer actions
  reset(): void {
    this.currentQuery = '';
    this.currentConfig = { ...getDefaultQueryConfig(), query_type: 'semantic' };
    this.messages = [];
    this.metrics = null;
    this.resultCount = null;
    this.lastSearchTimeMs = null;
    this.searchResults$.next(null);
    this.errorMessage = '';
  }

  exportConfiguration(): void {
    const config = {
      type: 'semantic_search',
      parameters: this.currentConfig,
      timestamp: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `semantic-search-config-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  get canSearch(): boolean {
    return !!this.currentQuery && this.currentQuery.trim().length >= 2;
  }

  applyToUseCase(): void {
    if (!this.selectedUseCaseId || !this.currentConfig) {
      return;
    }

    // Fetch current UC to merge config
    this.useCaseService
      .getUseCase(this.selectedUseCaseId, true)
      .pipe(
        switchMap((uc) => {
          const existing = uc?.config_json || ({} as Record<string, any>);
          const existingRag = (existing['rag'] || {}) as Record<string, any>;
          const existingVectorDb = (existing['vector_db'] || {}) as Record<
            string,
            any
          >;
          const merged: Record<string, any> = {
            ...existing,
            ['rag']: {
              ...existingRag,
              enabled: true,
              vector_collections: this.currentConfig.rag.vector_collections,
              top_k: this.currentConfig.rag.top_k,
              similarity_threshold: this.currentConfig.rag.similarity_threshold,
              hybrid_bm25: this.currentConfig.rag.hybrid_bm25,
            },
            ['vector_db']: {
              ...existingVectorDb,
              ef_search: this.currentConfig.vector_db?.ef_search,
              score_normalization:
                this.currentConfig.vector_db?.score_normalization,
            },
          };

          return this.useCaseService.updateUseCase(this.selectedUseCaseId!, {
            config_json: merged,
          });
        }),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (updated) => {
          this.snackBar.open(`Applied to "${updated.name}"`, 'Close', {
            duration: 3000,
          });
        },
        error: (err) => {
          this.snackBar.open(
            `Apply failed: ${err.message || 'Error'}`,
            'Close',
            { duration: 4000, panelClass: ['error-snackbar'] }
          );
        },
      });
  }
}
