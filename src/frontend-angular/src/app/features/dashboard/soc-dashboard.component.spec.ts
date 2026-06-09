import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { expect, jest } from '@jest/globals';
import { of } from 'rxjs';

import { WebSocketConnectionState } from '../../api/services/websocket.service';
import { UserProfile, UserRole } from '../../core/auth/auth.models';
import { AuthService } from '../../core/auth/auth.service';
import {
  DashboardState,
  DashboardWidget,
  RealTimeData,
  SystemStatus,
  WidgetType,
} from './models/dashboard.models';
import { DashboardConfigService } from './services/dashboard-config.service';
import { RealTimeDataService } from './services/real-time-data.service';
import { SocDashboardComponent } from './soc-dashboard.component';

describe('SocDashboardComponent', () => {
  let component: SocDashboardComponent;
  let fixture: ComponentFixture<SocDashboardComponent>;
  let mockRealTimeDataService: Partial<RealTimeDataService>;
  let mockDashboardConfigService: Partial<DashboardConfigService>;
  let mockAuthService: Partial<AuthService>;
  let mockSnackBar: MatSnackBar;
  let snackBarSpy: ReturnType<typeof jest.spyOn>;

  const mockUser: UserProfile = {
    id: 'test-user',
    username: 'testuser',
    full_name: 'Test User',
    roles: ['admin' as UserRole],
    expires_at: undefined,
  };

  const mockRealTimeData: RealTimeData = {
    threat_events: [],
    system_health: {
      status: SystemStatus.HEALTHY,
      uptime: 1000,
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
  };

  const mockDashboardState: DashboardState = {
    currentLayout: 'default',
    widgets: [],
    isFullscreen: false,
    isEditing: false,
    selectedWidget: undefined,
    realTimeData: mockRealTimeData,
    lastUpdate: new Date(),
  };

  const mockWidget: DashboardWidget = {
    id: 'test-widget-1',
    type: WidgetType.SYSTEM_HEALTH,
    title: 'Test Widget',
    size: { width: 2, height: 2 },
    position: { x: 0, y: 0, z: 0 },
    data: {},
    config: { autoRefresh: true, showHeader: true, showControls: true },
    isVisible: true,
    isCollapsed: false,
    lastUpdated: new Date(),
  };

  beforeEach(async () => {
    mockRealTimeDataService = {
      getConnectionState: jest.fn(() => of(WebSocketConnectionState.CONNECTED)),
      getRealTimeData: jest.fn(() => of(mockRealTimeData)),
      requestDataUpdate: jest.fn(),
    };

    mockDashboardConfigService = {
      getDashboardState: jest.fn(() =>
        of({ ...mockDashboardState, widgets: [mockWidget] })
      ),
      getCurrentWidgets: jest.fn(() => of([mockWidget])),
      resetToDefault: jest.fn(() => of(true)),
      setEditingMode: jest.fn(),
      setFullscreenMode: jest.fn(),
      selectWidget: jest.fn(),
      addWidget: jest.fn(() => of(mockWidget)),
      removeWidget: jest.fn(() => of(true)),
      toggleWidgetCollapsed: jest.fn(() => of(true)),
      updateWidget: jest.fn(() => of(true)),
      updateWidgetPosition: jest.fn(() => of(true)),
    };

    mockAuthService = {
      getCurrentUser: jest.fn(() => of(mockUser)),
      hasAnyRole: jest.fn(() => true),
    };

    await TestBed.configureTestingModule({
      imports: [SocDashboardComponent, NoopAnimationsModule],
      providers: [
        {
          provide: RealTimeDataService,
          useValue: mockRealTimeDataService,
        },
        {
          provide: DashboardConfigService,
          useValue: mockDashboardConfigService,
        },
        { provide: AuthService, useValue: mockAuthService },
        MatSnackBar,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SocDashboardComponent);
    component = fixture.componentInstance;
    mockSnackBar = TestBed.inject(MatSnackBar);
    snackBarSpy = jest.spyOn(mockSnackBar, 'open').mockImplementation(() => {
      return {} as any;
    });
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
    if (snackBarSpy) {
      snackBarSpy.mockRestore();
    }
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize dashboard on ngOnInit', () => {
    component.ngOnInit();
    expect(mockAuthService.getCurrentUser).toHaveBeenCalled();
    expect(mockDashboardConfigService.getDashboardState).toHaveBeenCalled();
  });

  it('should setup subscriptions on ngOnInit', () => {
    component.ngOnInit();
    expect(mockRealTimeDataService.getConnectionState).toHaveBeenCalled();
    expect(mockRealTimeDataService.getRealTimeData).toHaveBeenCalled();
  });

  it('should toggle editing mode', () => {
    component.isEditing = false;
    component.toggleEditing();
    expect(component.isEditing).toBe(true);
    expect(mockDashboardConfigService.setEditingMode).toHaveBeenCalledWith(
      true
    );

    component.toggleEditing();
    expect(component.isEditing).toBe(false);
    expect(mockDashboardConfigService.setEditingMode).toHaveBeenCalledWith(
      false
    );
  });

  it('should toggle fullscreen mode', () => {
    component.isFullscreen = false;
    component.toggleFullscreen();
    expect(component.isFullscreen).toBe(true);
    expect(mockDashboardConfigService.setFullscreenMode).toHaveBeenCalledWith(
      true
    );
  });

  it('should add widget', () => {
    component.addWidget();
    expect(mockDashboardConfigService.addWidget).toHaveBeenCalled();
  });

  it('should remove widget', () => {
    component.removeWidget('test-widget-1');
    expect(mockDashboardConfigService.removeWidget).toHaveBeenCalledWith(
      'test-widget-1'
    );
  });

  it('should select widget', () => {
    component.selectWidget('test-widget-1');
    expect(component.selectedWidget).toBe('test-widget-1');
    expect(mockDashboardConfigService.selectWidget).toHaveBeenCalledWith(
      'test-widget-1'
    );
  });

  it('should toggle widget collapsed state', () => {
    component.toggleWidgetCollapsed('test-widget-1');
    expect(
      mockDashboardConfigService.toggleWidgetCollapsed
    ).toHaveBeenCalledWith('test-widget-1');
  });

  it('should refresh widget', () => {
    // Get the snackBar from the component's private field
    const componentSnackBar = (component as any).snackBar;
    const spy = jest.spyOn(componentSnackBar, 'open');

    component.refreshWidget('test-widget-1');
    expect(mockRealTimeDataService.requestDataUpdate).toHaveBeenCalledWith(
      'all'
    );
    expect(spy).toHaveBeenCalledWith('Widget refreshed', 'Close', {
      duration: 2000,
    });
  });

  it('should configure widget', () => {
    const componentSnackBar = (component as any).snackBar;
    const spy = jest.spyOn(componentSnackBar, 'open');

    component.configureWidget('test-widget-1');
    expect(spy).toHaveBeenCalledWith(
      'Widget configuration not implemented yet',
      'Close',
      { duration: 2000 }
    );
  });

  it('should reset layout', () => {
    component.resetLayout();
    expect(mockAuthService.getCurrentUser).toHaveBeenCalled();
  });

  it('should save layout', () => {
    const componentSnackBar = (component as any).snackBar;
    const spy = jest.spyOn(componentSnackBar, 'open');

    component.saveLayout();
    expect(spy).toHaveBeenCalledWith('Layout saved', 'Close', {
      duration: 2000,
    });
  });

  it('should export layout', () => {
    const componentSnackBar = (component as any).snackBar;
    const spy = jest.spyOn(componentSnackBar, 'open');

    component.exportLayout();
    expect(spy).toHaveBeenCalledWith(
      'Layout export not implemented yet',
      'Close',
      { duration: 2000 }
    );
  });

  it('should import layout', () => {
    const componentSnackBar = (component as any).snackBar;
    const spy = jest.spyOn(componentSnackBar, 'open');

    component.importLayout();
    expect(spy).toHaveBeenCalledWith(
      'Layout import not implemented yet',
      'Close',
      { duration: 2000 }
    );
  });

  it('should get correct connection icon', () => {
    component.connectionState = WebSocketConnectionState.CONNECTED;
    expect(component.getConnectionIcon()).toBe('wifi');

    component.connectionState = WebSocketConnectionState.CONNECTING;
    expect(component.getConnectionIcon()).toBe('wifi');

    component.connectionState = WebSocketConnectionState.DISCONNECTED;
    expect(component.getConnectionIcon()).toBe('wifi-off');
  });

  it('should get correct connection text', () => {
    component.connectionState = WebSocketConnectionState.CONNECTED;
    expect(component.getConnectionText()).toBe('Connected');

    component.connectionState = WebSocketConnectionState.CONNECTING;
    expect(component.getConnectionText()).toBe('Connecting...');

    component.connectionState = WebSocketConnectionState.DISCONNECTED;
    expect(component.getConnectionText()).toBe('Disconnected');
  });

  it('should get correct widget icon', () => {
    expect(component.getWidgetIcon(WidgetType.SYSTEM_HEALTH)).toBe('activity');
    expect(component.getWidgetIcon(WidgetType.THREAT_FEED)).toBe('shield');
    expect(component.getWidgetIcon(WidgetType.QUERY_STATS)).toBe(
      'chart-column'
    );
  });

  it('should track widgets by id', () => {
    expect(component.trackByWidgetId(0, mockWidget)).toBe('test-widget-1');
  });

  it('should cleanup on destroy', () => {
    const destroySpy = jest.spyOn(component['destroy$'], 'next');
    const completeSpy = jest.spyOn(component['destroy$'], 'complete');

    component.ngOnDestroy();

    expect(destroySpy).toHaveBeenCalled();
    expect(completeSpy).toHaveBeenCalled();
  });
});
