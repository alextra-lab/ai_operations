import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';

import {
  ServiceStatus,
  SystemHealth,
  SystemStatus,
  WidgetConfig,
} from '../models/dashboard.models';

@Component({
  selector: 'app-system-health-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="system-health-widget">
      <div *ngIf="isLoading" class="loading-container">
        <mat-spinner diameter="24"></mat-spinner>
      </div>

      <div *ngIf="!isLoading" class="health-content">
        <!-- Compact header -->
        <div class="status-header" [class]="'status-' + systemHealth?.status">
          <mat-icon>{{ getStatusIcon(systemHealth?.status) }}</mat-icon>
          <span class="status-text">{{
            systemHealth?.status?.toUpperCase()
          }}</span>
          <span class="uptime">{{ formatUptime(systemHealth?.uptime) }}</span>
        </div>

        <!-- Services grid -->
        <div class="services-grid">
          <div
            *ngFor="
              let svc of systemHealth?.services || [];
              trackBy: trackBySvc
            "
            class="service-row"
            [class]="'svc-' + svc.status"
            [matTooltip]="svc.name + ': ' + svc.status"
          >
            <mat-icon class="svc-icon">{{ getSvcIcon(svc.status) }}</mat-icon>
            <span class="svc-name">{{ svc.name }}</span>
            <span class="svc-status">{{ svc.status }}</span>
          </div>
        </div>

        <!-- Last check footer -->
        <div class="footer">
          <mat-icon>schedule</mat-icon>
          <span>{{ formatLastCheck(systemHealth?.last_check) }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .system-health-widget {
        height: 100%;
        display: flex;
        flex-direction: column;
      }

      .loading-container {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .health-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .status-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 600;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
        }

        .status-text {
          flex: 1;
        }

        .uptime {
          font-size: 12px;
          font-weight: 400;
          opacity: 0.8;
        }

        &.status-healthy {
          background: rgba(76, 175, 80, 0.15);
          color: #2e7d32;
        }

        &.status-warning {
          background: rgba(255, 193, 7, 0.15);
          color: #f57f17;
        }

        &.status-critical,
        &.status-unhealthy {
          background: rgba(244, 67, 54, 0.15);
          color: #c62828;
        }

        &.status-offline {
          background: rgba(158, 158, 158, 0.15);
          color: #616161;
        }
      }

      .services-grid {
        flex: 1;
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
        overflow-y: auto;
      }

      .service-row {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 12px;
        border-left: 3px solid;

        .svc-icon {
          font-size: 14px;
          width: 14px;
          height: 14px;
        }

        .svc-name {
          flex: 1;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .svc-status {
          font-size: 10px;
          text-transform: uppercase;
          opacity: 0.7;
        }

        &.svc-healthy {
          background: rgba(76, 175, 80, 0.08);
          border-left-color: #4caf50;
          color: #2e7d32;
        }

        &.svc-warning {
          background: rgba(255, 193, 7, 0.08);
          border-left-color: #ffc107;
          color: #f57f17;
        }

        &.svc-critical,
        &.svc-unhealthy {
          background: rgba(244, 67, 54, 0.08);
          border-left-color: #f44336;
          color: #c62828;
        }

        &.svc-offline,
        &.svc-unreachable,
        &.svc-unknown {
          background: rgba(158, 158, 158, 0.08);
          border-left-color: #9e9e9e;
          color: #616161;
        }
      }

      .footer {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        color: var(--mat-on-surface-variant-color);
        padding-top: 4px;
        border-top: 1px solid var(--mat-outline-variant-color);

        mat-icon {
          font-size: 12px;
          width: 12px;
          height: 12px;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SystemHealthWidgetComponent
  implements OnInit, OnChanges, OnDestroy
{
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() data: any = {};
  @Input() config: WidgetConfig = {
    autoRefresh: true,
    showHeader: true,
    showControls: true,
  };

  private readonly destroy$ = new Subject<void>();

  systemHealth: SystemHealth | null = null;
  isLoading = false;

  ngOnInit(): void {
    this.loadSystemHealth();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && !changes['data'].firstChange) {
      this.updateSystemHealth();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadSystemHealth(): void {
    this.isLoading = true;
    setTimeout(() => {
      this.systemHealth =
        this.data.system_health || this.getDefaultSystemHealth();
      this.isLoading = false;
      this.cdr.markForCheck();
    }, 300);
  }

  private updateSystemHealth(): void {
    if (this.data?.system_health) {
      this.systemHealth = this.data.system_health;
      this.cdr.markForCheck();
    }
  }

  getStatusIcon(status?: SystemStatus): string {
    const icons: Record<SystemStatus, string> = {
      [SystemStatus.HEALTHY]: 'check_circle',
      [SystemStatus.WARNING]: 'warning',
      [SystemStatus.CRITICAL]: 'error',
      [SystemStatus.OFFLINE]: 'cloud_off',
    };
    return icons[status || SystemStatus.OFFLINE] || 'help';
  }

  getSvcIcon(status: SystemStatus): string {
    return this.getStatusIcon(status);
  }

  formatUptime(uptime?: number): string {
    if (!uptime) return '0s';
    const d = Math.floor(uptime / 86400);
    const h = Math.floor((uptime % 86400) / 3600);
    const m = Math.floor((uptime % 3600) / 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  formatLastCheck(lastCheck?: Date): string {
    if (!lastCheck) return 'Never';
    const diff = Date.now() - new Date(lastCheck).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ago`;
  }

  trackBySvc(_i: number, svc: ServiceStatus): string {
    return svc.name;
  }

  private getDefaultSystemHealth(): SystemHealth {
    return {
      status: SystemStatus.HEALTHY,
      uptime: 0,
      cpu_usage: 0,
      memory_usage: 0,
      disk_usage: 0,
      network_status: {
        latency: 0,
        bandwidth: 0,
        packet_loss: 0,
        status: 'up',
      },
      services: [],
      last_check: new Date(),
    };
  }
}
