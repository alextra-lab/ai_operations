import { CommonModule, NgFor, NgIf } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { of } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';

import { Document } from '../../api/models/document.models';
import { DocumentService } from '../../api/services/document.service';
import { LucideAngularModule } from 'lucide-angular';

export interface DocumentViewerDialogData {
  documentId: string;
  title: string;
  sourceType: string;
}

@Component({
  selector: 'app-document-viewer-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    NgFor,
    NgIf,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTabsModule,
  ],
  template: `
    <div class="document-viewer-dialog">
      <!-- Dialog Header -->
      <div mat-dialog-title class="dialog-header">
        <div class="header-content">
          <lucide-icon class="document-icon" name="file-text"></lucide-icon>
          <div class="document-info">
            <h2 class="document-title">
              {{ data.title || 'Document Viewer' }}
            </h2>
            <p class="document-meta">
              <span class="document-id">ID: {{ data.documentId }}</span>
              <span class="source-type">{{ data.sourceType }}</span>
            </p>
          </div>
        </div>
        <button
          mat-icon-button
          mat-dialog-close
          class="close-button"
          [attr.aria-label]="'Close dialog'"
        >
          <lucide-icon name="x"></lucide-icon>
        </button>
      </div>

      <!-- Dialog Content -->
      <div mat-dialog-content class="dialog-content">
        <!-- Loading State -->
        <div *ngIf="isLoading" class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
          <p>Loading document...</p>
        </div>

        <!-- Error State -->
        <div *ngIf="errorMessage" class="error-container">
          <lucide-icon color="warn" class="error-icon" name="circle-alert"></lucide-icon>
          <h3>Error Loading Document</h3>
          <p>{{ errorMessage }}</p>
          <button mat-button (click)="retryLoad()">Retry</button>
        </div>

        <!-- Document Content -->
        <div *ngIf="document && !isLoading" class="document-content">
          <mat-tab-group class="document-tabs">
            <!-- Document Info Tab -->
            <mat-tab label="Document Info">
              <div class="document-info-content">
                <div class="info-grid">
                  <div class="info-item">
                    <label>Title:</label>
                    <span>{{ document.title }}</span>
                  </div>
                  <div class="info-item">
                    <label>File Type:</label>
                    <span>{{ document.file_type }}</span>
                  </div>
                  <div class="info-item">
                    <label>File Size:</label>
                    <span>{{ formatFileSize(document.file_size) }}</span>
                  </div>
                  <div class="info-item">
                    <label>Status:</label>
                    <span
                      class="status-badge"
                      [class]="'status-' + document.status.toLowerCase()"
                    >
                      {{ document.status }}
                    </span>
                  </div>
                  <div class="info-item">
                    <label>Classification:</label>
                    <span>{{ document.classification }}</span>
                  </div>
                  <div class="info-item">
                    <label>Author:</label>
                    <span>{{ document.author || 'Unknown' }}</span>
                  </div>
                  <div class="info-item">
                    <label>Uploaded:</label>
                    <span>{{ formatDate(document.uploaded_at) }}</span>
                  </div>
                  <div class="info-item">
                    <label>Processed:</label>
                    <span>{{
                      document.processed_at
                        ? formatDate(document.processed_at)
                        : 'Not processed'
                    }}</span>
                  </div>
                </div>

                <!-- Tags -->
                <div *ngIf="document.tags.length > 0" class="tags-section">
                  <h4>Tags:</h4>
                  <div class="tags-list">
                    <span *ngFor="let tag of document.tags" class="tag">{{
                      tag
                    }}</span>
                  </div>
                </div>

                <!-- Metadata -->
                <div *ngIf="hasMetadata()" class="metadata-section">
                  <h4>Metadata:</h4>
                  <div class="metadata-grid">
                    <div
                      *ngFor="let entry of getMetadataEntries()"
                      class="metadata-item"
                    >
                      <label>{{ entry[0] }}:</label>
                      <span>{{ formatMetadataValue(entry[1]) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </mat-tab>

            <!-- Document Preview Tab -->
            <mat-tab label="Preview">
              <div class="preview-content">
                <div *ngIf="!documentPreview" class="preview-placeholder">
                  <lucide-icon class="preview-icon" name="eye"></lucide-icon>
                  <p>Document preview not available</p>
                  <p class="preview-note">
                    This document type may not support preview, or preview
                    generation failed.
                  </p>
                </div>
                <div *ngIf="documentPreview" class="preview-container">
                  <iframe
                    [src]="getSafePreviewUrl()"
                    class="preview-iframe"
                    title="Document Preview"
                  >
                  </iframe>
                </div>
              </div>
            </mat-tab>
          </mat-tab-group>
        </div>
      </div>

      <!-- Dialog Actions -->
      <div mat-dialog-actions class="dialog-actions">
        <button mat-button (click)="downloadDocument()" [disabled]="!document">
          <lucide-icon name="download"></lucide-icon>
          Download
        </button>
        <button mat-button mat-dialog-close>Close</button>
      </div>
    </div>
  `,
  styles: [
    `
      .document-viewer-dialog {
        display: flex;
        flex-direction: column;
        height: 100%;
      }

      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        border-bottom: 1px solid #e0e0e0;
      }

      .header-content {
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1;
      }

      .document-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: #2196f3;
      }

      .document-info {
        flex: 1;
      }

      .document-title {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 500;
        color: #333;
      }

      .document-meta {
        margin: 4px 0 0 0;
        font-size: 0.875rem;
        color: #666;
        display: flex;
        gap: 16px;
      }

      .close-button {
        margin-left: 16px;
      }

      .dialog-content {
        flex: 1;
        padding: 24px;
        overflow: auto;
      }

      .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        padding: 40px;
      }

      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        padding: 40px;
        text-align: center;
      }

      .error-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
      }

      .document-content {
        height: 100%;
      }

      .document-tabs {
        height: 100%;
      }

      .document-info-content {
        padding: 16px 0;
      }

      .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }

      .info-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .info-item label {
        font-weight: 500;
        color: #666;
        font-size: 0.875rem;
      }

      .info-item span {
        color: #333;
      }

      .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
      }

      .status-badge.status-processed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .status-badge.status-processing {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .status-badge.status-error {
        background-color: #ffebee;
        color: #d32f2f;
      }

      .tags-section,
      .metadata-section {
        margin-top: 24px;
      }

      .tags-section h4,
      .metadata-section h4 {
        margin: 0 0 12px 0;
        color: #333;
        font-size: 1rem;
      }

      .tags-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .tag {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 4px 8px;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
      }

      .metadata-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 12px;
      }

      .metadata-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .metadata-item label {
        font-weight: 500;
        color: #666;
        font-size: 0.875rem;
      }

      .metadata-item span {
        color: #333;
        word-break: break-word;
      }

      .preview-content {
        height: 500px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
      }

      .preview-placeholder {
        text-align: center;
        color: #666;
      }

      .preview-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #ccc;
        margin-bottom: 16px;
      }

      .preview-note {
        font-size: 0.875rem;
        color: #999;
      }

      .preview-container {
        width: 100%;
        height: 100%;
      }

      .preview-iframe {
        width: 100%;
        height: 100%;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
      }

      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding: 16px 24px;
        border-top: 1px solid #e0e0e0;
      }

      @media (max-width: 768px) {
        .info-grid {
          grid-template-columns: 1fr;
        }

        .document-meta {
          flex-direction: column;
          gap: 4px;
        }

        .metadata-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class DocumentViewerDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  document: Document | null = null;
  documentPreview: any = null;
  isLoading = true;
  errorMessage = '';

  constructor(
    public dialogRef: MatDialogRef<DocumentViewerDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DocumentViewerDialogData,
    private documentService: DocumentService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadDocument();
  }

  private loadDocument(): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.documentService
      .getDocument(this.data.documentId)
      .pipe(
        finalize(() => { this.isLoading = false; this.cdr.detectChanges(); }),
        catchError((error) => {
          this.errorMessage = error.message || 'Failed to load document';
          return of(null);
        })
      )
      .subscribe((document) => {
        if (document) {
          this.document = document;
          this.loadDocumentPreview();
        }
      });
  }

  private loadDocumentPreview(): void {
    if (!this.document) return;

    this.documentService
      .getDocumentPreview(this.data.documentId)
      .pipe(
        catchError((error) => {
          console.warn('Preview not available:', error);
          return of(null);
        })
      )
      .subscribe((preview) => {
        this.documentPreview = preview;
      });
  }

  retryLoad(): void {
    this.loadDocument();
  }

  downloadDocument(): void {
    if (!this.document) return;

    this.snackBar.open('Starting download...', 'Close', { duration: 2000 });

    this.documentService
      .downloadDocument(this.data.documentId)
      .pipe(
        catchError((error) => {
          this.snackBar.open(
            'Download failed: ' + (error.message || 'Unknown error'),
            'Close',
            {
              duration: 5000,
              panelClass: ['error-snackbar'],
            }
          );
          return of(null);
        })
      )
      .subscribe((blob) => {
        if (blob) {
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download =
            this.document!.original_file_name ||
            `document_${this.data.documentId}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);

          this.snackBar.open('Download completed', 'Close', { duration: 3000 });
        }
      });
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatMetadataValue(value: any): string {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  }

  hasMetadata(): boolean {
    return !!(
      this.document?.metadata && Object.keys(this.document.metadata).length > 0
    );
  }

  getMetadataEntries(): [string, any][] {
    if (!this.document?.metadata) return [];
    return Object.entries(this.document.metadata);
  }

  getSafePreviewUrl(): string {
    if (!this.documentPreview) return '';
    // In a real implementation, you'd sanitize this URL
    return this.documentPreview.url || '';
  }
}
