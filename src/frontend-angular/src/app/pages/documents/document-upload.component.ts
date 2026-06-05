import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatOptionModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import { Collection } from '../../api/models/collection.models';
import {
  Document,
  DocumentListResponse,
  DocumentState,
  DocumentUploadProgress,
  DocumentUploadRequest,
} from '../../api/models/document.models';
import { CollectionService } from '../../api/services/collection.service';
import { DocumentService } from '../../api/services/document.service';

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatOptionModule,
    MatButtonModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatCheckboxModule,
    MatTooltipModule,
  ],
  template: `
    <!-- LAYERED_PAGE_LAYOUT_PATTERN Applied -->
    <!-- ADR-012 Compliant: Material + Tailwind utilities -->
    <div class="page-container">
      <!-- Layer 2: Page Header + Controls (NEVER SCROLLS) -->
      <div class="page-header-section">
        <div class="page-title">
          <h1>
            <lucide-icon name="cloud-upload"></lucide-icon>
            Document Upload
          </h1>
          <p class="subtitle">
            Upload documents for processing, chunking, and vector embedding
          </p>
        </div>

        <div class="page-controls">
          <div class="controls-container">
            <!-- Compact File Upload Section -->
            <div class="flex gap-4 items-start mb-4">
              <!-- File Upload Area (Compact) -->
              <div
                class="upload-area-compact flex-1"
                [class.drag-over]="isDragOver"
                (dragover)="onDragOver($event)"
                (dragleave)="onDragLeave($event)"
                (drop)="onDrop($event)"
              >
                <div class="flex items-center gap-3">
                  <lucide-icon
                    class="text-blue-600"
                    name="cloud-upload"
                  ></lucide-icon>
                  <div class="flex-1">
                    <p class="m-0 font-medium">
                      Drag & drop files or click to browse
                    </p>
                    <p class="m-0 text-xs text-gray-600">
                      PDF, DOC, DOCX, TXT, RTF, ODT (max 50MB)
                    </p>
                  </div>
                  <button
                    mat-raised-button
                    color="primary"
                    type="button"
                    class="shrink-0"
                    (click)="fileInput.click()"
                  >
                    <lucide-icon name="folder-open"></lucide-icon>
                    Browse
                  </button>
                </div>

                <input
                  #fileInput
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.rtf,.odt"
                  (change)="onFileSelected($event)"
                  style="display: none;"
                />
              </div>
            </div>

            <!-- Selected Files (Compact) -->
            <div
              *ngIf="selectedFiles.length > 0"
              class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-medium text-blue-900"
                  >{{ selectedFiles.length }} file(s) selected</span
                >
                <button mat-button (click)="selectedFiles = []" class="text-xs">
                  Clear All
                </button>
              </div>
              <div class="flex flex-wrap gap-2 max-h-20 overflow-y-auto">
                <div
                  *ngFor="let file of selectedFiles; let i = index"
                  class="flex items-center gap-1 px-2 py-1 bg-white border border-blue-300 rounded text-xs"
                >
                  <lucide-icon
                    class="text-base text-gray-600"
                    name="file-text"
                  ></lucide-icon>
                  <span class="max-w-32 truncate">{{ file.name }}</span>
                  <button
                    mat-icon-button
                    (click)="removeFile(i)"
                    class="w-5 h-5"
                  >
                    <lucide-icon class="text-sm" name="x"></lucide-icon>
                  </button>
                </div>
              </div>
            </div>

            <!-- Upload Metadata Form (Minimal) -->
            <form [formGroup]="uploadForm" class="flex flex-col gap-3">
              <!-- Collection and Title in same row -->
              <div class="flex gap-3">
                <mat-form-field appearance="outline" class="flex-1">
                  <mat-label>Collection *</mat-label>
                  <mat-select formControlName="collection" required>
                    <mat-select-trigger>
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{
                          getSelectedCollectionName()
                        }}</span>
                        <span
                          class="text-xs text-gray-500"
                          *ngIf="getSelectedCollection()"
                        >
                          ({{ getSelectedCollection()?.document_count }} docs)
                        </span>
                        <span
                          class="flex items-center gap-1 text-xs text-blue-600"
                          *ngIf="getSelectedCollection()"
                        >
                          <lucide-icon
                            class="text-base"
                            name="brain-circuit"
                          ></lucide-icon>
                          {{ getSelectedCollection()?.embedding_model }}
                        </span>
                        <span
                          class="flex items-center gap-1 text-xs text-yellow-600"
                          *ngIf="getSelectedCollection()?.is_default"
                        >
                          <lucide-icon
                            class="text-base"
                            name="star"
                          ></lucide-icon>
                          Default
                        </span>
                      </div>
                    </mat-select-trigger>
                    <mat-option
                      *ngFor="let collection of availableCollections"
                      [value]="collection.name"
                    >
                      <div class="flex items-center justify-between w-full">
                        <div class="flex items-center gap-2">
                          <span class="font-medium">{{ collection.name }}</span>
                          <span class="text-xs text-gray-500"
                            >({{ collection.document_count }} docs)</span
                          >
                        </div>
                        <div class="flex items-center gap-2">
                          <span
                            class="flex items-center gap-1 text-xs text-blue-600"
                          >
                            <lucide-icon
                              class="text-base"
                              name="brain-circuit"
                            ></lucide-icon>
                            {{ collection.embedding_model }}
                          </span>
                          <span
                            *ngIf="collection.is_default"
                            class="flex items-center gap-1 text-xs text-yellow-600"
                          >
                            <lucide-icon
                              class="text-base"
                              name="star"
                            ></lucide-icon>
                            Default
                          </span>
                        </div>
                      </div>
                    </mat-option>
                  </mat-select>
                  <mat-hint>Target collection for documents</mat-hint>
                  <mat-error
                    *ngIf="uploadForm.get('collection')?.hasError('required')"
                  >
                    Collection is required
                  </mat-error>
                </mat-form-field>

                <mat-form-field appearance="outline" class="flex-1">
                  <mat-label>Title (Optional)</mat-label>
                  <input
                    matInput
                    formControlName="title"
                    placeholder="Document title"
                  />
                  <mat-hint>Override default title</mat-hint>
                </mat-form-field>
              </div>

              <!-- Chunking Status Indicator (Compact) -->
              <div class="flex items-center gap-2 text-xs text-gray-600">
                <lucide-icon
                  [class.text-green-600]="
                    uploadForm.value.chunkingStrategy === 'auto'
                  "
                  [class.text-blue-600]="
                    uploadForm.value.chunkingStrategy !== 'auto'
                  "
                  class="text-base"
                  [matTooltip]="getChunkingTooltip()"
                  [name]="
                    uploadForm.value.chunkingStrategy === 'auto'
                      ? 'sparkles'
                      : 'settings'
                  "
                ></lucide-icon>
                <span
                  [class.text-green-700]="
                    uploadForm.value.chunkingStrategy === 'auto'
                  "
                  [class.text-gray-700]="
                    uploadForm.value.chunkingStrategy !== 'auto'
                  "
                >
                  {{ getChunkingStatusLabel() }}
                </span>
              </div>

              <!-- Loading/Error States -->
              <div
                *ngIf="loadingCollections"
                class="flex items-center gap-2 p-2 bg-gray-50 border border-gray-200 rounded"
              >
                <mat-spinner diameter="20"></mat-spinner>
                <span class="text-sm text-gray-600"
                  >Loading collections...</span
                >
              </div>

              <div
                *ngIf="collectionError"
                class="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded"
              >
                <lucide-icon
                  class="text-red-600"
                  name="circle-alert"
                ></lucide-icon>
                <span class="text-sm text-red-800">{{ collectionError }}</span>
              </div>

              <!-- Action Buttons (Always Visible) -->
              <div class="flex gap-3 mt-4">
                <button
                  mat-raised-button
                  color="primary"
                  (click)="uploadFiles()"
                  [disabled]="selectedFiles.length === 0 || isUploading"
                >
                  <lucide-icon name="upload"></lucide-icon>
                  Upload {{ selectedFiles.length }} File(s)
                </button>

                <button
                  mat-button
                  (click)="clearForm()"
                  [disabled]="isUploading"
                >
                  Clear
                </button>

                <div class="flex-1"></div>

                <button
                  mat-stroked-button
                  color="accent"
                  type="button"
                  [disabled]="selectedFiles.length === 0"
                  routerLink="/documents/chunking-analysis"
                  matTooltip="Advanced workflow: See metrics, compare strategies, and manually configure chunking"
                  class="text-sm"
                >
                  <lucide-icon name="flask-conical"></lucide-icon>
                  Advanced Analysis
                </button>
              </div>

              <!-- Advanced Options Toggle -->
              <div class="mt-4 pt-4 border-t border-gray-300">
                <button
                  mat-button
                  type="button"
                  (click)="showAdvancedOptions = !showAdvancedOptions"
                  class="text-sm"
                >
                  <lucide-icon
                    [name]="showAdvancedOptions ? 'chevron-up' : 'chevron-down'"
                  ></lucide-icon>
                  {{ showAdvancedOptions ? 'Hide' : 'Show' }} Advanced Metadata
                  & Chunking Options
                </button>
              </div>

              <!-- Advanced Options (Collapsible) -->
              <div
                *ngIf="showAdvancedOptions"
                class="flex flex-col gap-3 p-3 bg-gray-50 border border-gray-200 rounded"
              >
                <!-- Metadata Section -->
                <div
                  class="text-xs font-semibold text-gray-700 uppercase tracking-wide"
                >
                  Document Metadata
                </div>

                <div class="flex gap-3">
                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Source</mat-label>
                    <input
                      matInput
                      formControlName="source"
                      placeholder="e.g., Internal, External"
                    />
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Author</mat-label>
                    <input
                      matInput
                      formControlName="author"
                      placeholder="Document author"
                    />
                  </mat-form-field>
                </div>

                <div class="flex gap-3">
                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Classification</mat-label>
                    <mat-select formControlName="classification">
                      <mat-option value="public">Public</mat-option>
                      <mat-option value="internal">Internal</mat-option>
                      <mat-option value="confidential">Confidential</mat-option>
                      <mat-option value="restricted">Restricted</mat-option>
                    </mat-select>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Tags</mat-label>
                    <input
                      matInput
                      formControlName="tags"
                      placeholder="Comma-separated tags"
                    />
                  </mat-form-field>
                </div>

                <!-- Chunking Configuration Section -->
                <div
                  class="text-xs font-semibold text-gray-700 uppercase tracking-wide mt-3 pt-3 border-t border-gray-300"
                >
                  Chunking Strategy
                </div>

                <div class="flex gap-3">
                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Chunking Strategy</mat-label>
                    <mat-select formControlName="chunkingStrategy">
                      <mat-select-trigger>
                        <div class="flex items-center gap-2">
                          <lucide-icon
                            class="text-green-600 text-base"
                            *ngIf="uploadForm.value.chunkingStrategy === 'auto'"
                            name="sparkles"
                          ></lucide-icon>
                          <lucide-icon
                            class="text-blue-600 text-base"
                            *ngIf="uploadForm.value.chunkingStrategy !== 'auto'"
                            name="settings"
                          ></lucide-icon>
                          <span>{{
                            formatStrategyName(
                              uploadForm.value.chunkingStrategy || 'auto'
                            )
                          }}</span>
                          <span
                            *ngIf="uploadForm.value.chunkingStrategy === 'auto'"
                            class="text-xs text-gray-500"
                            >(Recommended)</span
                          >
                        </div>
                      </mat-select-trigger>
                      <mat-option value="auto">
                        <div class="flex items-center gap-2">
                          <lucide-icon
                            class="text-green-600 text-base"
                            name="sparkles"
                          ></lucide-icon>
                          <span class="font-medium"
                            >Auto-Detect (Recommended)</span
                          >
                        </div>
                      </mat-option>
                      <mat-optgroup label="Manual Strategies">
                        <mat-option value="recursive"
                          >Recursive - Balanced (fallback default)</mat-option
                        >
                        <mat-option value="fixed_token"
                          >Fixed Token - Consistent sizes</mat-option
                        >
                        <mat-option value="sliding_token"
                          >Sliding Window - Better context overlap</mat-option
                        >
                        <mat-option value="heading_aware"
                          >Heading Aware - Structured documents</mat-option
                        >
                        <mat-option value="sentence_paragraph"
                          >Sentence/Paragraph - Natural boundaries</mat-option
                        >
                        <mat-option value="table_aware"
                          >Table Aware - Preserves tables</mat-option
                        >
                      </mat-optgroup>
                      <mat-optgroup label="Expert Strategies">
                        <mat-option value="semantic_adaptive"
                          >Semantic Adaptive - AI-driven (slow)</mat-option
                        >
                        <mat-option value="page_block"
                          >Page Block - Page-based splitting</mat-option
                        >
                      </mat-optgroup>
                    </mat-select>
                    <mat-hint
                      >Auto analyzes each document and picks optimal
                      strategy</mat-hint
                    >
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="w-32">
                    <mat-label>Chunk Size</mat-label>
                    <input
                      matInput
                      type="number"
                      formControlName="chunkSize"
                      placeholder="512"
                    />
                    <mat-hint>Tokens</mat-hint>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="w-32">
                    <mat-label>Overlap</mat-label>
                    <input
                      matInput
                      type="number"
                      formControlName="chunkOverlap"
                      placeholder="50"
                    />
                    <mat-hint>Tokens</mat-hint>
                  </mat-form-field>
                </div>

                <!-- Processing Options -->
                <div
                  class="text-xs font-semibold text-gray-700 uppercase tracking-wide mt-3 pt-3 border-t border-gray-300"
                >
                  Processing Options
                </div>

                <div class="flex flex-col gap-2">
                  <mat-checkbox formControlName="processAsync">
                    Process asynchronously (recommended for large files)
                  </mat-checkbox>
                  <mat-checkbox formControlName="preserveWhitespace">
                    Preserve whitespace in chunks
                  </mat-checkbox>
                  <mat-checkbox formControlName="respectSentenceBoundaries">
                    Respect sentence boundaries when chunking
                  </mat-checkbox>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Layer 3: Content Area (SCROLLS) -->
      <div class="content-area">
        <!-- Upload Progress -->
        <mat-card *ngIf="uploadProgress.length > 0" class="mb-6">
          <mat-card-header>
            <mat-card-title>Upload Progress</mat-card-title>
          </mat-card-header>

          <mat-card-content>
            <div *ngFor="let progress of uploadProgress" class="mb-4">
              <div class="flex justify-between items-center mb-2">
                <span class="font-medium">{{ progress.filename }}</span>
                <span class="status" [class]="progress.status">
                  {{ getStatusText(progress.status) }}
                </span>
              </div>

              <mat-progress-bar
                [value]="progress.progress"
                [mode]="
                  progress.status === 'uploading'
                    ? 'determinate'
                    : 'indeterminate'
                "
              >
              </mat-progress-bar>

              <div *ngIf="progress.message" class="mt-1 text-xs text-gray-600">
                {{ progress.message }}
              </div>

              <!-- Auto-detection details (P4-DOC-07) -->
              <div
                *ngIf="progress.status === 'analyzing'"
                class="mt-1 text-xs text-blue-700 flex items-center gap-1"
              >
                <lucide-icon class="text-sm" name="flask-conical"></lucide-icon>
                <span>{{
                  progress.message || 'Analyzing document structure...'
                }}</span>
                <span *ngIf="progress.strategies_tested">
                  ({{ progress.strategies_tested }})</span
                >
              </div>

              <!-- Selection result -->
              <div
                *ngIf="progress.selected_strategy"
                class="mt-1 text-xs text-green-700 flex items-center gap-1"
              >
                <lucide-icon class="text-sm" name="circle-check"></lucide-icon>
                <span
                  >Selected:
                  {{ formatStrategyName(progress.selected_strategy) }}</span
                >
                <span *ngIf="progress.confidence">
                  ({{ (progress.confidence * 100).toFixed(0) }}%
                  confidence)</span
                >
              </div>

              <div
                *ngIf="progress.error"
                class="flex items-center gap-1 mt-1 text-xs text-red-700"
              >
                <lucide-icon
                  class="text-base"
                  name="circle-alert"
                ></lucide-icon>
                {{ progress.error }}
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Upload History -->
        <mat-card class="mb-6">
          <mat-card-header>
            <mat-card-title>Recent Uploads</mat-card-title>
          </mat-card-header>

          <mat-card-content>
            <div
              *ngIf="recentUploads && recentUploads.length === 0"
              class="text-center p-6 text-gray-600"
            >
              <lucide-icon class="text-4xl" name="history"></lucide-icon>
              <p class="m-0">No recent uploads</p>
            </div>

            <div
              *ngFor="let upload of recentUploads"
              class="flex items-center py-3 border-b border-gray-200 last:border-b-0"
            >
              <lucide-icon
                class="mr-3 text-gray-600"
                name="file-text"
              ></lucide-icon>
              <div class="flex-1 ml-3">
                <span class="font-medium block">{{
                  upload.original_file_name
                }}</span>
                <span class="text-xs text-gray-600 block">{{
                  formatDateString(upload.uploaded_at)
                }}</span>
              </div>
              <div
                class="upload-status flex items-center gap-1 text-xs"
                [class]="upload.status"
              >
                <lucide-icon
                  class="text-base"
                  [name]="getStatusIcon(upload.status)"
                ></lucide-icon>
                {{ upload.status }}
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    `
      /**
         * Document Upload Styles
         * ADR-012 Compliant: Material + Tailwind + Component SCSS
         * LAYERED_PAGE_LAYOUT_PATTERN Applied
         *
         * Uses Tailwind for: layout, spacing, colors, typography
         * Uses SCSS for: critical flexbox pattern, complex component states
         */

      // ========================================================================
      // CRITICAL LAYERED PATTERN (Cannot be done with Tailwind utilities)
      // ========================================================================

      .page-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 200px);
        margin: -24px -32px;
        padding: 0;
        overflow: hidden; // CRITICAL: Prevents double scrollbars
      }

      // December 2025 Controls Container Standard
      .page-header-section {
        flex: 0 0 auto; // CRITICAL: Never grow/shrink
        z-index: 100;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);

        .page-title {
          padding: 16px 24px 12px 24px;

          h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            height: 36px;

            mat-icon {
              font-size: 28px;
              width: 28px;
              height: 28px;
              color: #1976d2;
            }
          }

          .subtitle {
            margin: 4px 0 0 0;
            color: #666;
            font-size: 13px;
          }
        }

        .page-controls {
          padding: 0 24px 12px 24px;

          .controls-container {
            background: #f5f5f5;
            border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
            padding: 16px;
          }
        }
      }

      .content-area {
        flex: 1; // CRITICAL: Take remaining space
        overflow-y: auto; // CRITICAL: Enable scrolling
        overflow-x: hidden;
        padding: 24px;
        min-height: 0; // CRITICAL: Allows flex child to shrink
        background: #fafafa;
      }

      // ========================================================================
      // COMPONENT-SPECIFIC STYLES (Complex states that need SCSS)
      // ========================================================================

      .upload-area-compact {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: #fafafa;

        &:hover,
        &.drag-over {
          border-color: #1976d2;
          background-color: #e3f2fd;
        }
      }

      .file-item {
        display: flex;
        align-items: center;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        background-color: #f9f9f9;
      }

      // Status badge colors
      .status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;

        &.uploading {
          background-color: #e3f2fd;
          color: #1976d2;
        }

        &.processing {
          background-color: #fff3e0;
          color: #f57c00;
        }

        &.completed {
          background-color: #e8f5e8;
          color: #2e7d32;
        }

        &.error {
          background-color: #ffebee;
          color: #c62828;
        }
      }

      // Upload status colors
      .upload-status {
        &.completed {
          color: #2e7d32;
        }

        &.processing {
          color: #f57c00;
        }

        &.failed {
          color: #c62828;
        }
      }
    `,
  ],
})
export class DocumentUploadComponent implements OnInit, OnDestroy {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  uploadForm: FormGroup;
  selectedFiles: File[] = [];
  isUploading = false;
  isDragOver = false;
  uploadProgress: DocumentUploadProgress[] = [];
  recentUploads: Document[] = [];
  showAdvancedOptions = false;

  // Collection support
  availableCollections: Collection[] = [];
  loadingCollections = false;
  collectionError = '';
  private statusPollingSubscription?: Subscription;
  private readonly POLLING_INTERVAL_MS = 2000; // Poll every 2 seconds

  constructor(
    private fb: FormBuilder,
    private documentService: DocumentService,
    private collectionService: CollectionService,
    private snackBar: MatSnackBar,
    private router: Router
  ) {
    this.uploadForm = this.fb.group({
      collection: ['default', Validators.required],
      title: [''],
      source: [''],
      author: [''],
      classification: ['internal'],
      tags: [''],
      // Chunking configuration (auto = system tests & picks best strategy)
      chunkingStrategy: ['auto'],
      chunkSize: [512, [Validators.min(64), Validators.max(8192)]],
      chunkOverlap: [50, [Validators.min(0), Validators.max(200)]],
      // Processing options
      processAsync: [true],
      preserveWhitespace: [true],
      respectSentenceBoundaries: [true],
    });
  }

  ngOnInit(): void {
    this.loadCollections();
    this.loadRecentUploads();
    this.subscribeToUploadProgress();
  }

  ngOnDestroy(): void {
    this.stopStatusPolling();
  }

  /**
   * Start polling for document status updates
   */
  private startStatusPolling(): void {
    this.stopStatusPolling();

    this.statusPollingSubscription = interval(this.POLLING_INTERVAL_MS)
      .pipe(
        switchMap(() => this.documentService.getDocuments({ limit: 5 })),
        takeWhile(() => {
          // Continue polling if any document is still processing
          return this.recentUploads.some(
            (doc) =>
              doc.status === DocumentState.PROCESSING ||
              doc.status === DocumentState.PENDING
          );
        }, true) // Include the last emission
      )
      .subscribe({
        next: (response: DocumentListResponse) => {
          this.recentUploads = response.documents;
        },
        error: (error: Error) => {
          console.error('Status polling error:', error);
          this.stopStatusPolling();
        },
      });
  }

  /**
   * Stop polling for document status
   */
  private stopStatusPolling(): void {
    if (this.statusPollingSubscription) {
      this.statusPollingSubscription.unsubscribe();
      this.statusPollingSubscription = undefined;
    }
  }

  loadCollections(): void {
    this.loadingCollections = true;
    this.collectionError = '';

    this.collectionService.listCollections(true).subscribe({
      next: (response: { collections: Collection[] }) => {
        this.availableCollections = response.collections;

        // Set default collection if exists
        const defaultCollection = this.availableCollections.find(
          (c) => c.is_default
        );
        if (defaultCollection) {
          this.uploadForm.patchValue({ collection: defaultCollection.name });
        }

        this.loadingCollections = false;
      },
      error: (error: any) => {
        console.error('Failed to load collections:', error);
        this.collectionError = 'Failed to load collections. Using default.';
        this.loadingCollections = false;

        this.snackBar.open('Failed to load collections', 'Close', {
          duration: 5000,
        });
      },
    });
  }

  getSelectedCollection(): Collection | undefined {
    const selectedName = this.uploadForm.get('collection')?.value;
    return this.availableCollections.find((c) => c.name === selectedName);
  }

  /**
   * Get the display name for the selected collection
   */
  getSelectedCollectionName(): string {
    const selected = this.getSelectedCollection();
    return (
      selected?.name || this.uploadForm.get('collection')?.value || 'default'
    );
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files) {
      this.addFiles(Array.from(files));
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
    }
  }

  addFiles(files: File[]): void {
    const validFiles = files.filter((file) => this.isValidFile(file));

    if (validFiles.length !== files.length) {
      this.snackBar.open(
        'Some files were skipped due to invalid format or size',
        'Close',
        {
          duration: 5000,
        }
      );
    }

    this.selectedFiles = [...this.selectedFiles, ...validFiles];
  }

  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
  }

  isValidFile(file: File): boolean {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'application/rtf',
      'application/vnd.oasis.opendocument.text',
    ];

    const maxSize = 50 * 1024 * 1024; // 50MB

    return allowedTypes.includes(file.type) && file.size <= maxSize;
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  uploadFiles(): void {
    if (this.selectedFiles.length === 0) return;

    this.isUploading = true;
    this.documentService.clearUploadProgress();

    const selectedCollection = this.getSelectedCollection();
    const collectionName = this.uploadForm.get('collection')?.value;

    if (!collectionName) {
      console.error('Collection name is undefined');
      this.snackBar.open(
        'Collection selection error. Please select a collection.',
        'Close',
        { duration: 5000 }
      );
      this.isUploading = false;
      return;
    }

    const uploadRequests: DocumentUploadRequest[] = this.selectedFiles.map(
      (file) => {
        const request: DocumentUploadRequest = {
          file,
          collection_name: collectionName,
          title: this.uploadForm.value.title || undefined,
          source: this.uploadForm.value.source || undefined,
          author: this.uploadForm.value.author || undefined,
          classification: this.uploadForm.value.classification || undefined,
          tags: this.uploadForm.value.tags
            ? this.uploadForm.value.tags
                .split(',')
                .map((tag: string) => tag.trim())
            : undefined,
          process_async: this.uploadForm.value.processAsync,
          // Chunking configuration
          chunking_config: {
            strategy: this.uploadForm.value.chunkingStrategy,
            chunk_size: this.uploadForm.value.chunkSize,
            chunk_overlap: this.uploadForm.value.chunkOverlap,
            preserve_whitespace: this.uploadForm.value.preserveWhitespace,
            respect_sentence_boundaries:
              this.uploadForm.value.respectSentenceBoundaries,
          },
        };

        return request;
      }
    );

    this.documentService.uploadDocuments(uploadRequests).subscribe({
      next: (documents) => {
        this.snackBar.open(
          `Successfully uploaded ${documents.length} document(s) to ${selectedCollection?.name || 'collection'}`,
          'Close',
          { duration: 5000 }
        );
        this.clearForm();
        this.loadRecentUploads();
        // Start polling for status updates
        this.startStatusPolling();
      },
      error: (error) => {
        this.snackBar.open(`Upload failed: ${error.message}`, 'Close', {
          duration: 5000,
        });
        this.isUploading = false;
      },
    });
  }

  clearForm(): void {
    this.selectedFiles = [];
    this.uploadForm.reset({
      classification: 'internal',
      processAsync: true,
    });
    this.documentService.clearUploadProgress();
    this.isUploading = false;
  }

  loadRecentUploads(): void {
    this.documentService.getDocuments({ limit: 5 }).subscribe({
      next: (response) => {
        this.recentUploads = response.documents;
      },
      error: (error) => {
        console.error('Failed to load recent uploads:', error);
      },
    });
  }

  subscribeToUploadProgress(): void {
    this.documentService.uploadProgress$.subscribe((progress) => {
      this.uploadProgress = progress;
    });
  }

  getStatusText(status: string): string {
    switch (status) {
      case 'uploading':
        return 'Uploading...';
      case 'analyzing':
        return 'Analyzing...';
      case 'chunking':
        return 'Chunking...';
      case 'embedding':
        return 'Embedding...';
      case 'processing':
        return 'Processing...';
      case DocumentState.PROCESSED:
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return status;
    }
  }

  getStatusIcon(status: DocumentState): string {
    switch (status) {
      case DocumentState.PROCESSED:
        return 'circle-check';
      case DocumentState.PROCESSING:
        return 'hourglass';
      case DocumentState.FAILED:
        return 'circle-alert';
      case DocumentState.PENDING:
        return 'upload';
      case DocumentState.DELETED:
        return 'trash-2';
      default:
        return 'file-text';
    }
  }

  formatDate(date: Date): string {
    return new Date(date).toLocaleString();
  }

  formatDateString(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  formatStrategyName(strategy: string | undefined): string {
    if (!strategy) return '';
    const strategyNames: Record<string, string> = {
      auto: 'Auto-Detect',
      recursive: 'Recursive',
      fixed_token: 'Fixed Token',
      sliding_token: 'Sliding Window',
      heading_aware: 'Heading Aware',
      sentence_paragraph: 'Sentence/Paragraph',
      table_aware: 'Table Aware',
      semantic_adaptive: 'Semantic Adaptive',
      page_block: 'Page Block',
    };
    return strategyNames[strategy] || strategy;
  }

  getChunkingStrategyLabel(): string {
    const strategy = this.uploadForm.value.chunkingStrategy || 'auto';
    const labels: Record<string, string> = {
      auto: 'Auto-Detect (AI Optimized)',
      recursive: 'Recursive - Balanced',
      fixed_token: 'Fixed Token',
      sliding_token: 'Sliding Window',
      heading_aware: 'Heading Aware',
      sentence_paragraph: 'Sentence/Paragraph',
      table_aware: 'Table Aware',
      semantic_adaptive: 'Semantic Adaptive',
      page_block: 'Page Block',
    };
    return labels[strategy] || strategy;
  }

  getChunkingStatusLabel(): string {
    const strategy = this.uploadForm.value.chunkingStrategy || 'auto';
    if (strategy === 'auto') {
      return 'Auto-Detect Active';
    }
    return `Manual: ${this.getChunkingStrategyLabel()}`;
  }

  getChunkingTooltip(): string {
    const strategy = this.uploadForm.value.chunkingStrategy || 'auto';

    if (strategy === 'auto') {
      return 'Auto-Detect Mode: System will analyze each document, test multiple strategies, and automatically select the optimal configuration. Click "Advanced Options" to override.';
    }

    const size = this.uploadForm.value.chunkSize || 512;
    const overlap = this.uploadForm.value.chunkOverlap || 50;
    return `Manual Mode: Using ${this.getChunkingStrategyLabel()} strategy with ${size} token chunks and ${overlap} token overlap. Click "Advanced Options" to change.`;
  }
}
