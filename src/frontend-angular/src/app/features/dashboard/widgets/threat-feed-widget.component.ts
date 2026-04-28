import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';

import {
  ThreatEvent,
  ThreatSeverity,
  ThreatStatus,
  WidgetConfig,
} from '../models/dashboard.models';

@Component({
  selector: 'app-threat-feed-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="threat-feed-widget">
      <!-- Loading State -->
      <div *ngIf="isLoading" class="loading-container">
        <mat-spinner diameter="30"></mat-spinner>
        <p>Loading threat events...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="hasError" class="error-container">
        <mat-icon color="warn">error</mat-icon>
        <p>Failed to load threat events</p>
        <button mat-button (click)="refresh()">Retry</button>
      </div>

      <!-- Content -->
      <div *ngIf="!isLoading && !hasError" class="threat-feed-content">
        <!-- Summary Stats -->
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-value">{{ getTotalThreats() }}</span>
            <span class="stat-label">Total Threats</span>
          </div>
          <div class="stat-item">
            <span class="stat-value critical">{{ getCriticalThreats() }}</span>
            <span class="stat-label">Critical</span>
          </div>
          <div class="stat-item">
            <span class="stat-value high">{{ getHighThreats() }}</span>
            <span class="stat-label">High</span>
          </div>
          <div class="stat-item">
            <span class="stat-value medium">{{ getMediumThreats() }}</span>
            <span class="stat-label">Medium</span>
          </div>
        </div>

        <!-- Threat Events List -->
        <div class="threat-events-list">
          <div
            *ngFor="let event of displayThreats; trackBy: trackByThreatId"
            class="threat-event"
            [class]="'severity-' + event.severity"
            (click)="selectThreat(event)"
          >
            <div class="threat-header">
              <div class="threat-title">
                <mat-icon [class]="'severity-' + event.severity">
                  {{ getSeverityIcon(event.severity) }}
                </mat-icon>
                <span class="title">{{ event.title }}</span>
              </div>
              <div class="threat-meta">
                <mat-chip [class]="'severity-' + event.severity">
                  {{ event.severity.toUpperCase() }}
                </mat-chip>
                <span class="timestamp">{{
                  formatTimestamp(event.timestamp)
                }}</span>
              </div>
            </div>

            <div class="threat-content">
              <p class="description">{{ event.description }}</p>
              <div class="threat-tags" *ngIf="event.tags.length > 0">
                <mat-chip *ngFor="let tag of event.tags" class="tag-chip">
                  {{ tag }}
                </mat-chip>
              </div>
            </div>

            <div class="threat-footer">
              <div class="threat-source">
                <mat-icon>source</mat-icon>
                <span>{{ event.source }}</span>
              </div>
              <div class="threat-status">
                <mat-icon [class]="'status-' + event.status">
                  {{ getStatusIcon(event.status) }}
                </mat-icon>
                <span>{{ formatStatus(event.status) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Load More Button -->
        <div class="load-more" *ngIf="hasMoreThreats">
          <button mat-button (click)="loadMore()">
            <mat-icon>expand_more</mat-icon>
            Load More
          </button>
        </div>

        <!-- Empty State -->
        <div *ngIf="threatEvents.length === 0" class="empty-state">
          <mat-icon>security</mat-icon>
          <p>No threat events detected</p>
          <small>All systems are secure</small>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .threat-feed-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      .loading-container,
      .error-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        gap: 16px;
        color: var(--mat-on-surface-variant-color);

        p {
          margin: 0;
          text-align: center;
        }
      }

      .error-container {
        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          color: var(--mat-warn-color);
        }
      }

      .threat-feed-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .summary-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(60px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
        padding: 12px;
        background: var(--mat-surface-variant-color);
        border-radius: 8px;

        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;

          .stat-value {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;

            &.critical {
              color: #f44336;
            }

            &.high {
              color: #ff9800;
            }

            &.medium {
              color: #ffc107;
            }
          }

          .stat-label {
            font-size: 12px;
            color: var(--mat-on-surface-variant-color);
          }
        }
      }

      .threat-events-list {
        flex: 1;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .threat-event {
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid;
        background: var(--mat-surface-color);
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover {
          background: var(--mat-surface-variant-color);
          transform: translateX(2px);
        }

        &.severity-critical {
          border-left-color: #f44336;
          background: rgba(244, 67, 54, 0.05);
        }

        &.severity-high {
          border-left-color: #ff9800;
          background: rgba(255, 152, 0, 0.05);
        }

        &.severity-medium {
          border-left-color: #ffc107;
          background: rgba(255, 193, 7, 0.05);
        }

        &.severity-low {
          border-left-color: #4caf50;
          background: rgba(76, 175, 80, 0.05);
        }
      }

      .threat-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;

        .threat-title {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;

          mat-icon {
            font-size: 18px;
            width: 18px;
            height: 18px;

            &.severity-critical {
              color: #f44336;
            }

            &.severity-high {
              color: #ff9800;
            }

            &.severity-medium {
              color: #ffc107;
            }

            &.severity-low {
              color: #4caf50;
            }
          }

          .title {
            font-weight: 500;
            font-size: 14px;
          }
        }

        .threat-meta {
          display: flex;
          align-items: center;
          gap: 8px;

          .timestamp {
            font-size: 12px;
            color: var(--mat-on-surface-variant-color);
          }
        }
      }

      .threat-content {
        margin-bottom: 8px;

        .description {
          margin: 0 0 8px 0;
          font-size: 13px;
          color: var(--mat-on-surface-color);
          line-height: 1.4;
        }

        .threat-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;

          .tag-chip {
            font-size: 10px;
            height: 20px;
            background: var(--mat-primary-color);
            color: var(--mat-on-primary-color);
          }
        }
      }

      .threat-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: var(--mat-on-surface-variant-color);

        .threat-source,
        .threat-status {
          display: flex;
          align-items: center;
          gap: 4px;

          mat-icon {
            font-size: 14px;
            width: 14px;
            height: 14px;
          }
        }

        .threat-status {
          mat-icon {
            &.status-new {
              color: #2196f3;
            }

            &.status-investigating {
              color: #ff9800;
            }

            &.status-resolved {
              color: #4caf50;
            }

            &.status-false-positive {
              color: #9e9e9e;
            }

            &.status-escalated {
              color: #f44336;
            }
          }
        }
      }

      .load-more {
        display: flex;
        justify-content: center;
        padding: 8px;
        margin-top: 8px;

        button {
          color: var(--mat-primary-color);
        }
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: var(--mat-on-surface-variant-color);
        text-align: center;

        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          margin-bottom: 16px;
          opacity: 0.5;
        }

        p {
          margin: 0 0 4px 0;
          font-weight: 500;
        }

        small {
          font-size: 12px;
          opacity: 0.7;
        }
      }

      @media (max-width: 768px) {
        .summary-stats {
          grid-template-columns: repeat(2, 1fr);
        }

        .threat-header {
          flex-direction: column;
          gap: 8px;

          .threat-meta {
            align-self: flex-start;
          }
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ThreatFeedWidgetComponent implements OnInit, OnDestroy {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  private readonly destroy$ = new Subject<void>();

  threatEvents: ThreatEvent[] = [];
  displayThreats: ThreatEvent[] = [];
  isLoading = false;
  hasError = false;
  hasMoreThreats = false;
  selectedThreat: ThreatEvent | null = null;

  ngOnInit(): void {
    this.loadThreatEvents();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load threat events from data
   */
  private loadThreatEvents(): void {
    this.isLoading = true;
    this.hasError = false;

    // Simulate loading delay
    setTimeout(() => {
      this.threatEvents = this.data.threat_events || [];
      this.displayThreats = this.threatEvents.slice(0, 10);
      this.hasMoreThreats = this.threatEvents.length > 10;
      this.isLoading = false;
    }, 500);
  }

  /**
   * Refresh threat events
   */
  refresh(): void {
    this.loadThreatEvents();
  }

  /**
   * Load more threats
   */
  loadMore(): void {
    const currentLength = this.displayThreats.length;
    const nextBatch = this.threatEvents.slice(
      currentLength,
      currentLength + 10
    );
    this.displayThreats = [...this.displayThreats, ...nextBatch];
    this.hasMoreThreats = this.displayThreats.length < this.threatEvents.length;
  }

  /**
   * Select threat event
   */
  selectThreat(threat: ThreatEvent): void {
    this.selectedThreat = threat;
    // In a real implementation, this would open a detailed view or emit an event
  }

  /**
   * Get total number of threats
   */
  getTotalThreats(): number {
    return this.threatEvents.length;
  }

  /**
   * Get number of critical threats
   */
  getCriticalThreats(): number {
    return this.threatEvents.filter(
      (t) => t.severity === ThreatSeverity.CRITICAL
    ).length;
  }

  /**
   * Get number of high threats
   */
  getHighThreats(): number {
    return this.threatEvents.filter((t) => t.severity === ThreatSeverity.HIGH)
      .length;
  }

  /**
   * Get number of medium threats
   */
  getMediumThreats(): number {
    return this.threatEvents.filter((t) => t.severity === ThreatSeverity.MEDIUM)
      .length;
  }

  /**
   * Get severity icon
   */
  getSeverityIcon(severity: ThreatSeverity): string {
    const iconMap: Record<ThreatSeverity, string> = {
      [ThreatSeverity.CRITICAL]: 'error',
      [ThreatSeverity.HIGH]: 'warning',
      [ThreatSeverity.MEDIUM]: 'info',
      [ThreatSeverity.LOW]: 'check_circle',
    };

    return iconMap[severity] || 'help';
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: ThreatStatus): string {
    const iconMap: Record<ThreatStatus, string> = {
      [ThreatStatus.NEW]: 'fiber_new',
      [ThreatStatus.INVESTIGATING]: 'search',
      [ThreatStatus.RESOLVED]: 'check_circle',
      [ThreatStatus.FALSE_POSITIVE]: 'cancel',
      [ThreatStatus.ESCALATED]: 'trending_up',
    };

    return iconMap[status] || 'help';
  }

  /**
   * Format status text
   */
  formatStatus(status: ThreatStatus): string {
    const statusMap: Record<ThreatStatus, string> = {
      [ThreatStatus.NEW]: 'New',
      [ThreatStatus.INVESTIGATING]: 'Investigating',
      [ThreatStatus.RESOLVED]: 'Resolved',
      [ThreatStatus.FALSE_POSITIVE]: 'False Positive',
      [ThreatStatus.ESCALATED]: 'Escalated',
    };

    return statusMap[status] || status;
  }

  /**
   * Format timestamp
   */
  formatTimestamp(timestamp: Date): string {
    const now = new Date();
    const diff = now.getTime() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) {
      return 'Just now';
    } else if (minutes < 60) {
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else {
      return `${days}d ago`;
    }
  }

  /**
   * Track by function for threat events
   */
  trackByThreatId(index: number, threat: ThreatEvent): string {
    return threat.id;
  }
}
