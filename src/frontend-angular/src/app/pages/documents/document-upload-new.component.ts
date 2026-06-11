import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

import {
  Document,
  DocumentState,
  DocumentUploadProgress,
  DocumentUploadRequest,
} from '../../api/models/document.models';
import { DocumentService } from '../../api/services/document.service';

@Component({
  selector: 'app-document-upload',
  standalone: true,
  template: `
    <div class="document-upload-page">
      <div class="upload-header">
        <h1>Document Upload</h1>
        <p>
          Upload documents to the AI Operations Platform for processing and
          analysis.
        </p>
      </div>

      <!-- Upload Form -->
      <mat-card class="upload-card">
        <mat-card-header>
          <mat-card-title>Upload Documents</mat-card-title>
          <mat-card-subtitle
            >Select files or drag and drop them here</mat-card-subtitle
          >
        </mat-card-header>

        <mat-card-content>
          <!-- File Upload Area -->
          <div
            class="upload-area"
            [class.drag-over]="isDragOver"
            (dragover)="onDragOver($event)"
            (dragleave)="onDragLeave($event)"
            (drop)="onDrop($event)"
            (click)="fileInput.click()"
          >
            <div class="upload-content">
              <lucide-icon
                class="upload-icon"
                name="cloud-upload"
              ></lucide-icon>
              <h3>Drag & Drop Files Here</h3>
              <p>or click to browse files</p>
              <button mat-raised-button color="primary" type="button">
                <lucide-icon name="folder-open"></lucide-icon>
                Choose Files
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

          <!-- Selected Files -->
          <div *ngIf="selectedFiles.length > 0" class="selected-files">
            <h4>Selected Files ({{ selectedFiles.length }})</h4>
            <div class="file-list">
              <div
                *ngFor="let file of selectedFiles; let i = index"
                class="file-item"
              >
                <lucide-icon class="file-icon" name="file-text"></lucide-icon>
                <div class="file-info">
                  <span class="file-name">{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                </div>
                <button mat-icon-button (click)="removeFile(i)" color="warn">
                  <lucide-icon name="x"></lucide-icon>
                </button>
              </div>
            </div>
          </div>

          <!-- Upload Metadata Form -->
          <form [formGroup]="uploadForm" class="upload-form">
            <div class="form-row">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Title (Optional)</mat-label>
                <input
                  matInput
                  formControlName="title"
                  placeholder="Document title"
                />
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Source</mat-label>
                <input
                  matInput
                  formControlName="source"
                  placeholder="e.g., Internal, External"
                />
              </mat-form-field>

              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Author</mat-label>
                <input
                  matInput
                  formControlName="author"
                  placeholder="Document author"
                />
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Classification</mat-label>
                <mat-select formControlName="classification">
                  <mat-option value="public">Public</mat-option>
                  <mat-option value="internal">Internal</mat-option>
                  <mat-option value="confidential">Confidential</mat-option>
                  <mat-option value="restricted">Restricted</mat-option>
                </mat-select>
              </mat-form-field>

              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Tags</mat-label>
                <input
                  matInput
                  formControlName="tags"
                  placeholder="Comma-separated tags"
                />
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-checkbox formControlName="processAsync">
                Process asynchronously (recommended for large files)
              </mat-checkbox>
            </div>
          </form>
        </mat-card-content>

        <mat-card-actions>
          <button
            mat-raised-button
            color="primary"
            (click)="uploadFiles()"
            [disabled]="selectedFiles.length === 0 || isUploading"
            [loading]="isUploading"
          >
            <lucide-icon name="upload"></lucide-icon>
            Upload {{ selectedFiles.length }} File(s)
          </button>

          <button mat-button (click)="clearForm()" [disabled]="isUploading">
            Clear
          </button>
        </mat-card-actions>
      </mat-card>

      <!-- Upload Progress -->
      <mat-card *ngIf="uploadProgress.length > 0" class="progress-card">
        <mat-card-header>
          <mat-card-title>Upload Progress</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <div *ngFor="let progress of uploadProgress" class="progress-item">
            <div class="progress-header">
              <span class="file-name">{{ progress.filename }}</span>
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

            <div *ngIf="progress.message" class="progress-message">
              {{ progress.message }}
            </div>

            <div *ngIf="progress.error" class="error-message">
              <lucide-icon name="circle-alert"></lucide-icon>
              {{ progress.error }}
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Upload History -->
      <mat-card class="history-card">
        <mat-card-header>
          <mat-card-title>Recent Uploads</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <div *ngIf="recentUploads.length === 0" class="no-uploads">
            <lucide-icon name="history"></lucide-icon>
            <p>No recent uploads</p>
          </div>

          <div *ngFor="let upload of recentUploads" class="upload-item">
            <lucide-icon class="file-icon" name="file-text"></lucide-icon>
            <div class="upload-info">
              <span class="file-name">{{ upload.filename }}</span>
              <span class="upload-time">{{
                formatDate(upload.uploaded_at)
              }}</span>
            </div>
            <div class="upload-status" [class]="upload.status">
              <lucide-icon [name]="getStatusIcon(upload.status)"></lucide-icon>
              {{ upload.status }}
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .document-upload-page {
        padding: 24px;
        max-width: 1200px;
        margin: 0 auto;
      }

      .upload-header {
        margin-bottom: 24px;
      }

      .upload-header h1 {
        margin: 0 0 8px 0;
        color: #1976d2;
      }

      .upload-header p {
        margin: 0;
        color: #666;
      }

      .upload-card,
      .progress-card,
      .history-card {
        margin-bottom: 24px;
      }

      .upload-area {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 48px 24px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        background-color: #fafafa;
      }

      .upload-area:hover,
      .upload-area.drag-over {
        border-color: #1976d2;
        background-color: #e3f2fd;
      }

      .upload-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
      }

      .upload-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #1976d2;
      }

      .selected-files {
        margin-top: 24px;
      }

      .file-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .file-item {
        display: flex;
        align-items: center;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        background-color: #f9f9f9;
      }

      .file-icon {
        margin-right: 12px;
        color: #666;
      }

      .file-info {
        flex: 1;
        display: flex;
        flex-direction: column;
      }

      .file-name {
        font-weight: 500;
      }

      .file-size {
        font-size: 12px;
        color: #666;
      }

      .upload-form {
        margin-top: 24px;
      }

      .form-row {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
      }

      .full-width {
        width: 100%;
      }

      .half-width {
        flex: 1;
      }

      .progress-item {
        margin-bottom: 16px;
      }

      .progress-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }

      .status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
      }

      .status.uploading {
        background-color: #e3f2fd;
        color: #1976d2;
      }

      .status.processing {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .status.completed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .status.error {
        background-color: #ffebee;
        color: #c62828;
      }

      .progress-message {
        margin-top: 4px;
        font-size: 12px;
        color: #666;
      }

      .error-message {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
        color: #c62828;
        font-size: 12px;
      }

      .no-uploads {
        text-align: center;
        padding: 24px;
        color: #666;
      }

      .upload-item {
        display: flex;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #e0e0e0;
      }

      .upload-info {
        flex: 1;
        margin-left: 12px;
      }

      .upload-time {
        font-size: 12px;
        color: #666;
      }

      .upload-status {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
      }

      .upload-status.completed {
        color: #2e7d32;
      }

      .upload-status.processing {
        color: #f57c00;
      }

      .upload-status.failed {
        color: #c62828;
      }
    `,
  ],
})
export class DocumentUploadComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  uploadForm: FormGroup;
  selectedFiles: File[] = [];
  isUploading = false;
  isDragOver = false;
  uploadProgress: DocumentUploadProgress[] = [];
  recentUploads: Document[] = [];

  constructor(
    private fb: FormBuilder,
    private documentService: DocumentService,
    private snackBar: MatSnackBar,
    private router: Router
  ) {
    this.uploadForm = this.fb.group({
      title: [''],
      source: [''],
      author: [''],
      classification: ['internal'],
      tags: [''],
      processAsync: [true],
    });
  }

  ngOnInit(): void {
    this.loadRecentUploads();
    this.subscribeToUploadProgress();
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

    const uploadRequests: DocumentUploadRequest[] = this.selectedFiles.map(
      (file) => ({
        file,
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
      })
    );

    this.documentService.uploadDocuments(uploadRequests).subscribe({
      next: (documents) => {
        this.snackBar.open(
          `Successfully uploaded ${documents.length} document(s)`,
          'Close',
          {
            duration: 5000,
          }
        );
        this.clearForm();
        this.loadRecentUploads();
      },
      error: (error) => {
        this.snackBar.open(`Upload failed: ${error.message}`, 'Close', {
          duration: 5000,
        });
        this.isUploading = false;
        queueMicrotask(() => this.cdr.detectChanges());
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
    queueMicrotask(() => this.cdr.detectChanges());
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

  formatDate(date: Date): string {
    return new Date(date).toLocaleString();
  }
}
