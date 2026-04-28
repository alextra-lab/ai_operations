import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  SecurityAlert,
  ThreatSeverity,
  WidgetConfig,
} from '../models/dashboard.models';

@Component({
  selector: 'app-security-alerts-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="security-alerts-widget">
      <div class="header">
        <div class="title">
          <mat-icon aria-hidden="true">warning</mat-icon>
          <div>
            <p>Security Alerts</p>
            <small>{{ alerts.length }} active</small>
          </div>
        </div>
        <div class="severity-pills">
          <mat-chip class="sev critical"
            >Critical {{ count('critical') }}</mat-chip
          >
          <mat-chip class="sev high">High {{ count('high') }}</mat-chip>
          <mat-chip class="sev medium">Med {{ count('medium') }}</mat-chip>
          <mat-chip class="sev low">Low {{ count('low') }}</mat-chip>
        </div>
      </div>

      <div class="alerts-list" *ngIf="alerts.length; else emptyState">
        <div
          class="alert-row"
          *ngFor="let alert of alerts; trackBy: trackByAlert"
        >
          <div class="alert-main">
            <mat-icon [class]="'sev-' + alert.severity">
              {{ severityIcon(alert.severity) }}
            </mat-icon>
            <div class="details">
              <div class="top-line">
                <span class="title-text">{{ alert.title }}</span>
                <mat-chip [class]="'sev-chip ' + alert.severity">
                  {{ alert.severity.toUpperCase() }}
                </mat-chip>
              </div>
              <p class="desc">{{ alert.description }}</p>
              <div class="meta">
                <span>{{ alert.source }}</span>
                <span>{{ formatTimestamp(alert.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ng-template #emptyState>
        <div class="empty-state">
          <mat-icon aria-hidden="true">shield</mat-icon>
          <p>No alerts</p>
          <small>System will surface alerts here</small>
        </div>
      </ng-template>
    </div>
  `,
  styles: [
    `
      .security-alerts-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .header {
        display: flex;
        justify-content: space-between;
        gap: 12px;
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

      .severity-pills {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }

      .sev {
        color: white;
      }

      .critical {
        background: #d32f2f;
      }

      .high {
        background: #f57c00;
      }

      .medium {
        background: #fbc02d;
        color: black;
      }

      .low {
        background: #388e3c;
      }

      .alerts-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        overflow-y: auto;
      }

      .alert-row {
        border: 1px solid var(--mat-outline-variant-color);
        border-radius: 10px;
        padding: 10px 12px;
        background: var(--mat-surface-color);
      }

      .alert-main {
        display: flex;
        gap: 12px;
      }

      .alert-main mat-icon {
        margin-top: 4px;
      }

      .sev-critical {
        color: #d32f2f;
      }

      .sev-high {
        color: #f57c00;
      }

      .sev-medium {
        color: #fbc02d;
      }

      .sev-low {
        color: #388e3c;
      }

      .details {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .top-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }

      .title-text {
        font-weight: 600;
      }

      .desc {
        margin: 0;
        color: var(--mat-on-surface-color);
      }

      .meta {
        display: flex;
        gap: 10px;
        color: var(--mat-on-surface-variant-color);
        font-size: 12px;
      }

      .sev-chip {
        color: white;
      }

      .sev-chip.medium {
        color: black;
      }

      .empty-state {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        color: var(--mat-on-surface-variant-color);
      }

      .empty-state mat-icon {
        opacity: 0.5;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SecurityAlertsWidgetComponent {
  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  get alerts(): SecurityAlert[] {
    return (this.data.security_alerts || []).slice(0, 8);
  }

  count(severity: ThreatSeverity | string): number {
    return this.alerts.filter((a) => a.severity === severity).length;
  }

  severityIcon(severity: ThreatSeverity): string {
    const map: Record<ThreatSeverity, string> = {
      critical: 'error',
      high: 'warning',
      medium: 'info',
      low: 'check_circle',
    };
    return map[severity] || 'shield';
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

  trackByAlert(index: number, alert: SecurityAlert): string {
    return alert.id;
  }
}
