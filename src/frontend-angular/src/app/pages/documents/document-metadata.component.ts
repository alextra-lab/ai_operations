import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Inject,
  Input,
  OnInit,
  Output,
} from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatOptionModule } from '@angular/material/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { LucideAngularModule } from 'lucide-angular';
import {
  Document,
  DocumentMetadata,
  DocumentUpdateRequest,
} from '../../api/models/document.models';
import { DocumentService } from '../../api/services/document.service';

@Component({
  selector: 'app-document-metadata',
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
    MatChipsModule,
    MatDividerModule,
  ],
  template: `
    <div class="metadata-editor">
      <div class="editor-header">
        <h2>{{ document?.title || document?.original_file_name }}</h2>
        <p class="text-sm text-gray-600">
          {{ formatFileSize(document?.file_size || 0) }} •
          {{ document?.file_type }} •
          {{ formatDateString(document?.uploaded_at || '') }}
        </p>
      </div>

      <!-- Collection & Chunking Info (Prominent) -->
      <div class="flex gap-4 mb-4">
        <div
          class="flex-1 p-4 bg-blue-50 border border-blue-200 rounded flex items-center gap-3"
          *ngIf="getCollectionName()"
        >
          <lucide-icon
            class="text-blue-600 text-3xl"
            name="folder"
          ></lucide-icon>
          <div class="flex-1">
            <div class="text-xs text-blue-700 uppercase">Collection</div>
            <div class="text-lg font-semibold text-blue-900">
              {{ getCollectionName() }}
            </div>
          </div>
        </div>

        <div
          class="flex-1 p-4 bg-green-50 border border-green-200 rounded flex items-center gap-3"
          *ngIf="document?.num_chunks"
        >
          <lucide-icon
            class="text-green-600 text-3xl"
            name="chart-column"
          ></lucide-icon>
          <div class="flex-1">
            <div class="text-xs text-green-700 uppercase">Chunking</div>
            <div class="text-lg font-semibold text-green-900">
              {{ document?.num_chunks }} chunks
            </div>
            <div class="text-xs text-green-700" *ngIf="getChunkingStrategy()">
              Strategy: {{ getChunkingStrategy() }} • Avg
              {{ document?.avg_chunk_size_tokens }} tokens/chunk
            </div>
          </div>
        </div>
      </div>

      <form [formGroup]="metadataForm" class="metadata-form">
        <!-- Two Column Layout for Compact Display -->
        <div class="grid grid-cols-2 gap-4 mb-4">
          <!-- Left Column: Editable Fields -->
          <mat-card class="info-card">
            <mat-card-header>
              <mat-card-title class="text-base">Metadata</mat-card-title>
            </mat-card-header>

            <mat-card-content class="compact-form">
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Title</mat-label>
                <input matInput formControlName="title" />
              </mat-form-field>

              <div class="grid grid-cols-2 gap-2">
                <mat-form-field appearance="outline">
                  <mat-label>Source</mat-label>
                  <input matInput formControlName="source" />
                </mat-form-field>

                <mat-form-field appearance="outline">
                  <mat-label>Author</mat-label>
                  <input matInput formControlName="author" />
                </mat-form-field>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <mat-form-field appearance="outline">
                  <mat-label>Classification</mat-label>
                  <mat-select formControlName="classification">
                    <mat-option value="public">Public</mat-option>
                    <mat-option value="internal">Internal</mat-option>
                    <mat-option value="confidential">Confidential</mat-option>
                    <mat-option value="restricted">Restricted</mat-option>
                  </mat-select>
                </mat-form-field>

                <mat-form-field appearance="outline">
                  <mat-label>Tags</mat-label>
                  <input
                    matInput
                    formControlName="tags"
                    placeholder="tag1, tag2"
                  />
                </mat-form-field>
              </div>
            </mat-card-content>
          </mat-card>

          <!-- Right Column: Read-Only Properties -->
          <mat-card class="properties-card">
            <mat-card-header>
              <mat-card-title class="text-base">Properties</mat-card-title>
            </mat-card-header>

            <mat-card-content>
              <div class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <div class="property-item-compact">
                  <span class="text-xs text-gray-600 uppercase">Filename</span>
                  <span class="font-medium truncate">{{
                    document?.original_file_name
                  }}</span>
                </div>

                <div class="property-item-compact">
                  <span class="text-xs text-gray-600 uppercase">File Size</span>
                  <span class="font-medium">{{
                    formatFileSize(document?.file_size || 0)
                  }}</span>
                </div>

                <div class="property-item-compact">
                  <span class="text-xs text-gray-600 uppercase">Type</span>
                  <span class="font-medium uppercase">{{
                    document?.file_type
                  }}</span>
                </div>

                <div class="property-item-compact">
                  <span class="text-xs text-gray-600 uppercase">Status</span>
                  <span class="status-badge" [class]="document?.status">{{
                    document?.status
                  }}</span>
                </div>

                <div class="property-item-compact">
                  <span class="text-xs text-gray-600 uppercase">Uploaded</span>
                  <span class="text-xs">{{
                    formatDateString(document?.uploaded_at || '')
                  }}</span>
                </div>

                <div
                  class="property-item-compact"
                  *ngIf="document?.processed_at"
                >
                  <span class="text-xs text-gray-600 uppercase">Processed</span>
                  <span class="text-xs">{{
                    formatDateString(document?.processed_at || '')
                  }}</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Technical Details (Compact) -->
        <div
          class="flex gap-4"
          *ngIf="document?.embedding_model || customFields.length > 0"
        >
          <!-- Embedding Info -->
          <mat-card class="flex-1" *ngIf="document?.embedding_model">
            <mat-card-header>
              <mat-card-title class="text-sm">Embedding</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="text-xs text-gray-700">
                {{ document?.embedding_model }}
                <span
                  *ngIf="document?.embedding_dimensions"
                  class="text-gray-500"
                >
                  ({{ document?.embedding_dimensions }} dims)</span
                >
              </div>
            </mat-card-content>
          </mat-card>

          <!-- Custom Metadata -->
          <mat-card class="flex-1" *ngIf="customFields.length > 0">
            <mat-card-header>
              <mat-card-title class="text-sm"
                >Additional Metadata</mat-card-title
              >
            </mat-card-header>

            <mat-card-content>
              <div class="text-xs space-y-1">
                <div
                  *ngFor="let field of customFields"
                  class="flex items-center gap-2 text-gray-700"
                >
                  <span class="font-medium">{{ field.key }}:</span>
                  <span>{{ field.value }}</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      </form>

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-3 border-t border-gray-200 mt-3">
        <button mat-button (click)="cancel()" [disabled]="isSaving">
          Cancel
        </button>
        <button mat-button (click)="resetForm()" [disabled]="isSaving">
          <lucide-icon class="text-base" name="refresh-cw"></lucide-icon>
          Reset
        </button>
        <button
          mat-raised-button
          color="primary"
          (click)="saveMetadata()"
          [disabled]="!metadataForm.valid || isSaving"
        >
          <lucide-icon class="text-base" name="save"></lucide-icon>
          {{ isSaving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .metadata-editor {
        padding: 16px;
      }

      .editor-header {
        margin-bottom: 16px;
      }

      .editor-header h2 {
        margin: 0 0 4px 0;
        font-size: 20px;
        color: #1976d2;
      }

      .editor-header p {
        margin: 0;
        font-size: 13px;
      }

      .metadata-form {
        display: flex;
        flex-direction: column;
        gap: 0;
      }

      .compact-form {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 12px !important;
      }

      .property-item-compact {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      mat-card-header {
        padding: 12px 16px !important;
      }

      mat-card-content {
        padding: 12px 16px !important;
      }

      mat-form-field {
        font-size: 14px;
      }

      .status-badge {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        width: fit-content;
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

      .custom-fields {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .custom-field {
        display: flex;
        gap: 12px;
        align-items: center;
      }

      .field-key {
        flex: 1;
      }

      .field-value {
        flex: 2;
      }

      .add-field-btn {
        align-self: flex-start;
        margin-top: 8px;
      }

      .preview-content {
        max-height: 300px;
        overflow-y: auto;
        padding: 16px;
        background-color: #f5f5f5;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.4;
        white-space: pre-wrap;
      }

      .editor-actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
        margin-top: 24px;
        padding-top: 24px;
        border-top: 1px solid #e0e0e0;
      }
    `,
  ],
})
export class DocumentMetadataComponent implements OnInit {
  @Input() document?: Document;
  @Output() metadataSaved = new EventEmitter<Document>();
  @Output() cancelled = new EventEmitter<void>();

  metadataForm: FormGroup;
  customFields: { key: string; value: string }[] = [];
  isSaving = false;

  constructor(
    private fb: FormBuilder,
    private documentService: DocumentService,
    private snackBar: MatSnackBar,
    private dialogRef: MatDialogRef<DocumentMetadataComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { document: Document }
  ) {
    this.metadataForm = this.fb.group({
      title: [''],
      source: [''],
      author: [''],
      classification: ['internal'],
      tags: [''],
    });
  }

  ngOnInit(): void {
    if (this.data?.document) {
      this.document = this.data.document;
      this.loadDocumentMetadata();
    }
  }

  loadDocumentMetadata(): void {
    if (!this.document) return;

    this.metadataForm.patchValue({
      title: this.document.title || '',
      source: this.document.source || '',
      author: this.document.author || '',
      classification: this.document.classification || 'internal',
      tags: this.document.tags ? this.document.tags.join(', ') : '',
    });

    // Load custom metadata fields (excluding system fields)
    if (this.document.metadata) {
      const systemFields = [
        'collection_name',
        'collection_id',
        'chunking_strategy',
        'strategy',
      ];
      this.customFields = Object.entries(this.document.metadata)
        .filter(([key]) => !systemFields.includes(key))
        .map(([key, value]) => ({
          key,
          value: typeof value === 'string' ? value : JSON.stringify(value),
        }));
    }
  }

  addCustomField(): void {
    this.customFields.push({ key: '', value: '' });
  }

  removeCustomField(index: number): void {
    this.customFields.splice(index, 1);
  }

  saveMetadata(): void {
    if (!this.document || !this.metadataForm.valid) return;

    this.isSaving = true;

    const formValue = this.metadataForm.value;
    const customMetadata: DocumentMetadata = {};

    // Process custom fields
    this.customFields.forEach((field) => {
      if (field.key.trim() && field.value.trim()) {
        customMetadata[field.key.trim()] = field.value.trim();
      }
    });

    const updateRequest: DocumentUpdateRequest = {
      title: formValue.title || undefined,
      source: formValue.source || undefined,
      author: formValue.author || undefined,
      classification: formValue.classification || undefined,
      tags: formValue.tags
        ? formValue.tags
            .split(',')
            .map((tag: string) => tag.trim())
            .filter((tag: string) => tag)
        : undefined,
      metadata:
        Object.keys(customMetadata).length > 0 ? customMetadata : undefined,
    };

    this.documentService
      .updateDocument(this.document.id, updateRequest)
      .subscribe({
        next: (updatedDocument) => {
          this.snackBar.open(
            'Document metadata updated successfully',
            'Close',
            {
              duration: 3000,
            }
          );
          this.metadataSaved.emit(updatedDocument);
          this.isSaving = false;
          // Close dialog and return the updated document
          this.dialogRef.close(updatedDocument);
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to update metadata: ${error.message}`,
            'Close',
            {
              duration: 5000,
            }
          );
          this.isSaving = false;
        },
      });
  }

  resetForm(): void {
    this.loadDocumentMetadata();
  }

  cancel(): void {
    this.dialogRef.close();
  }

  formatDateString(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (error) {
      return dateString;
    }
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDate(date: Date): string {
    return new Date(date).toLocaleString();
  }

  getCollectionName(): string | null {
    if (!this.document) return null;
    return (
      this.document.metadata?.['collection_name'] ||
      this.document.metadata?.['collection'] ||
      null
    );
  }

  getChunkingStrategy(): string | null {
    if (!this.document) return null;
    const strategy =
      this.document.metadata?.['chunking_strategy'] ||
      this.document.metadata?.['strategy'] ||
      null;

    // Format strategy name for display
    if (strategy === 'recursive') return 'Recursive';
    if (strategy === 'fixed_token') return 'Fixed Token';
    if (strategy === 'sliding_token') return 'Sliding Window';
    if (strategy === 'heading_aware') return 'Heading Aware';
    if (strategy === 'sentence_paragraph') return 'Sentence/Paragraph';
    if (strategy === 'table_aware') return 'Table Aware';
    if (strategy === 'semantic_adaptive') return 'Semantic Adaptive';
    if (strategy === 'page_block') return 'Page Block';

    return strategy;
  }
}
