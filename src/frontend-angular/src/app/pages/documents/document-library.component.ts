import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatNativeDateModule, MatOptionModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, debounceTime, startWith, switchMap } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import { Collection } from '../../api/models/collection.models';
import {
  Document,
  DocumentListResponse,
  DocumentSearchFilters,
  DocumentState,
} from '../../api/models/document.models';
import { CollectionService } from '../../api/services/collection.service';
import { DocumentService } from '../../api/services/document.service';
import { DocumentMetadataComponent } from './document-metadata.component';

@Component({
  selector: 'app-document-library',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatOptionModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatChipsModule,
    MatMenuModule,
    MatDialogModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
  ],
  template: `
    <!-- LAYERED_PAGE_LAYOUT_PATTERN Applied -->
    <!-- ADR-012 Compliant: Material + Tailwind utilities -->
    <div class="page-container">
      <!-- Layer 2: Page Header + Controls (NEVER SCROLLS) -->
      <div class="page-header-section">
        <div class="page-title">
          <h1>
            <lucide-icon name="library"></lucide-icon>
            Document Library
          </h1>
          <p class="subtitle">
            Browse, search, and manage your documents in the AI Operations
            Platform.
          </p>
        </div>

        <div class="page-controls">
          <div class="controls-container">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="!m-0 text-base font-medium">Search & Filter</h3>
              <span class="text-xs text-gray-500"
                >Find by filename, content, status, or classification</span
              >
            </div>

            <form [formGroup]="searchForm" class="flex flex-col gap-2">
              <div class="flex gap-3 items-center">
                <!-- Search: flexible width, takes remaining space -->
                <mat-form-field
                  appearance="outline"
                  class="flex-1 min-w-[200px]"
                >
                  <mat-label>Search documents</mat-label>
                  <input
                    matInput
                    formControlName="searchTerm"
                    placeholder="Search by filename, title, or content"
                  />
                  <mat-icon matSuffix>search</mat-icon>
                </mat-form-field>

                <!-- Collection: medium width for collection names -->
                <mat-form-field appearance="outline" class="w-48 shrink-0">
                  <mat-label>Collection</mat-label>
                  <mat-select formControlName="collection">
                    <mat-option value="">All Collections</mat-option>
                    <mat-option
                      *ngFor="let collection of availableCollections"
                      [value]="collection.name"
                    >
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{ collection.name }}</span>
                        <span class="text-xs text-gray-500"
                          >({{ collection.document_count }})</span
                        >
                      </div>
                    </mat-option>
                  </mat-select>
                </mat-form-field>

                <!-- Status: narrow width for short status options -->
                <mat-form-field appearance="outline" class="w-36 shrink-0">
                  <mat-label>Status</mat-label>
                  <mat-select formControlName="status">
                    <mat-option value="">All Statuses</mat-option>
                    <mat-option value="uploaded">Uploaded</mat-option>
                    <mat-option value="processing">Processing</mat-option>
                    <mat-option value="completed">Completed</mat-option>
                    <mat-option value="failed">Failed</mat-option>
                  </mat-select>
                </mat-form-field>

                <!-- Classification: medium width for classification labels -->
                <mat-form-field appearance="outline" class="w-44 shrink-0">
                  <mat-label>Classification</mat-label>
                  <mat-select formControlName="classification">
                    <mat-option value="">All Classifications</mat-option>
                    <mat-option value="public">Public</mat-option>
                    <mat-option value="internal">Internal</mat-option>
                    <mat-option value="confidential">Confidential</mat-option>
                    <mat-option value="restricted">Restricted</mat-option>
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="flex gap-3 items-center">
                <!-- From Date: narrow width -->
                <mat-form-field appearance="outline" class="w-40 shrink-0">
                  <mat-label>From Date</mat-label>
                  <input
                    matInput
                    [matDatepicker]="fromPicker"
                    formControlName="dateFrom"
                  />
                  <mat-datepicker-toggle
                    matSuffix
                    [for]="fromPicker"
                  ></mat-datepicker-toggle>
                  <mat-datepicker #fromPicker></mat-datepicker>
                </mat-form-field>

                <!-- To Date: narrow width -->
                <mat-form-field appearance="outline" class="w-40 shrink-0">
                  <mat-label>To Date</mat-label>
                  <input
                    matInput
                    [matDatepicker]="toPicker"
                    formControlName="dateTo"
                  />
                  <mat-datepicker-toggle
                    matSuffix
                    [for]="toPicker"
                  ></mat-datepicker-toggle>
                  <mat-datepicker #toPicker></mat-datepicker>
                </mat-form-field>

                <!-- Spacer -->
                <div class="flex-1"></div>

                <!-- Clear Filters button aligned right -->
                <button mat-button (click)="clearFilters()">
                  <lucide-icon name="x"></lucide-icon>
                  Clear Filters
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Layer 3: Content Area (SCROLLS) -->
      <div class="content-area">
        <!-- Document List -->
        <mat-card class="mb-6">
          <mat-card-header>
            <mat-card-title>Documents ({{ totalDocuments }})</mat-card-title>
            <div class="flex items-center gap-2">
              <mat-checkbox
                [(ngModel)]="showDeleted"
                (change)="toggleShowDeleted()"
              >
                Show Deleted
              </mat-checkbox>
              <button
                mat-icon-button
                (click)="toggleView()"
                [matTooltip]="viewType === 'grid' ? 'List View' : 'Grid View'"
              >
                <lucide-icon
                  [name]="viewType === 'grid' ? 'list' : 'layout-grid'"
                ></lucide-icon>
              </button>
              <button
                mat-icon-button
                (click)="refreshDocuments()"
                matTooltip="Refresh"
              >
                <lucide-icon name="refresh-cw"></lucide-icon>
              </button>
            </div>
          </mat-card-header>

          <mat-card-content>
            <!-- Loading State -->
            <div *ngIf="isLoading" class="loading-state">
              <mat-spinner diameter="40"></mat-spinner>
              <p>Loading documents...</p>
            </div>

            <!-- Empty State -->
            <div
              *ngIf="!isLoading && documents && documents.length === 0"
              class="empty-state"
            >
              <lucide-icon name="folder-open"></lucide-icon>
              <h3>No documents found</h3>
              <p>
                Try adjusting your search criteria or upload some documents.
              </p>
            </div>

            <!-- Grid View -->
            <div
              *ngIf="
                !isLoading &&
                documents &&
                documents.length > 0 &&
                viewType === 'grid'
              "
              class="grid-view"
            >
              <div
                *ngFor="let document of documents"
                class="document-card"
                (click)="selectDocument(document)"
              >
                <div class="document-header">
                  <lucide-icon
                    class="document-icon"
                    [name]="getDocumentIcon(document.file_type)"
                  ></lucide-icon>
                  <div class="document-actions">
                    <button
                      mat-icon-button
                      (click)="
                        downloadDocument(document); $event.stopPropagation()
                      "
                      matTooltip="Download"
                    >
                      <lucide-icon name="download"></lucide-icon>
                    </button>
                    <button
                      mat-icon-button
                      (click)="editDocument(document); $event.stopPropagation()"
                      matTooltip="Edit"
                    >
                      <lucide-icon name="pencil"></lucide-icon>
                    </button>
                    <button
                      mat-icon-button
                      (click)="
                        deleteDocument(document); $event.stopPropagation()
                      "
                      matTooltip="Delete"
                      color="warn"
                    >
                      <lucide-icon name="trash-2"></lucide-icon>
                    </button>
                  </div>
                </div>

                <div class="document-content">
                  <h4 class="document-title">
                    {{ document.title || document.original_file_name }}
                  </h4>
                  <p class="document-meta">
                    {{ formatFileSize(document.file_size) }} •
                    {{ formatDate(document.uploaded_at) }}
                  </p>
                  <div
                    class="document-metadata-grid"
                    *ngIf="
                      getChunkCount(document) || getCollectionName(document)
                    "
                  >
                    <div
                      class="metadata-item-small"
                      *ngIf="getCollectionName(document)"
                    >
                      <lucide-icon
                        class="metadata-icon-small text-blue-600"
                        name="folder"
                      ></lucide-icon>
                      <span class="font-medium">{{
                        getCollectionName(document)
                      }}</span>
                    </div>
                    <div
                      class="metadata-item-small"
                      *ngIf="getChunkCount(document)"
                      [matTooltip]="getChunkingTooltip(document)"
                    >
                      <lucide-icon
                        class="metadata-icon-small text-green-600"
                        name="chart-column"
                      ></lucide-icon>
                      <span>{{ getChunkCount(document) }} chunks</span>
                      <span
                        class="text-xs text-gray-500 ml-1"
                        *ngIf="getChunkingStrategy(document)"
                      >
                        ({{ getChunkingStrategy(document) }})
                      </span>
                    </div>
                  </div>
                  <div class="document-status" [class]="document.status">
                    <lucide-icon
                      [name]="getStatusIcon(document.status)"
                    ></lucide-icon>
                    {{ document.status }}
                  </div>
                </div>
              </div>
            </div>

            <!-- List View -->
            <div
              *ngIf="
                !isLoading &&
                documents &&
                documents.length > 0 &&
                viewType === 'list'
              "
              class="list-view"
            >
              <div class="list-header">
                <div class="col-filename">Filename</div>
                <div class="col-size">Size</div>
                <div class="col-chunks">Chunks</div>
                <div class="col-model">Model</div>
                <div class="col-status">Status</div>
                <div class="col-date">Uploaded</div>
                <div class="col-actions">Actions</div>
              </div>

              <div
                *ngFor="let document of documents"
                class="list-item"
                (click)="selectDocument(document)"
              >
                <div class="col-filename">
                  <lucide-icon
                    class="file-icon"
                    [name]="getDocumentIcon(document.file_type)"
                  ></lucide-icon>
                  <span class="filename">{{
                    document.title || document.original_file_name
                  }}</span>
                </div>
                <div class="col-size">
                  {{ formatFileSize(document.file_size) }}
                </div>
                <div class="col-chunks">
                  <span
                    class="chunk-badge"
                    *ngIf="getChunkCount(document)"
                    [matTooltip]="getChunkingTooltip(document)"
                  >
                    <lucide-icon
                      class="small-icon"
                      name="chart-column"
                    ></lucide-icon>
                    {{ getChunkCount(document) }}
                    <span
                      class="text-xs text-gray-500 ml-1"
                      *ngIf="getChunkingStrategy(document)"
                    >
                      ({{ getChunkingStrategy(document) }})
                    </span>
                  </span>
                  <span class="no-data" *ngIf="!getChunkCount(document)"
                    >—</span
                  >
                </div>
                <div class="col-model">
                  <span
                    class="model-badge"
                    *ngIf="getEmbeddingModel(document)"
                    [matTooltip]="getEmbeddingModel(document)"
                  >
                    {{ truncateModel(getEmbeddingModel(document)) }}
                  </span>
                  <span class="no-data" *ngIf="!getEmbeddingModel(document)"
                    >—</span
                  >
                </div>
                <div class="col-status">
                  <span class="status-badge" [class]="document.status">
                    {{ document.status }}
                  </span>
                </div>
                <div class="col-date">
                  {{ formatDate(document.uploaded_at) }}
                </div>
                <div class="col-actions">
                  <button
                    mat-icon-button
                    (click)="
                      downloadDocument(document); $event.stopPropagation()
                    "
                    matTooltip="Download"
                  >
                    <lucide-icon name="download"></lucide-icon>
                  </button>
                  <button
                    mat-icon-button
                    (click)="editDocument(document); $event.stopPropagation()"
                    matTooltip="Edit"
                  >
                    <lucide-icon name="pencil"></lucide-icon>
                  </button>
                  <button
                    mat-icon-button
                    (click)="deleteDocument(document); $event.stopPropagation()"
                    matTooltip="Delete"
                    color="warn"
                  >
                    <lucide-icon name="trash-2"></lucide-icon>
                  </button>
                </div>
              </div>
            </div>

            <!-- Pagination -->
            <mat-paginator
              *ngIf="!isLoading && documents && documents.length > 0"
              [length]="totalDocuments"
              [pageSize]="pageSize"
              [pageSizeOptions]="[10, 25, 50, 100]"
              (page)="onPageChange($event)"
              showFirstLastButtons
            >
            </mat-paginator>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    `
      /**
         * Document Library Styles
         * ADR-012 Compliant: Material + Tailwind + Component SCSS
         * LAYERED_PAGE_LAYOUT_PATTERN Applied
         */

      // Layer 2: Page container
      .page-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - var(--chrome-h));
        margin: -24px -32px;
        padding: 0;
        overflow: hidden;
      }

      // Layer 2: Page Header + Controls (NEVER SCROLLS)
      .page-header-section {
        flex: 0 0 auto;
        z-index: 100;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        .page-title {
          padding: 16px 24px 12px 24px;

          h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            height: 36px;

            mat-icon {
              font-size: 28px;
              width: 28px;
              height: 28px;
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
            padding: 8px 16px 4px 16px;

            h3 {
              margin: 0 !important;
              font-size: 20px !important;
              font-weight: 500;
            }

            ::ng-deep .mat-mdc-form-field-subscript-wrapper {
              display: none;
            }
          }
        }
      }

      // Layer 3: Content Area (SCROLLS)
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

      .loading-state,
      .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: #666;
      }

      .loading-state mat-spinner {
        margin: 0 auto 16px;
      }

      .empty-state mat-icon {
        font-size: 64px;
        width: 64px;
        height: 64px;
        margin-bottom: 16px;
        color: #ccc;
      }

      .grid-view {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;
      }

      .document-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: #fafafa;
      }

      .document-card:hover {
        border-color: #1976d2;
        box-shadow: 0 2px 8px rgba(25, 118, 210, 0.2);
      }

      .document-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .document-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: #1976d2;
      }

      .document-actions {
        display: flex;
        gap: 4px;
      }

      .document-title {
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .document-meta {
        margin: 0 0 8px 0;
        font-size: 12px;
        color: #666;
      }

      .document-status {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        font-weight: 500;
        padding: 4px 8px;
        border-radius: 4px;
        width: fit-content;
      }

      .document-status.completed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .document-status.processing {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .document-status.failed {
        background-color: #ffebee;
        color: #c62828;
      }

      .document-status.uploaded {
        background-color: #e3f2fd;
        color: #1976d2;
      }

      .list-view {
        display: flex;
        flex-direction: column;
      }

      .list-header {
        display: grid;
        grid-template-columns: 2fr 0.8fr 0.8fr 1.2fr 0.8fr 0.8fr 1fr;
        gap: 12px;
        padding: 12px 16px;
        background-color: #f5f5f5;
        border-radius: 4px;
        font-weight: 500;
        font-size: 14px;
      }

      .list-item {
        display: grid;
        grid-template-columns: 2fr 0.8fr 0.8fr 1.2fr 0.8fr 0.8fr 1fr;
        gap: 12px;
        padding: 12px 16px;
        border-bottom: 1px solid #e0e0e0;
        cursor: pointer;
        transition: background-color 0.3s ease;
        align-items: center;
      }

      .list-item:hover {
        background-color: #f5f5f5;
      }

      .col-filename {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .file-icon {
        color: #666;
      }

      .filename {
        font-weight: 500;
      }

      .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
      }

      .status-badge.completed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .status-badge.processing {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .status-badge.failed {
        background-color: #ffebee;
        color: #c62828;
      }

      .status-badge.uploaded {
        background-color: #e3f2fd;
        color: #1976d2;
      }

      .col-actions {
        display: flex;
        gap: 4px;
      }

      .chunk-badge,
      .model-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        padding: 2px 8px;
        background-color: #e3f2fd;
        border-radius: 4px;
        color: #1976d2;
        font-weight: 500;
      }

      .model-badge {
        background-color: #f3e5f5;
        color: #7b1fa2;
      }

      .small-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }

      .no-data {
        color: #999;
        font-size: 12px;
      }

      .document-metadata-grid {
        display: flex;
        gap: 8px;
        margin: 8px 0;
        flex-wrap: wrap;
      }

      .metadata-item-small {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        padding: 3px 6px;
        background-color: #f5f5f5;
        border-radius: 4px;
        color: #666;
      }

      .metadata-icon-small {
        font-size: 14px;
        width: 14px;
        height: 14px;
        color: #1976d2;
      }
    `,
  ],
})
export class DocumentLibraryComponent implements OnInit {
  searchForm: FormGroup;
  documents: Document[] = [];
  totalDocuments = 0;
  pageSize = 25;
  currentPage = 0;
  isLoading = false;
  viewType: 'grid' | 'list' = 'grid';
  showDeleted = false;
  availableCollections: Collection[] = [];

  constructor(
    private fb: FormBuilder,
    private documentService: DocumentService,
    private collectionService: CollectionService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.searchForm = this.fb.group({
      searchTerm: [''],
      collection: [''],
      status: [''],
      classification: [''],
      dateFrom: [null],
      dateTo: [null],
    });
  }

  ngOnInit(): void {
    this.loadCollections();
    this.setupSearchForm();
    this.loadDocuments();
  }

  loadCollections(): void {
    this.collectionService.listCollections(true).subscribe({
      next: (response) => {
        this.availableCollections = response.collections;
      },
      error: (error) => {
        console.error('Failed to load collections:', error);
      },
    });
  }

  setupSearchForm(): void {
    this.searchForm.valueChanges
      .pipe(
        debounceTime(300),
        startWith(this.searchForm.value),
        switchMap((filters) => {
          this.isLoading = true;
          return this.searchDocuments(filters);
        })
      )
      .subscribe({
        next: (response) => {
          this.documents = response.documents;
          this.totalDocuments = response.total;
          this.isLoading = false;
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to load documents: ${error.message}`,
            'Close',
            {
              duration: 5000,
            }
          );
          this.isLoading = false;
        },
      });
  }

  searchDocuments(filters: any): Observable<DocumentListResponse> {
    const searchFilters: DocumentSearchFilters = {
      searchTerm: filters.searchTerm || '',
      category: '',
      status: filters.status || '',
      classification: filters.classification || '',
      dateRange: {
        start: filters.dateFrom || null,
        end: filters.dateTo || null,
      },
      tags: [],
      uploadedBy: '',
    };

    return this.documentService.searchDocuments(searchFilters);
  }

  loadDocuments(): void {
    this.isLoading = true;
    this.documentService
      .getDocuments({
        limit: this.pageSize,
        offset: this.currentPage * this.pageSize,
        include_deleted: this.showDeleted,
      })
      .subscribe({
        next: (response) => {
          this.documents = response.documents;
          this.totalDocuments = response.total;
          this.isLoading = false;
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to load documents: ${error.message}`,
            'Close',
            {
              duration: 5000,
            }
          );
          this.isLoading = false;
        },
      });
  }

  toggleShowDeleted(): void {
    this.showDeleted = !this.showDeleted;
    this.loadDocuments();
  }

  refreshDocuments(): void {
    this.loadDocuments();
  }

  clearFilters(): void {
    this.searchForm.reset();
  }

  toggleView(): void {
    this.viewType = this.viewType === 'grid' ? 'list' : 'grid';
  }

  onPageChange(event: any): void {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadDocuments();
  }

  selectDocument(document: Document): void {
    // Open document details dialog
    const dialogRef = this.dialog.open(DocumentMetadataComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '85vh',
      data: {
        document,
        mode: 'view', // View mode (not edit)
      },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result === 'refresh') {
        this.loadDocuments();
      }
    });
  }

  downloadDocument(document: Document): void {
    this.documentService.downloadDocument(document.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = document.original_file_name;
        link.click();
        window.URL.revokeObjectURL(url);
      },
      error: (error) => {
        this.snackBar.open(
          `Failed to download document: ${error.message}`,
          'Close',
          {
            duration: 5000,
          }
        );
      },
    });
  }

  editDocument(document: Document): void {
    const dialogRef = this.dialog.open(DocumentMetadataComponent, {
      width: '600px',
      maxHeight: '90vh',
      data: { document },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        // Refresh the document list to show updated data
        this.loadDocuments();
        this.snackBar.open('Document metadata updated successfully', 'Close', {
          duration: 3000,
        });
      }
    });
  }

  deleteDocument(document: Document): void {
    if (
      confirm(
        `Are you sure you want to delete "${document.original_file_name}"?`
      )
    ) {
      this.documentService
        .deleteDocument({
          document_id: document.id,
          force: false,
        })
        .subscribe({
          next: () => {
            this.snackBar.open('Document deleted successfully', 'Close', {
              duration: 3000,
            });
            this.loadDocuments();
          },
          error: (error) => {
            this.snackBar.open(
              `Failed to delete document: ${error.message}`,
              'Close',
              {
                duration: 5000,
              }
            );
          },
        });
    }
  }

  getDocumentIcon(mimeType: string): string {
    if (!mimeType) return 'file-text';
    if (mimeType.includes('pdf')) return 'file-text';
    if (mimeType.includes('word')) return 'file-text';
    if (mimeType.includes('text')) return 'file-text';
    return 'file-text';
  }

  getStatusIcon(status: DocumentState): string {
    switch (status) {
      case DocumentState.PROCESSED:
        return 'circle-check';
      case 'processing':
        return 'hourglass';
      case 'failed':
        return 'circle-alert';
      case DocumentState.PENDING:
        return 'upload';
      default:
        return 'file-text';
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString();
  }

  truncateModel(model: string | null): string {
    if (!model) return '';
    // Truncate long model names for display
    if (model.length > 20) {
      return model.substring(0, 17) + '...';
    }
    return model;
  }

  getChunkCount(document: Document): number | null {
    // Try different possible field names
    return (
      (document as any).num_chunks ||
      (document as any).chunks_count ||
      document.metadata?.['num_chunks'] ||
      document.metadata?.['chunks_count'] ||
      null
    );
  }

  getEmbeddingModel(document: Document): string | null {
    // Try different possible field names
    return (
      (document as any).embedding_model ||
      document.metadata?.['embedding_model'] ||
      null
    );
  }

  getChunkingStrategy(document: Document): string | null {
    // Try to get chunking strategy from metadata
    return (
      document.metadata?.['chunking_strategy'] ||
      document.metadata?.['strategy'] ||
      null
    );
  }

  getChunkingTooltip(document: Document): string {
    const chunks = this.getChunkCount(document);
    const strategy = this.getChunkingStrategy(document);
    const avgSize = (document as any).avg_chunk_size_tokens;

    let tooltip = `${chunks} chunks`;
    if (strategy) {
      tooltip += ` (${strategy} strategy)`;
    }
    if (avgSize) {
      tooltip += ` · Avg ${avgSize} tokens/chunk`;
    }
    return tooltip;
  }

  getCollectionName(document: Document): string | null {
    // Try to get collection name from metadata
    return (
      document.metadata?.['collection_name'] ||
      document.metadata?.['collection'] ||
      null
    );
  }
}
