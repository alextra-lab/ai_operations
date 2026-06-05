import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { UserActivity, WidgetConfig } from '../models/dashboard.models';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-user-activity-widget',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatChipsModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="user-activity-widget">
      <div class="header">
        <div class="title">
          <lucide-icon aria-hidden="true" name="users"></lucide-icon>
          <div class="text">
            <p>Recent User Activity</p>
            <small>{{ activities.length }} events</small>
          </div>
        </div>
        <mat-chip class="success-chip" *ngIf="successRate >= 0">
          {{ successRate }}% success
        </mat-chip>
      </div>

      <div class="activity-list" *ngIf="activities.length; else emptyState">
        <div
          class="activity-row"
          *ngFor="let activity of activities; trackBy: trackByUserActivity"
        >
          <div class="activity-main">
            <div class="avatar">
              <lucide-icon aria-hidden="true" name="user"></lucide-icon>
            </div>
            <div class="details">
              <div class="top-line">
                <span class="user">{{ activity.username }}</span>
                <mat-chip
                  [class.success]="activity.success"
                  [class.failure]="!activity.success"
                  >{{ activity.success ? 'Success' : 'Failed' }}
                </mat-chip>
              </div>
              <div class="action">
                <span>{{ activity.action }}</span>
                <span class="resource">{{ activity.resource }}</span>
              </div>
              <div class="meta">
                <span>{{ formatTimestamp(activity.timestamp) }}</span>
                <span class="ip">{{ activity.ip_address }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ng-template #emptyState>
        <div class="empty-state">
          <lucide-icon aria-hidden="true" name="users"></lucide-icon>
          <p>No recent activity</p>
          <small>Events will appear as users interact</small>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .user-activity-widget {
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

      .title mat-icon {
        color: var(--mat-primary-color);
      }

      .title p {
        margin: 0;
        font-weight: 600;
      }

      .title small {
        color: var(--mat-on-surface-variant-color);
      }

      .success-chip {
        background: #4caf50;
        color: white;
      }

      .activity-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        overflow-y: auto;
      }

      .activity-row {
        background: var(--mat-surface-color);
        border: 1px solid var(--mat-outline-variant-color);
        border-radius: 10px;
        padding: 10px 12px;
      }

      .activity-main {
        display: flex;
        gap: 12px;
      }

      .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: var(--mat-surface-variant-color);
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .avatar mat-icon {
        color: var(--mat-primary-color);
      }

      .details {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .top-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }

      .user {
        font-weight: 600;
      }

      .action {
        color: var(--mat-on-surface-color);
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .resource {
        color: var(--mat-on-surface-variant-color);
      }

      .meta {
        display: flex;
        gap: 8px;
        color: var(--mat-on-surface-variant-color);
        font-size: 12px;
      }

      .ip {
        font-family: monospace;
      }

      .success {
        background: #4caf50;
        color: white;
      }

      .failure {
        background: #f44336;
        color: white;
      }

      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--mat-on-surface-variant-color);
        text-align: center;
        gap: 4px;
      }

      .empty-state mat-icon {
        opacity: 0.5;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserActivityWidgetComponent {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  get activities(): UserActivity[] {
    return (this.data.user_activity || []).slice(0, 10);
  }

  get successRate(): number {
    const events = this.activities;
    if (!events.length) {
      return 0;
    }

    const success = events.filter((a) => a.success).length;
    return Math.round((success / events.length) * 100);
  }

  formatTimestamp(timestamp: Date): string {
    const now = Date.now();
    const diff = now - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  }

  trackByUserActivity(index: number, activity: UserActivity): string {
    return `${activity.user_id}-${activity.timestamp}`;
  }
}
