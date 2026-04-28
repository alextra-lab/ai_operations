import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import {
  DocumentProcessingStats,
  RecentDocument,
  WidgetConfig,
} from '../models/dashboard.models';

@Component({
  selector: 'app-document-processing-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="document-processing-widget">
      <div class="header">
        <div class="title">
          <mat-icon aria-hidden="true">description</mat-icon>
          <div>
            <p>Document Processing</p>
            <small>{{ stats?.total_documents || 0 }} total</small>
          </div>
        </div>
        <mat-chip class="queue-chip">
          Queue {{ stats?.queue_size || 0 }}
        </mat-chip>
      </div>

      <div *ngIf="stats; else emptyState" class="summary">
        <div class="summary-item">
          <span>Processing</span>
          <strong>{{ stats.processing }}</strong>
        </div>
        <div class="summary-item">
          <span>Completed</span>
          <strong>{{ stats.completed }}</strong>
        </div>
        <div class="summary-item">
          <span>Failed</span>
          <strong>{{ stats.failed }}</strong>
        </div>
        <div class="summary-item">
          <span>Avg Time</span>
          <strong
            >{{ stats.average_processing_time | number: '1.1-1' }}s</strong
          >
        </div>
      </div>

      <div *ngIf="stats?.processing" class="progress">
        <mat-progress-bar
          [value]="progressPercent"
          class="usage-medium"
        ></mat-progress-bar>
        <span class="bar-label"
          >{{ progressPercent | number: '1.0-0' }}% done</span
        >
      </div>

      <div class="recent" *ngIf="recentDocuments.length">
        <h4>Recent Documents</h4>
        <div
          class="doc-row"
          *ngFor="let doc of recentDocuments; trackBy: trackByDoc"
        >
          <div class="doc-main">
            <mat-icon aria-hidden="true">article</mat-icon>
            <div class="doc-text">
              <span class="name">{{ doc.filename }}</span>
              <small>
                {{ formatTimestamp(doc.uploaded_at) }}
                • {{ doc.uploaded_by }}
              </small>
            </div>
          </div>
          <mat-chip [class]="statusClass(doc.status)">
            {{ doc.status.toUpperCase() }}
          </mat-chip>
        </div>
      </div>

      <ng-template #emptyState>
        <div class="empty-state">
          <mat-icon aria-hidden="true">description</mat-icon>
          <p>No documents yet</p>
          <small>Upload documents to see processing status</small>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .document-processing-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .title {
        display: flex;
        gap: 10px;
        align-items: center;
      }

      .title p {
        margin: 0;
        font-weight: 600;
      }

      .title small {
        color: var(--mat-on-surface-variant-color);
      }

      .queue-chip {
        background: var(--mat-primary-color);
        color: var(--mat-on-primary-color);
      }

      .summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
      }

      .summary-item {
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--mat-surface-color);
        border: 1px solid var(--mat-outline-variant-color);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .progress {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .bar-label {
        font-weight: 600;
      }

      mat-progress-bar.usage-medium ::ng-deep .mat-progress-bar-fill::after {
        background-color: #4caf50;
      }

      .recent {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .recent h4 {
        margin: 0;
        font-weight: 600;
      }

      .doc-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid var(--mat-outline-variant-color);
        background: var(--mat-surface-color);
      }

      .doc-main {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .doc-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .name {
        font-weight: 600;
      }

      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--mat-on-surface-variant-color);
        gap: 4px;
      }

      .empty-state mat-icon {
        opacity: 0.5;
      }

      .status-processing {
        background: #fbc02d;
        color: black;
      }

      .status-completed {
        background: #4caf50;
        color: white;
      }

      .status-failed {
        background: #d32f2f;
        color: white;
      }

      .status-queued {
        background: #90a4ae;
        color: white;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DocumentProcessingWidgetComponent {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  get stats(): DocumentProcessingStats | null {
    return this.data.document_processing || null;
  }

  get recentDocuments(): RecentDocument[] {
    return (this.stats?.recent_documents || []).slice(0, 5);
  }

  get progressPercent(): number {
    if (!this.stats) return 0;
    const total = this.stats.total_documents || 1;
    return Math.min((this.stats.completed / total) * 100, 100);
  }

  formatTimestamp(timestamp: Date): string {
    const now = Date.now();
    const diff = now - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return new Date(timestamp).toLocaleDateString();
  }

  statusClass(status: string): string {
    const map: Record<string, string> = {
      processing: 'status-processing',
      completed: 'status-completed',
      failed: 'status-failed',
      queued: 'status-queued',
    };
    return map[status] || 'status-queued';
  }

  trackByDoc(index: number, doc: RecentDocument): string {
    return doc.id;
  }
}
