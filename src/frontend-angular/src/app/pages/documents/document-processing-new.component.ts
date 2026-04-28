import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subscription, interval } from 'rxjs';

import {
  DocumentProcessingStatus,
  DocumentState,
} from '../../api/models/document.models';
import { DocumentService } from '../../api/services/document.service';

@Component({
  selector: 'app-document-processing',
  standalone: true,
  template: `
    <div class="document-processing-page">
      <div class="processing-header">
        <h1>Document Processing Status</h1>
        <p>
          Monitor the processing status of your uploaded documents in real-time.
        </p>
      </div>

      <!-- Processing Overview -->
      <mat-card class="overview-card">
        <mat-card-header>
          <mat-card-title>Processing Overview</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-number">{{ getStatusCount('processing') }}</div>
              <div class="stat-label">Processing</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ getStatusCount('completed') }}</div>
              <div class="stat-label">Completed</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ getStatusCount('failed') }}</div>
              <div class="stat-label">Failed</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ getStatusCount('queued') }}</div>
              <div class="stat-label">Queued</div>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Processing Queue -->
      <mat-card class="queue-card">
        <mat-card-header>
          <mat-card-title>Processing Queue</mat-card-title>
          <div class="header-actions">
            <button
              mat-icon-button
              (click)="refreshStatus()"
              matTooltip="Refresh"
            >
              <mat-icon>refresh</mat-icon>
            </button>
            <button
              mat-icon-button
              (click)="toggleAutoRefresh()"
              [matTooltip]="
                autoRefresh ? 'Stop Auto-refresh' : 'Start Auto-refresh'
              "
            >
              <mat-icon>{{ autoRefresh ? 'pause' : 'play_arrow' }}</mat-icon>
            </button>
          </div>
        </mat-card-header>

        <mat-card-content>
          <!-- Loading State -->
          <div *ngIf="isLoading" class="loading-state">
            <mat-spinner diameter="40"></mat-spinner>
            <p>Loading processing status...</p>
          </div>

          <!-- Empty State -->
          <div
            *ngIf="!isLoading && (processingStatuses?.length ?? 0) === 0"
            class="empty-state"
          >
            <mat-icon>hourglass_empty</mat-icon>
            <h3>No documents processing</h3>
            <p>
              All documents have been processed or no documents are currently in
              the queue.
            </p>
          </div>

          <!-- Processing List -->
          <div
            *ngIf="!isLoading && (processingStatuses?.length ?? 0) > 0"
            class="processing-list"
          >
            <div
              *ngFor="let status of processingStatuses"
              class="processing-item"
            >
              <div class="item-header">
                <div class="document-info">
                  <mat-icon class="document-icon">{{
                    getStatusIcon(status.status)
                  }}</mat-icon>
                  <div class="document-details">
                    <h4 class="document-name">{{ status.document_id }}</h4>
                    <p class="current-step">{{ status.current_step }}</p>
                  </div>
                </div>

                <div class="status-info">
                  <span class="status-badge" [class]="status.status">
                    {{ status.status }}
                  </span>
                  <span class="progress-text">
                    {{ status.progress }}% ({{ status.current_step }}
                    {{ status.total_steps }})
                  </span>
                </div>
              </div>

              <!-- Progress Bar -->
              <mat-progress-bar
                [value]="status.progress"
                [mode]="
                  status.status === 'processing'
                    ? 'determinate'
                    : 'indeterminate'
                "
                [class]="status.status"
              >
              </mat-progress-bar>

              <!-- Processing Logs -->
              <div
                *ngIf="status.processing_logs?.length > 0"
                class="processing-logs"
              >
                <h5>Processing Logs</h5>
                <div class="log-list">
                  <div
                    *ngFor="let log of status.processing_logs"
                    class="log-item"
                    [class]="log.level"
                  >
                    <span class="log-time">{{
                      formatTime(log.timestamp)
                    }}</span>
                    <span class="log-step">{{ log.step }}</span>
                    <span class="log-message">{{ log.message }}</span>
                  </div>
                </div>
              </div>

              <!-- Error Message -->
              <div *ngIf="status.error_message" class="error-message">
                <mat-icon>error</mat-icon>
                <span>{{ status.error_message }}</span>
              </div>

              <!-- Actions -->
              <div class="item-actions">
                <button
                  mat-button
                  (click)="reprocessDocument(status.document_id)"
                  [disabled]="status.status === 'processing'"
                >
                  <mat-icon>refresh</mat-icon>
                  Reprocess
                </button>

                <button
                  mat-button
                  (click)="viewDocument(status.document_id)"
                  [disabled]="status.status !== 'completed'"
                >
                  <mat-icon>visibility</mat-icon>
                  View Document
                </button>
              </div>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Recent Processing History -->
      <mat-card class="history-card">
        <mat-card-header>
          <mat-card-title>Recent Processing History</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <div *ngIf="(recentHistory?.length ?? 0) === 0" class="no-history">
            <mat-icon>history</mat-icon>
            <p>No recent processing history</p>
          </div>

          <div *ngFor="let item of recentHistory" class="history-item">
            <mat-icon class="status-icon" [class]="item.status">{{
              getStatusIcon(item.status)
            }}</mat-icon>
            <div class="history-info">
              <span class="document-name">{{ item.document_id }}</span>
              <span class="history-time">{{
                formatTime(item.completed_at || item.started_at)
              }}</span>
            </div>
            <div class="history-status" [class]="item.status">
              {{ item.status }}
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .document-processing-page {
        padding: 24px;
        max-width: 1200px;
        margin: 0 auto;
      }

      .processing-header {
        margin-bottom: 24px;
      }

      .processing-header h1 {
        margin: 0 0 8px 0;
        color: #1976d2;
      }

      .processing-header p {
        margin: 0;
        color: #666;
      }

      .overview-card,
      .queue-card,
      .history-card {
        margin-bottom: 24px;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
      }

      .stat-item {
        text-align: center;
        padding: 16px;
        border-radius: 8px;
        background-color: #f5f5f5;
      }

      .stat-number {
        font-size: 32px;
        font-weight: bold;
        color: #1976d2;
        margin-bottom: 4px;
      }

      .stat-label {
        font-size: 14px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .header-actions {
        display: flex;
        gap: 8px;
      }

      .loading-state,
      .empty-state,
      .no-history {
        text-align: center;
        padding: 48px 24px;
        color: #666;
      }

      .loading-state mat-spinner {
        margin: 0 auto 16px;
      }

      .empty-state mat-icon,
      .no-history mat-icon {
        font-size: 64px;
        width: 64px;
        height: 64px;
        margin-bottom: 16px;
        color: #ccc;
      }

      .processing-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .processing-item {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        background-color: #fafafa;
      }

      .item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .document-info {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .document-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
        color: #1976d2;
      }

      .document-details h4 {
        margin: 0 0 4px 0;
        font-size: 16px;
        font-weight: 500;
      }

      .current-step {
        margin: 0;
        font-size: 12px;
        color: #666;
      }

      .status-info {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 4px;
      }

      .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
      }

      .status-badge.processing {
        background-color: #fff3e0;
        color: #f57c00;
      }

      .status-badge.completed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .status-badge.failed {
        background-color: #ffebee;
        color: #c62828;
      }

      .status-badge.queued {
        background-color: #e3f2fd;
        color: #1976d2;
      }

      .progress-text {
        font-size: 12px;
        color: #666;
      }

      mat-progress-bar {
        margin: 8px 0;
      }

      .processing-logs {
        margin-top: 16px;
      }

      .processing-logs h5 {
        margin: 0 0 8px 0;
        font-size: 14px;
        font-weight: 500;
      }

      .log-list {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        background-color: #f9f9f9;
      }

      .log-item {
        display: flex;
        gap: 8px;
        padding: 8px 12px;
        border-bottom: 1px solid #e0e0e0;
        font-size: 12px;
      }

      .log-item:last-child {
        border-bottom: none;
      }

      .log-item.info {
        color: #1976d2;
      }

      .log-item.warning {
        color: #f57c00;
      }

      .log-item.error {
        color: #c62828;
      }

      .log-time {
        min-width: 60px;
        color: #666;
      }

      .log-step {
        min-width: 80px;
        font-weight: 500;
      }

      .log-message {
        flex: 1;
      }

      .error-message {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 12px;
        padding: 8px 12px;
        background-color: #ffebee;
        border-radius: 4px;
        color: #c62828;
        font-size: 14px;
      }

      .item-actions {
        display: flex;
        gap: 8px;
        margin-top: 16px;
      }

      .history-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid #e0e0e0;
      }

      .history-item:last-child {
        border-bottom: none;
      }

      .status-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }

      .status-icon.completed {
        color: #2e7d32;
      }

      .status-icon.failed {
        color: #c62828;
      }

      .status-icon.processing {
        color: #f57c00;
      }

      .history-info {
        flex: 1;
        display: flex;
        flex-direction: column;
      }

      .document-name {
        font-weight: 500;
        font-size: 14px;
      }

      .history-time {
        font-size: 12px;
        color: #666;
      }

      .history-status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
      }

      .history-status.completed {
        background-color: #e8f5e8;
        color: #2e7d32;
      }

      .history-status.failed {
        background-color: #ffebee;
        color: #c62828;
      }

      .history-status.processing {
        background-color: #fff3e0;
        color: #f57c00;
      }
    `,
  ],
})
export class DocumentProcessingComponent implements OnInit, OnDestroy {
  processingStatuses: DocumentProcessingStatus[] = [];
  recentHistory: any[] = [];
  isLoading = false;
  autoRefresh = false;
  private refreshSubscription?: Subscription;

  constructor(
    private documentService: DocumentService,
    private snackBar: MatSnackBar
  ) { }

  ngOnInit(): void {
    this.loadProcessingStatus();
  }

  ngOnDestroy(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  loadProcessingStatus(): void {
    this.isLoading = true;
    this.documentService.getAllProcessingStatuses().subscribe({
      next: (statuses) => {
        this.processingStatuses = statuses;
        this.isLoading = false;
      },
      error: (error) => {
        this.snackBar.open(
          `Failed to load processing status: ${error.message}`,
          'Close',
          {
            duration: 5000,
          }
        );
        this.isLoading = false;
      },
    });
  }

  refreshStatus(): void {
    this.loadProcessingStatus();
  }

  toggleAutoRefresh(): void {
    this.autoRefresh = !this.autoRefresh;

    if (this.autoRefresh) {
      this.refreshSubscription = interval(5000).subscribe(() => {
        this.loadProcessingStatus();
      });
    } else if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  getStatusCount(status: DocumentState): number {
    return this.processingStatuses.filter((s) => s.status === status).length;
  }

  getStatusIcon(status: DocumentState): string {
    switch (status) {
      case DocumentState.PROCESSED:
        return 'check_circle';
      case 'processing':
        return 'hourglass_empty';
      case 'failed':
        return 'error';
      case 'queued':
        return 'schedule';
      case DocumentState.PENDING:
        return 'upload';
      default:
        return 'description';
    }
  }

  reprocessDocument(documentId: string): void {
    this.documentService.reprocessDocument(documentId).subscribe({
      next: () => {
        this.snackBar.open('Document reprocessing started', 'Close', {
          duration: 3000,
        });
        this.loadProcessingStatus();
      },
      error: (error) => {
        this.snackBar.open(
          `Failed to reprocess document: ${error.message}`,
          'Close',
          {
            duration: 5000,
          }
        );
      },
    });
  }

  viewDocument(documentId: string): void {
    // TODO: Implement document viewing
  }

  formatTime(date: Date): string {
    return new Date(date).toLocaleTimeString();
  }
}
