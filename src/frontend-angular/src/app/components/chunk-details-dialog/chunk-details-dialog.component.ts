import { CommonModule, NgFor, NgIf } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
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
import { SearchResult } from '../../api/models/query.models';
import { DocumentService } from '../../api/services/document.service';
import { LucideAngularModule } from 'lucide-angular';

export interface ChunkDetailsDialogData {
  chunk: SearchResult;
  chunkIndex?: number;
  documentId?: string;
  title: string;
}

@Component({
  selector: 'app-chunk-details-dialog',
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
    <div class="chunk-details-dialog">
      <!-- Dialog Header -->
      <div mat-dialog-title class="dialog-header">
        <div class="header-content">
          <lucide-icon class="chunk-icon" name="file-text"></lucide-icon>
          <div class="chunk-info">
            <h2 class="chunk-title">Chunk Details</h2>
            <p class="chunk-meta">
              <span *ngIf="data.chunkIndex !== undefined" class="chunk-index"
                >Chunk #{{ data.chunkIndex }}</span
              >
              <span *ngIf="data.documentId" class="document-id"
                >Document: {{ data.documentId }}</span
              >
              <span
                class="relevance-score"
                [class.high]="data.chunk.relevance_score > 0.8"
                [class.medium]="data.chunk.relevance_score > 0.6"
              >
                {{ (data.chunk.relevance_score * 100).toFixed(1) }}% relevant
              </span>
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
        <mat-tab-group class="chunk-tabs">
          <!-- Chunk Content Tab -->
          <mat-tab label="Content">
            <div class="chunk-content-tab">
              <div class="content-header">
                <h3>Full Chunk Text</h3>
                <div class="content-stats">
                  <span class="char-count"
                    >{{ getContentLength() }} characters</span
                  >
                  <span class="word-count">{{ getWordCount() }} words</span>
                </div>
              </div>

              <div class="chunk-text-container">
                <div
                  class="chunk-text"
                  [innerHTML]="getHighlightedContent()"
                ></div>
              </div>

              <!-- Content Actions -->
              <div class="content-actions">
                <button mat-button (click)="copyChunkText()">
                  <lucide-icon name="copy"></lucide-icon>
                  Copy Text
                </button>
                <button mat-button (click)="copyChunkWithMetadata()">
                  <lucide-icon name="copy"></lucide-icon>
                  Copy with Metadata
                </button>
              </div>
            </div>
          </mat-tab>

          <!-- Chunk Metadata Tab -->
          <mat-tab label="Metadata">
            <div class="metadata-tab">
              <div class="metadata-sections">
                <!-- Search Result Metadata -->
                <div class="metadata-section">
                  <h4>Search Result Information</h4>
                  <div class="metadata-grid">
                    <div class="metadata-item">
                      <label>Result ID:</label>
                      <span class="monospace">{{ data.chunk.id }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Source Type:</label>
                      <span class="source-type-badge">{{
                        data.chunk.source_type
                      }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Relevance Score:</label>
                      <span
                        class="score-badge"
                        [class.high]="data.chunk.relevance_score > 0.8"
                        [class.medium]="data.chunk.relevance_score > 0.6"
                      >
                        {{ (data.chunk.relevance_score * 100).toFixed(1) }}%
                      </span>
                    </div>
                    <div class="metadata-item">
                      <label>Confidence Score:</label>
                      <span
                        class="score-badge"
                        [class.high]="data.chunk.confidence > 0.8"
                        [class.medium]="data.chunk.confidence > 0.6"
                      >
                        {{ (data.chunk.confidence * 100).toFixed(1) }}%
                      </span>
                    </div>
                    <div
                      class="metadata-item"
                      *ngIf="data.chunk.chunk_index !== undefined"
                    >
                      <label>Chunk Index:</label>
                      <span>{{ data.chunk.chunk_index }}</span>
                    </div>
                    <div class="metadata-item" *ngIf="data.chunk.document_id">
                      <label>Document ID:</label>
                      <span class="monospace">{{
                        data.chunk.document_id
                      }}</span>
                    </div>
                  </div>
                </div>

                <!-- Document Metadata -->
                <div class="metadata-section" *ngIf="document">
                  <h4>Document Information</h4>
                  <div class="metadata-grid">
                    <div class="metadata-item">
                      <label>Title:</label>
                      <span>{{ document.title }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>File Type:</label>
                      <span>{{ document.file_type }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>File Size:</label>
                      <span>{{ formatFileSize(document.file_size) }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Status:</label>
                      <span
                        class="status-badge"
                        [class]="'status-' + document.status.toLowerCase()"
                      >
                        {{ document.status }}
                      </span>
                    </div>
                    <div class="metadata-item">
                      <label>Classification:</label>
                      <span>{{ document.classification }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Author:</label>
                      <span>{{ document.author || 'Unknown' }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Uploaded:</label>
                      <span>{{ formatDate(document.uploaded_at) }}</span>
                    </div>
                    <div class="metadata-item">
                      <label>Total Chunks:</label>
                      <span>{{ document.num_chunks || 'Unknown' }}</span>
                    </div>
                  </div>
                </div>

                <!-- Chunk Metadata -->
                <div class="metadata-section">
                  <h4>Chunk Metadata</h4>
                  <div class="metadata-grid">
                    <div
                      *ngFor="let entry of getChunkMetadataEntries()"
                      class="metadata-item"
                    >
                      <label>{{ formatMetadataKey(entry[0]) }}:</label>
                      <span>{{ formatMetadataValue(entry[1]) }}</span>
                    </div>
                  </div>
                </div>

                <!-- Suggested Actions -->
                <div
                  class="metadata-section"
                  *ngIf="data.chunk.suggested_actions?.length"
                >
                  <h4>Suggested Actions</h4>
                  <div class="suggested-actions">
                    <span
                      *ngFor="let action of data.chunk.suggested_actions"
                      class="action-chip"
                    >
                      {{ action }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </mat-tab>

          <!-- Context Tab -->
          <mat-tab label="Context" *ngIf="data.documentId">
            <div class="context-tab">
              <div *ngIf="isLoadingDocument" class="loading-container">
                <mat-spinner diameter="30"></mat-spinner>
                <p>Loading document context...</p>
              </div>

              <div
                *ngIf="document && !isLoadingDocument"
                class="document-context"
              >
                <h4>Document Context</h4>
                <p class="context-description">
                  This chunk is part of the document "{{ document.title }}"
                  <span *ngIf="data.chunkIndex !== undefined"
                    >at position {{ data.chunkIndex }}</span
                  >
                  <span *ngIf="document.num_chunks"
                    >out of {{ document.num_chunks }} total chunks</span
                  >.
                </p>

                <div class="context-actions">
                  <button
                    mat-raised-button
                    color="primary"
                    (click)="viewFullDocument()"
                  >
                    <lucide-icon name="file-text"></lucide-icon>
                    View Full Document
                  </button>
                  <button mat-button (click)="downloadDocument()">
                    <lucide-icon name="download"></lucide-icon>
                    Download Document
                  </button>
                </div>
              </div>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>

      <!-- Dialog Actions -->
      <div mat-dialog-actions class="dialog-actions">
        <button
          mat-button
          (click)="downloadDocument()"
          [disabled]="!data.documentId"
        >
          <lucide-icon name="download"></lucide-icon>
          Download Document
        </button>
        <button
          mat-button
          (click)="viewFullDocument()"
          [disabled]="!data.documentId"
        >
          <lucide-icon name="file-text"></lucide-icon>
          View Full Document
        </button>
        <button mat-button mat-dialog-close>Close</button>
      </div>
    </div>
  `,
  styles: [
    `
      .chunk-details-dialog {
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

      .chunk-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: #ff9800;
      }

      .chunk-info {
        flex: 1;
      }

      .chunk-title {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 500;
        color: #333;
      }

      .chunk-meta {
        margin: 4px 0 0 0;
        font-size: 0.875rem;
        color: #666;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
      }

      .chunk-index {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 500;
      }

      .document-id {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 2px 6px;
        border-radius: 4px;
      }

      .relevance-score {
        font-weight: 500;
      }

      .relevance-score.high {
        color: #4caf50;
      }

      .relevance-score.medium {
        color: #ff9800;
      }

      .close-button {
        margin-left: 16px;
      }

      .dialog-content {
        flex: 1;
        padding: 24px;
        overflow: auto;
      }

      .chunk-tabs {
        height: 100%;
      }

      .chunk-content-tab {
        padding: 16px 0;
      }

      .content-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }

      .content-header h3 {
        margin: 0;
        color: #333;
      }

      .content-stats {
        display: flex;
        gap: 16px;
        font-size: 0.875rem;
        color: #666;
      }

      .chunk-text-container {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        max-height: 400px;
        overflow-y: auto;
      }

      .chunk-text {
        line-height: 1.6;
        font-size: 0.95rem;
        color: #333;
        white-space: pre-wrap;
        word-wrap: break-word;
      }

      .content-actions {
        display: flex;
        gap: 8px;
      }

      .metadata-tab {
        padding: 16px 0;
      }

      .metadata-sections {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .metadata-section h4 {
        margin: 0 0 16px 0;
        color: #333;
        font-size: 1.1rem;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 8px;
      }

      .metadata-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
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

      .monospace {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 2px 4px;
        border-radius: 3px;
        font-size: 0.85rem;
      }

      .source-type-badge {
        background-color: #e8f5e8;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
      }

      .score-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
      }

      .score-badge.high {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .score-badge.medium {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .score-badge:not(.high):not(.medium) {
        background-color: #ffebee;
        color: #d32f2f;
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

      .suggested-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .action-chip {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 4px 8px;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
      }

      .context-tab {
        padding: 16px 0;
      }

      .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        padding: 40px;
      }

      .document-context {
        padding: 16px;
        background-color: #f9f9f9;
        border-radius: 8px;
      }

      .context-description {
        margin-bottom: 16px;
        color: #666;
        line-height: 1.5;
      }

      .context-actions {
        display: flex;
        gap: 8px;
      }

      .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding: 16px 24px;
        border-top: 1px solid #e0e0e0;
      }

      @media (max-width: 768px) {
        .metadata-grid {
          grid-template-columns: 1fr;
        }

        .chunk-meta {
          flex-direction: column;
          gap: 8px;
        }

        .content-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }

        .context-actions {
          flex-direction: column;
        }
      }
    `,
  ],
})
export class ChunkDetailsDialogComponent implements OnInit {
  document: Document | null = null;
  isLoadingDocument = false;

  constructor(
    public dialogRef: MatDialogRef<ChunkDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ChunkDetailsDialogData,
    private documentService: DocumentService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    if (this.data.documentId) {
      this.loadDocument();
    }
  }

  private loadDocument(): void {
    this.isLoadingDocument = true;

    this.documentService
      .getDocument(this.data.documentId!)
      .pipe(
        finalize(() => (this.isLoadingDocument = false)),
        catchError((error) => {
          console.warn('Failed to load document:', error);
          return of(null);
        })
      )
      .subscribe((document) => {
        this.document = document;
      });
  }

  getContentLength(): number {
    const content = this.data.chunk.content || this.data.chunk.snippet || '';
    return content.length;
  }

  getWordCount(): number {
    const content = this.data.chunk.content || this.data.chunk.snippet || '';
    return content.split(/\s+/).filter((word) => word.length > 0).length;
  }

  getHighlightedContent(): string {
    const content = this.data.chunk.content || this.data.chunk.snippet || '';
    if (this.data.chunk.highlighted_content) {
      return this.data.chunk.highlighted_content;
    }
    return content;
  }

  getChunkMetadataEntries(): [string, any][] {
    if (!this.data.chunk.metadata) return [];
    return Object.entries(this.data.chunk.metadata);
  }

  formatMetadataKey(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }

  formatMetadataValue(value: any): string {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
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

  copyChunkText(): void {
    const text = this.data.chunk.content || this.data.chunk.snippet || '';
    navigator.clipboard
      .writeText(text)
      .then(() => {
        this.snackBar.open('Chunk text copied to clipboard', 'Close', {
          duration: 2000,
        });
      })
      .catch(() => {
        this.snackBar.open('Failed to copy text', 'Close', { duration: 2000 });
      });
  }

  copyChunkWithMetadata(): void {
    const text = this.data.chunk.content || this.data.chunk.snippet || '';
    const metadata = `Chunk Details:
Title: ${this.data.title}
Chunk Index: ${this.data.chunkIndex || 'N/A'}
Document ID: ${this.data.documentId || 'N/A'}
Relevance Score: ${(this.data.chunk.relevance_score * 100).toFixed(1)}%
Confidence: ${(this.data.chunk.confidence * 100).toFixed(1)}%

Content:
${text}`;

    navigator.clipboard
      .writeText(metadata)
      .then(() => {
        this.snackBar.open('Chunk with metadata copied to clipboard', 'Close', {
          duration: 2000,
        });
      })
      .catch(() => {
        this.snackBar.open('Failed to copy text', 'Close', { duration: 2000 });
      });
  }

  viewFullDocument(): void {
    if (!this.data.documentId) return;

    // Close this dialog and open document viewer
    this.dialogRef.close({
      action: 'viewDocument',
      documentId: this.data.documentId,
    });
  }

  downloadDocument(): void {
    if (!this.data.documentId) return;

    // Close this dialog and trigger download
    this.dialogRef.close({
      action: 'downloadDocument',
      documentId: this.data.documentId,
    });
  }
}
