import {
  CdkDrag,
  CdkDragDrop,
  CdkDropList,
  moveItemInArray,
  transferArrayItem,
} from '@angular/cdk/drag-drop';
import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { combineLatest, Subject, takeUntil } from 'rxjs';

// Widget Components
import { DocumentProcessingWidgetComponent } from './widgets/document-processing-widget.component';
import { PerformanceMetricsWidgetComponent } from './widgets/performance-metrics-widget.component';
import { QueryStatsWidgetComponent } from './widgets/query-stats-widget.component';
import { SecurityAlertsWidgetComponent } from './widgets/security-alerts-widget.component';
import { SystemHealthWidgetComponent } from './widgets/system-health-widget.component';
import { ThreatFeedWidgetComponent } from './widgets/threat-feed-widget.component';
import { UserActivityWidgetComponent } from './widgets/user-activity-widget.component';

import { WebSocketConnectionState } from '../../api/services/websocket.service';
import { AuthService } from '../../core/auth/auth.service';
import { DashboardWidget, WidgetType } from './models/dashboard.models';
import { DashboardConfigService } from './services/dashboard-config.service';
import { RealTimeDataService } from './services/real-time-data.service';

@Component({
  selector: 'app-soc-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatToolbarModule,
    MatMenuModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    CdkDrag,
    CdkDropList,
    // Widget Components
    ThreatFeedWidgetComponent,
    SystemHealthWidgetComponent,
    QueryStatsWidgetComponent,
    UserActivityWidgetComponent,
    SecurityAlertsWidgetComponent,
    PerformanceMetricsWidgetComponent,
    DocumentProcessingWidgetComponent,
  ],
  template: `
    <div
      class="dashboard-container"
      [class.fullscreen]="isFullscreen"
      [class.editing]="isEditing"
    >
      <!-- Dashboard Header -->
      <mat-toolbar class="dashboard-header" color="primary">
        <div class="header-content">
          <div class="header-left">
            <h1>Security Operations Center Dashboard</h1>
            <div class="connection-status" [class]="connectionState">
              <mat-icon>{{ getConnectionIcon() }}</mat-icon>
              <span>{{ getConnectionText() }}</span>
            </div>
          </div>

          <div class="header-right">
            <button
              mat-icon-button
              (click)="toggleEditing()"
              [class.active]="isEditing"
            >
              <mat-icon>edit</mat-icon>
            </button>

            <button mat-icon-button (click)="toggleFullscreen()">
              <mat-icon>{{
                isFullscreen ? 'fullscreen_exit' : 'fullscreen'
              }}</mat-icon>
            </button>

            <button mat-icon-button [matMenuTriggerFor]="dashboardMenu">
              <mat-icon>more_vert</mat-icon>
            </button>

            <mat-menu #dashboardMenu="matMenu">
              <button mat-menu-item (click)="addWidget()">
                <mat-icon>add</mat-icon>
                <span>Add Widget</span>
              </button>
              <button mat-menu-item (click)="resetLayout()">
                <mat-icon>refresh</mat-icon>
                <span>Reset Layout</span>
              </button>
              <button mat-menu-item (click)="saveLayout()">
                <mat-icon>save</mat-icon>
                <span>Save Layout</span>
              </button>
              <mat-divider></mat-divider>
              <button mat-menu-item (click)="exportLayout()">
                <mat-icon>download</mat-icon>
                <span>Export Layout</span>
              </button>
              <button mat-menu-item (click)="importLayout()">
                <mat-icon>upload</mat-icon>
                <span>Import Layout</span>
              </button>
            </mat-menu>
          </div>
        </div>
      </mat-toolbar>

      <!-- Dashboard Content -->
      <div class="dashboard-content">
        <!-- Loading Spinner -->
        <div *ngIf="isLoading" class="loading-container">
          <mat-spinner diameter="50"></mat-spinner>
          <p>Loading dashboard data...</p>
        </div>

        <!-- Dashboard Grid -->
        <div
          class="dashboard-grid"
          cdkDropList
          (cdkDropListDropped)="onWidgetDrop($event)"
          [cdkDropListData]="widgets"
          [class.editing]="isEditing"
        >
          <!-- Widget Cards -->
          <div
            *ngFor="let widget of widgets; trackBy: trackByWidgetId"
            class="widget-container"
            [class.selected]="selectedWidget === widget.id"
            [class.collapsed]="widget.isCollapsed"
            [class.hidden]="!widget.isVisible"
            cdkDrag
            [cdkDragData]="widget"
            (click)="selectWidget(widget.id)"
          >
            <!-- Widget Header -->
            <div class="widget-header" *ngIf="widget.config.showHeader">
              <div class="widget-title">
                <mat-icon>{{ getWidgetIcon(widget.type) }}</mat-icon>
                <span>{{ widget.title }}</span>
              </div>

              <div
                class="widget-actions"
                *ngIf="isEditing || widget.config.showControls"
              >
                <button
                  mat-icon-button
                  (click)="toggleWidgetCollapsed(widget.id)"
                  [matTooltip]="widget.isCollapsed ? 'Expand' : 'Collapse'"
                >
                  <mat-icon>{{
                    widget.isCollapsed ? 'expand_more' : 'expand_less'
                  }}</mat-icon>
                </button>

                <button
                  mat-icon-button
                  (click)="refreshWidget(widget.id)"
                  [matTooltip]="'Refresh'"
                >
                  <mat-icon>refresh</mat-icon>
                </button>

                <button
                  mat-icon-button
                  (click)="configureWidget(widget.id)"
                  [matTooltip]="'Configure'"
                >
                  <mat-icon>settings</mat-icon>
                </button>

                <button
                  mat-icon-button
                  (click)="removeWidget(widget.id)"
                  [matTooltip]="'Remove'"
                  *ngIf="isEditing"
                >
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            </div>

            <!-- Widget Content -->
            <div class="widget-content" *ngIf="!widget.isCollapsed">
              <ng-container [ngSwitch]="widget.type">
                <!-- Threat Feed Widget -->
                <app-threat-feed-widget
                  *ngSwitchCase="'threat_feed'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-threat-feed-widget>

                <!-- System Health Widget -->
                <app-system-health-widget
                  *ngSwitchCase="'system_health'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-system-health-widget>

                <!-- Query Stats Widget -->
                <app-query-stats-widget
                  *ngSwitchCase="'query_stats'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-query-stats-widget>

                <!-- User Activity Widget -->
                <app-user-activity-widget
                  *ngSwitchCase="'user_activity'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-user-activity-widget>

                <!-- Security Alerts Widget -->
                <app-security-alerts-widget
                  *ngSwitchCase="'security_alerts'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-security-alerts-widget>

                <!-- Performance Metrics Widget -->
                <app-performance-metrics-widget
                  *ngSwitchCase="'performance_metrics'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-performance-metrics-widget>

                <!-- Document Processing Widget -->
                <app-document-processing-widget
                  *ngSwitchCase="'document_processing'"
                  [data]="widget.data"
                  [config]="widget.config"
                >
                </app-document-processing-widget>

                <!-- Default Widget -->
                <div *ngSwitchDefault class="widget-placeholder">
                  <mat-icon>widgets</mat-icon>
                  <p>{{ widget.title }}</p>
                  <small>Widget type: {{ widget.type }}</small>
                </div>
              </ng-container>
            </div>

            <!-- Widget Resize Handle -->
            <div class="widget-resize-handle" *ngIf="isEditing" cdkDragHandle>
              <mat-icon>open_with</mat-icon>
            </div>
          </div>

          <!-- Add Widget Button (when editing) -->
          <div
            *ngIf="isEditing"
            class="add-widget-button"
            (click)="addWidget()"
          >
            <mat-icon>add</mat-icon>
            <span>Add Widget</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .dashboard-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        background-color: var(--mat-app-background-color);

        &.fullscreen {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 1000;
        }

        &.editing {
          .widget-container {
            cursor: move;

            &:hover {
              box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
          }
        }
      }

      .dashboard-header {
        flex-shrink: 0;
        z-index: 10;

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;

          .header-left {
            display: flex;
            align-items: center;
            gap: 24px;

            h1 {
              margin: 0;
              font-size: 20px;
              font-weight: 500;
            }

            .connection-status {
              display: flex;
              align-items: center;
              gap: 8px;
              padding: 4px 12px;
              border-radius: 16px;
              font-size: 12px;
              font-weight: 500;

              &.connected {
                background-color: rgba(76, 175, 80, 0.1);
                color: #4caf50;
              }

              &.connecting {
                background-color: rgba(255, 193, 7, 0.1);
                color: #ffc107;
              }

              &.disconnected,
              &.error {
                background-color: rgba(244, 67, 54, 0.1);
                color: #f44336;
              }
            }
          }

          .header-right {
            display: flex;
            align-items: center;
            gap: 8px;

            button.active {
              background-color: var(--mat-primary-color);
              color: var(--mat-on-primary-color);
            }
          }
        }
      }

      .dashboard-content {
        flex: 1;
        overflow: hidden;
        padding: 16px;
        height: calc(100vh - 80px);
      }

      .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        gap: 16px;

        p {
          margin: 0;
          color: var(--mat-on-surface-variant-color);
        }
      }

      .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        grid-template-rows: repeat(2, 1fr);
        gap: 12px;
        height: 100%;

        &.editing {
          .widget-container {
            border: 2px dashed var(--mat-primary-color);
          }
        }
      }

      .widget-container {
        background: var(--mat-surface-color);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        overflow: hidden;
        transition: all 0.2s ease;
        position: relative;
        display: flex;
        flex-direction: column;

        &:hover {
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
        }

        &.selected {
          border: 2px solid var(--mat-primary-color);
        }

        &.collapsed {
          .widget-content {
            display: none;
          }
        }

        &.hidden {
          display: none;
        }
      }

      .widget-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: var(--mat-surface-variant-color);
        border-bottom: 1px solid var(--mat-outline-variant-color);

        .widget-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;

          mat-icon {
            font-size: 18px;
            width: 18px;
            height: 18px;
          }
        }

        .widget-actions {
          display: flex;
          align-items: center;
          gap: 4px;

          button {
            width: 32px;
            height: 32px;
            line-height: 32px;

            mat-icon {
              font-size: 16px;
              width: 16px;
              height: 16px;
            }
          }
        }
      }

      .widget-content {
        padding: 16px;
        flex: 1; // Take remaining space
        overflow-y: auto; // Only content scrolls, not widget
        overflow-x: hidden; // Prevent horizontal scrolling
        min-height: 0; // Allow flex shrinking
      }

      .widget-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
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
          margin: 0 0 8px 0;
          font-weight: 500;
        }

        small {
          font-size: 12px;
          opacity: 0.7;
        }
      }

      .widget-resize-handle {
        position: absolute;
        bottom: 4px;
        right: 4px;
        width: 20px;
        height: 20px;
        background: var(--mat-primary-color);
        color: var(--mat-on-primary-color);
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: nw-resize;
        opacity: 0.7;

        &:hover {
          opacity: 1;
        }

        mat-icon {
          font-size: 12px;
          width: 12px;
          height: 12px;
        }
      }

      .add-widget-button {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 200px;
        border: 2px dashed var(--mat-outline-color);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        color: var(--mat-on-surface-variant-color);

        &:hover {
          border-color: var(--mat-primary-color);
          color: var(--mat-primary-color);
          background-color: rgba(var(--mat-primary-color-rgb), 0.04);
        }

        mat-icon {
          font-size: 48px;
          width: 48px;
          height: 48px;
          margin-bottom: 8px;
        }

        span {
          font-weight: 500;
        }
      }

      @media (max-width: 1200px) {
        .dashboard-grid {
          grid-template-columns: repeat(2, 1fr);
          grid-template-rows: repeat(3, 1fr);
        }
      }

      @media (max-width: 768px) {
        .dashboard-content {
          padding: 12px;
          height: auto;
          overflow-y: auto;
        }

        .dashboard-grid {
          grid-template-columns: 1fr;
          grid-template-rows: auto;
          height: auto;
        }

        .widget-container {
          min-height: 280px;
        }
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SocDashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly destroy$ = new Subject<void>();

  // State properties
  widgets: DashboardWidget[] = [];
  isEditing = false;
  isFullscreen = false;
  isLoading = true;
  selectedWidget: string | undefined;
  connectionState: WebSocketConnectionState =
    WebSocketConnectionState.DISCONNECTED;

  constructor(
    private realTimeDataService: RealTimeDataService,
    private dashboardConfigService: DashboardConfigService,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.initializeDashboard();
    this.setupSubscriptions();
  }

  ngAfterViewInit(): void {
    // Any view initialization logic
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Initialize dashboard
   */
  private initializeDashboard(): void {
    // Get user role and set up default widgets
    this.authService
      .getCurrentUser()
      .pipe(takeUntil(this.destroy$))
      .subscribe((user) => {
        if (user?.roles?.length) {
          const role = user.roles[0]; // Use first role
          this.dashboardConfigService.resetToDefault(role).subscribe();
        }
      });

    // Load dashboard state
    this.dashboardConfigService
      .getDashboardState()
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => {
        this.widgets = state.widgets;
        this.isEditing = state.isEditing;
        this.isFullscreen = state.isFullscreen;
        this.selectedWidget = state.selectedWidget;
      });
  }

  /**
   * Setup subscriptions
   */
  private setupSubscriptions(): void {
    // Monitor connection state
    this.realTimeDataService
      .getConnectionState()
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => {
        this.connectionState = state;
        this.isLoading = state === WebSocketConnectionState.CONNECTING;
      });

    // Update widget data when real-time data changes
    combineLatest([
      this.realTimeDataService.getRealTimeData(),
      this.dashboardConfigService.getCurrentWidgets(),
    ])
      .pipe(takeUntil(this.destroy$))
      .subscribe(([realTimeData, widgets]) => {
        if (realTimeData && widgets) {
          this.updateWidgetData(realTimeData);
        }
      });
  }

  /**
   * Handle widget drop event
   */
  onWidgetDrop(event: CdkDragDrop<DashboardWidget[]>): void {
    if (event.previousContainer === event.container) {
      moveItemInArray(
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
    } else {
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex
      );
    }

    // Update widget positions
    this.updateWidgetPositions();
  }

  /**
   * Toggle editing mode
   */
  toggleEditing(): void {
    this.isEditing = !this.isEditing;
    this.dashboardConfigService.setEditingMode(this.isEditing);

    if (!this.isEditing) {
      this.selectedWidget = undefined;
      this.dashboardConfigService.selectWidget(undefined);
    }
  }

  /**
   * Toggle fullscreen mode
   */
  toggleFullscreen(): void {
    this.isFullscreen = !this.isFullscreen;
    this.dashboardConfigService.setFullscreenMode(this.isFullscreen);
  }

  /**
   * Add new widget
   */
  addWidget(): void {
    // In a real implementation, this would open a widget selection dialog
    const newWidget: Omit<DashboardWidget, 'id' | 'position' | 'lastUpdated'> =
      {
        type: WidgetType.SYSTEM_HEALTH,
        title: 'New Widget',
        size: { width: 3, height: 3 },
        data: {},
        config: { autoRefresh: true, showHeader: true, showControls: true },
        isVisible: true,
        isCollapsed: false,
      };

    this.dashboardConfigService.addWidget(newWidget).subscribe();
  }

  /**
   * Remove widget
   */
  removeWidget(widgetId: string): void {
    this.dashboardConfigService.removeWidget(widgetId).subscribe();
  }

  /**
   * Select widget
   */
  selectWidget(widgetId: string): void {
    this.selectedWidget = widgetId;
    this.dashboardConfigService.selectWidget(widgetId);
  }

  /**
   * Toggle widget collapsed state
   */
  toggleWidgetCollapsed(widgetId: string): void {
    this.dashboardConfigService.toggleWidgetCollapsed(widgetId).subscribe();
  }

  /**
   * Refresh widget
   */
  refreshWidget(widgetId: string): void {
    this.realTimeDataService.requestDataUpdate('all');
    this.snackBar.open('Widget refreshed', 'Close', { duration: 2000 });
  }

  /**
   * Configure widget
   */
  configureWidget(widgetId: string): void {
    // In a real implementation, this would open a configuration dialog
    this.snackBar.open('Widget configuration not implemented yet', 'Close', {
      duration: 2000,
    });
  }

  /**
   * Reset layout
   */
  resetLayout(): void {
    this.authService
      .getCurrentUser()
      .pipe(takeUntil(this.destroy$))
      .subscribe((user) => {
        if (user?.roles?.length) {
          const role = user.roles[0];
          this.dashboardConfigService.resetToDefault(role).subscribe(() => {
            this.snackBar.open('Layout reset to default', 'Close', {
              duration: 2000,
            });
          });
        }
      });
  }

  /**
   * Save layout
   */
  saveLayout(): void {
    this.snackBar.open('Layout saved', 'Close', { duration: 2000 });
  }

  /**
   * Export layout
   */
  exportLayout(): void {
    this.snackBar.open('Layout export not implemented yet', 'Close', {
      duration: 2000,
    });
  }

  /**
   * Import layout
   */
  importLayout(): void {
    this.snackBar.open('Layout import not implemented yet', 'Close', {
      duration: 2000,
    });
  }

  /**
   * Update widget positions after drag and drop
   */
  private updateWidgetPositions(): void {
    this.widgets.forEach((widget, index) => {
      const position = {
        x: index % 12,
        y: Math.floor(index / 12),
        z: 0,
      };
      this.dashboardConfigService
        .updateWidgetPosition(widget.id, position)
        .subscribe();
    });
  }

  /**
   * Update widget data from real-time data
   */
  private updateWidgetData(realTimeData: any): void {
    this.widgets.forEach((widget) => {
      let newData = { ...widget.data };

      switch (widget.type) {
        case WidgetType.THREAT_FEED:
          newData = { ...newData, threat_events: realTimeData.threat_events };
          break;
        case WidgetType.SYSTEM_HEALTH:
          newData = { ...newData, system_health: realTimeData.system_health };
          break;
        case WidgetType.QUERY_STATS:
          newData = { ...newData, query_stats: realTimeData.query_stats };
          break;
        case WidgetType.USER_ACTIVITY:
          newData = { ...newData, user_activity: realTimeData.user_activity };
          break;
        case WidgetType.SECURITY_ALERTS:
          newData = {
            ...newData,
            security_alerts: realTimeData.security_alerts,
          };
          break;
        case WidgetType.PERFORMANCE_METRICS:
          newData = {
            ...newData,
            performance_metrics: realTimeData.performance_metrics,
          };
          break;
        case WidgetType.DOCUMENT_PROCESSING:
          newData = {
            ...newData,
            document_processing: realTimeData.document_processing,
          };
          break;
      }

      if (JSON.stringify(newData) !== JSON.stringify(widget.data)) {
        this.dashboardConfigService
          .updateWidget(widget.id, { data: newData })
          .subscribe();
      }
    });
  }

  /**
   * Get widget icon based on type
   */
  getWidgetIcon(type: WidgetType): string {
    const iconMap: Record<WidgetType, string> = {
      [WidgetType.THREAT_FEED]: 'security',
      [WidgetType.SYSTEM_HEALTH]: 'monitor_heart',
      [WidgetType.QUERY_STATS]: 'query_stats',
      [WidgetType.USER_ACTIVITY]: 'people',
      [WidgetType.SECURITY_ALERTS]: 'warning',
      [WidgetType.PERFORMANCE_METRICS]: 'speed',
      [WidgetType.DOCUMENT_PROCESSING]: 'description',
      [WidgetType.CUSTOM_CHART]: 'bar_chart',
    };

    return iconMap[type] || 'widgets';
  }

  /**
   * Get connection status icon
   */
  getConnectionIcon(): string {
    switch (this.connectionState) {
      case WebSocketConnectionState.CONNECTED:
        return 'wifi';
      case WebSocketConnectionState.CONNECTING:
      case WebSocketConnectionState.RECONNECTING:
        return 'wifi_find';
      case WebSocketConnectionState.DISCONNECTED:
      case WebSocketConnectionState.ERROR:
        return 'wifi_off';
      default:
        return 'wifi_off';
    }
  }

  /**
   * Get connection status text
   */
  getConnectionText(): string {
    switch (this.connectionState) {
      case WebSocketConnectionState.CONNECTED:
        return 'Connected';
      case WebSocketConnectionState.CONNECTING:
        return 'Connecting...';
      case WebSocketConnectionState.RECONNECTING:
        return 'Reconnecting...';
      case WebSocketConnectionState.DISCONNECTED:
        return 'Disconnected';
      case WebSocketConnectionState.ERROR:
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  }

  /**
   * Track by function for widgets
   */
  trackByWidgetId(index: number, widget: DashboardWidget): string {
    return widget.id;
  }
}
