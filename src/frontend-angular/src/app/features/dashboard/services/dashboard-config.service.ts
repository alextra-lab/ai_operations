import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';

import {
  DashboardConfig,
  DashboardLayout,
  DashboardState,
  DashboardWidget,
  GridConfig,
  WidgetPosition,
  WidgetSize,
  WidgetType,
} from '../models/dashboard.models';

@Injectable({
  providedIn: 'root',
})
export class DashboardConfigService {
  private readonly STORAGE_KEY = 'aiop_dashboard_config';
  private readonly LAYOUTS_KEY = 'aiop_dashboard_layouts';

  private readonly dashboardState$ = new BehaviorSubject<DashboardState>(
    this.getInitialState()
  );
  private readonly layouts$ = new BehaviorSubject<DashboardLayout[]>([]);
  private readonly config$ = new BehaviorSubject<DashboardConfig>(
    this.getDefaultConfig()
  );

  constructor() {
    this.loadConfigurations();
  }

  /**
   * Get current dashboard state
   */
  getDashboardState(): Observable<DashboardState> {
    return this.dashboardState$.asObservable();
  }

  /**
   * Get available layouts
   */
  getLayouts(): Observable<DashboardLayout[]> {
    return this.layouts$.asObservable();
  }

  /**
   * Get dashboard configuration
   */
  getConfig(): Observable<DashboardConfig> {
    return this.config$.asObservable();
  }

  /**
   * Get current layout
   */
  getCurrentLayout(): Observable<DashboardLayout | null> {
    return this.dashboardState$.pipe(
      map((state) => {
        const layouts = this.layouts$.value;
        return (
          layouts.find((layout) => layout.id === state.currentLayout) || null
        );
      })
    );
  }

  /**
   * Get widgets for current layout
   */
  getCurrentWidgets(): Observable<DashboardWidget[]> {
    return this.dashboardState$.pipe(map((state) => state.widgets));
  }

  /**
   * Set current layout
   */
  setCurrentLayout(layoutId: string): void {
    const layouts = this.layouts$.value;
    const layout = layouts.find((l) => l.id === layoutId);

    if (layout) {
      const currentState = this.dashboardState$.value;
      this.dashboardState$.next({
        ...currentState,
        currentLayout: layoutId,
        widgets: [...layout.widgets],
      });

      this.saveDashboardState();
    }
  }

  /**
   * Create new layout
   */
  createLayout(
    name: string,
    description?: string
  ): Observable<DashboardLayout> {
    const newLayout: DashboardLayout = {
      id: this.generateId(),
      name,
      description,
      widgets: [],
      gridConfig: this.getDefaultGridConfig(),
      isDefault: false,
      isPublic: false,
      createdBy: 'current_user', // In real app, get from auth service
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    const layouts = [...this.layouts$.value, newLayout];
    this.layouts$.next(layouts);
    this.saveLayouts();

    return of(newLayout);
  }

  /**
   * Update layout
   */
  updateLayout(
    layoutId: string,
    updates: Partial<DashboardLayout>
  ): Observable<boolean> {
    const layouts = this.layouts$.value;
    const index = layouts.findIndex((l) => l.id === layoutId);

    if (index !== -1) {
      layouts[index] = {
        ...layouts[index],
        ...updates,
        updatedAt: new Date(),
      };

      this.layouts$.next(layouts);
      this.saveLayouts();
      return of(true);
    }

    return of(false);
  }

  /**
   * Delete layout
   */
  deleteLayout(layoutId: string): Observable<boolean> {
    const layouts = this.layouts$.value;
    const filteredLayouts = layouts.filter((l) => l.id !== layoutId);

    if (filteredLayouts.length !== layouts.length) {
      this.layouts$.next(filteredLayouts);
      this.saveLayouts();
      return of(true);
    }

    return of(false);
  }

  /**
   * Add widget to current layout
   */
  addWidget(
    widget: Omit<DashboardWidget, 'id' | 'position' | 'lastUpdated'>
  ): Observable<DashboardWidget> {
    const newWidget: DashboardWidget = {
      ...widget,
      id: this.generateId(),
      position: this.calculateNextPosition(),
      lastUpdated: new Date(),
    };

    const currentState = this.dashboardState$.value;
    const updatedWidgets = [...currentState.widgets, newWidget];

    this.dashboardState$.next({
      ...currentState,
      widgets: updatedWidgets,
    });

    this.saveDashboardState();
    return of(newWidget);
  }

  /**
   * Update widget
   */
  updateWidget(
    widgetId: string,
    updates: Partial<DashboardWidget>
  ): Observable<boolean> {
    const currentState = this.dashboardState$.value;
    const widgetIndex = currentState.widgets.findIndex(
      (w) => w.id === widgetId
    );

    if (widgetIndex !== -1) {
      const updatedWidgets = [...currentState.widgets];
      updatedWidgets[widgetIndex] = {
        ...updatedWidgets[widgetIndex],
        ...updates,
        lastUpdated: new Date(),
      };

      this.dashboardState$.next({
        ...currentState,
        widgets: updatedWidgets,
      });

      this.saveDashboardState();
      return of(true);
    }

    return of(false);
  }

  /**
   * Remove widget
   */
  removeWidget(widgetId: string): Observable<boolean> {
    const currentState = this.dashboardState$.value;
    const filteredWidgets = currentState.widgets.filter(
      (w) => w.id !== widgetId
    );

    this.dashboardState$.next({
      ...currentState,
      widgets: filteredWidgets,
    });

    this.saveDashboardState();
    return of(true);
  }

  /**
   * Update widget position
   */
  updateWidgetPosition(
    widgetId: string,
    position: WidgetPosition
  ): Observable<boolean> {
    return this.updateWidget(widgetId, { position });
  }

  /**
   * Update widget size
   */
  updateWidgetSize(widgetId: string, size: WidgetSize): Observable<boolean> {
    return this.updateWidget(widgetId, { size });
  }

  /**
   * Toggle widget visibility
   */
  toggleWidgetVisibility(widgetId: string): Observable<boolean> {
    const currentState = this.dashboardState$.value;
    const widget = currentState.widgets.find((w) => w.id === widgetId);

    if (widget) {
      return this.updateWidget(widgetId, { isVisible: !widget.isVisible });
    }

    return of(false);
  }

  /**
   * Toggle widget collapsed state
   */
  toggleWidgetCollapsed(widgetId: string): Observable<boolean> {
    const currentState = this.dashboardState$.value;
    const widget = currentState.widgets.find((w) => w.id === widgetId);

    if (widget) {
      return this.updateWidget(widgetId, { isCollapsed: !widget.isCollapsed });
    }

    return of(false);
  }

  /**
   * Set editing mode
   */
  setEditingMode(isEditing: boolean): void {
    const currentState = this.dashboardState$.value;
    this.dashboardState$.next({
      ...currentState,
      isEditing: isEditing,
    });
  }

  /**
   * Set fullscreen mode
   */
  setFullscreenMode(isFullscreen: boolean): void {
    const currentState = this.dashboardState$.value;
    this.dashboardState$.next({
      ...currentState,
      isFullscreen: isFullscreen,
    });
  }

  /**
   * Select widget
   */
  selectWidget(widgetId: string | undefined): void {
    const currentState = this.dashboardState$.value;
    this.dashboardState$.next({
      ...currentState,
      selectedWidget: widgetId,
    });
  }

  /**
   * Get default widgets for role - 6 uniform widgets for 3x2 glass-table grid
   */
  getDefaultWidgetsForRole(_role: string): DashboardWidget[] {
    // All roles get same 6-widget dashboard layout for glass-table view
    const widgets: Omit<DashboardWidget, 'id' | 'position' | 'lastUpdated'>[] =
      [
        {
          type: WidgetType.SYSTEM_HEALTH,
          title: 'System Health',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
        {
          type: WidgetType.THREAT_FEED,
          title: 'Threat Feed',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
        {
          type: WidgetType.SECURITY_ALERTS,
          title: 'Security Alerts',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
        {
          type: WidgetType.QUERY_STATS,
          title: 'Query Statistics',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
        {
          type: WidgetType.USER_ACTIVITY,
          title: 'User Activity',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
        {
          type: WidgetType.PERFORMANCE_METRICS,
          title: 'Performance Metrics',
          size: { width: 1, height: 1 },
          data: {},
          config: { autoRefresh: true, showHeader: true, showControls: true },
          isVisible: true,
          isCollapsed: false,
        },
      ];

    return widgets.map((widget, index) => ({
      ...widget,
      id: this.generateId(),
      position: { x: index % 3, y: Math.floor(index / 3), z: 0 },
      lastUpdated: new Date(),
    }));
  }

  /**
   * Reset to default layout
   */
  resetToDefault(role: string): Observable<boolean> {
    const defaultWidgets = this.getDefaultWidgetsForRole(role);
    const currentState = this.dashboardState$.value;

    this.dashboardState$.next({
      ...currentState,
      widgets: defaultWidgets,
    });

    this.saveDashboardState();
    return of(true);
  }

  /**
   * Load configurations from storage
   */
  private loadConfigurations(): void {
    // Load dashboard state
    const savedState = localStorage.getItem(this.STORAGE_KEY);
    if (savedState) {
      try {
        const state = JSON.parse(savedState);
        this.dashboardState$.next({
          ...this.getInitialState(),
          ...state,
          lastUpdate: new Date(state.lastUpdate),
        });
      } catch (error) {
        console.error('Error loading dashboard state:', error);
      }
    }

    // Load layouts
    const savedLayouts = localStorage.getItem(this.LAYOUTS_KEY);
    if (savedLayouts) {
      try {
        const layouts = JSON.parse(savedLayouts);
        this.layouts$.next(
          layouts.map((layout: any) => ({
            ...layout,
            createdAt: new Date(layout.createdAt),
            updatedAt: new Date(layout.updatedAt),
          }))
        );
      } catch (error) {
        console.error('Error loading layouts:', error);
      }
    }

    // Load config
    const savedConfig = localStorage.getItem('aiop_dashboard_settings');
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig);
        this.config$.next({ ...this.getDefaultConfig(), ...config });
      } catch (error) {
        console.error('Error loading config:', error);
      }
    }
  }

  /**
   * Save dashboard state
   */
  private saveDashboardState(): void {
    const state = this.dashboardState$.value;
    localStorage.setItem(
      this.STORAGE_KEY,
      JSON.stringify({
        ...state,
        lastUpdate: new Date(),
      })
    );
  }

  /**
   * Save layouts
   */
  private saveLayouts(): void {
    const layouts = this.layouts$.value;
    localStorage.setItem(this.LAYOUTS_KEY, JSON.stringify(layouts));
  }

  /**
   * Get initial dashboard state
   */
  private getInitialState(): DashboardState {
    return {
      currentLayout: 'default',
      widgets: [],
      isFullscreen: false,
      isEditing: false,
      selectedWidget: undefined,
      realTimeData: {
        threat_events: [],
        system_health: {
          status: 'healthy' as any,
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
        },
        query_stats: {
          total_queries: 0,
          successful_queries: 0,
          failed_queries: 0,
          average_response_time: 0,
          queries_per_hour: 0,
          top_queries: [],
          recent_queries: [],
        },
        user_activity: [],
        security_alerts: [],
        performance_metrics: {
          response_time: 0,
          throughput: 0,
          error_rate: 0,
          cpu_usage: 0,
          memory_usage: 0,
          disk_io: 0,
          network_io: 0,
          active_connections: 0,
          queue_length: 0,
        },
        document_processing: {
          total_documents: 0,
          processing: 0,
          completed: 0,
          failed: 0,
          average_processing_time: 0,
          queue_size: 0,
          recent_documents: [],
        },
        timestamp: new Date(),
      },
      lastUpdate: new Date(),
    };
  }

  /**
   * Get default configuration
   */
  private getDefaultConfig(): DashboardConfig {
    return {
      defaultLayout: 'default',
      autoRefresh: true,
      refreshInterval: 30000,
      theme: 'auto',
      notifications: {
        enabled: true,
        sound: true,
        desktop: true,
        email: false,
        severity_threshold: 'medium' as any,
      },
      widgets: [],
    };
  }

  /**
   * Get default grid configuration
   */
  private getDefaultGridConfig(): GridConfig {
    return {
      columns: 12,
      rows: 8,
      cellSize: 50,
      gap: 16,
      autoFit: true,
    };
  }

  /**
   * Calculate next available position for widget
   */
  private calculateNextPosition(): WidgetPosition {
    const currentWidgets = this.dashboardState$.value.widgets;
    const gridConfig = this.getDefaultGridConfig();

    // Simple algorithm to find next available position
    for (let y = 0; y < gridConfig.rows; y++) {
      for (let x = 0; x < gridConfig.columns; x++) {
        const isOccupied = currentWidgets.some(
          (widget) => widget.position.x === x && widget.position.y === y
        );

        if (!isOccupied) {
          return { x, y, z: 0 };
        }
      }
    }

    // If no position found, place at end
    return { x: 0, y: currentWidgets.length, z: 0 };
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
  }
}
