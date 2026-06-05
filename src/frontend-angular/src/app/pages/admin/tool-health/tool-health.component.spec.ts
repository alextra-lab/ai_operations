/**
 * Tool Health Dashboard Component Unit Tests
 */

import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';

import { LibraryLoaderService } from '../../../services/library-loader.service';
import { ToolListItem } from '../tool-management/models/tool-management.models';
import { ToolAdminService } from '../tool-management/services/tool-admin.service';
import {
  HealthSummary,
  ToolHealthCheckRecord,
} from './models/tool-health.models';
import { ToolHealthService } from './services/tool-health.service';
import { ToolHealthComponent } from './tool-health.component';

describe('ToolHealthComponent', () => {
  let component: ToolHealthComponent;
  let fixture: ComponentFixture<ToolHealthComponent>;
  let healthServiceSpy: jest.Mocked<ToolHealthService>;
  let adminServiceSpy: jest.Mocked<ToolAdminService>;
  let snackBarSpy: jest.Mocked<MatSnackBar>;
  let libraryLoaderSpy: jest.Mocked<LibraryLoaderService>;

  const mockSummary: HealthSummary = {
    total_tools: 5,
    online: 4,
    offline: 1,
    health_percentage: 80.0,
    last_check: '2025-11-24T10:00:00Z',
  };

  const mockTools: ToolListItem[] = [
    {
      id: 'uuid-1',
      tool_id: 'tool-1',
      name: 'Test Tool 1',
      description: 'A test tool',
      category: 'database',
      is_enabled: true,
      is_healthy: true,
      requires_authentication: false,
    },
    {
      id: 'uuid-2',
      tool_id: 'tool-2',
      name: 'Test Tool 2',
      description: 'Another tool',
      category: 'web_scraping',
      is_enabled: true,
      is_healthy: false,
      requires_authentication: true,
    },
    {
      id: 'uuid-3',
      tool_id: 'tool-3',
      name: 'Disabled Tool',
      description: null,
      category: 'custom',
      is_enabled: false,
      is_healthy: false,
      requires_authentication: false,
    },
  ];

  const mockHistory: ToolHealthCheckRecord[] = [
    {
      id: 'check-1',
      tool_id: 'uuid-1',
      status: 'online',
      response_time_ms: 100,
      error_message: null,
      checked_at: '2025-11-24T10:00:00Z',
    },
    {
      id: 'check-2',
      tool_id: 'uuid-1',
      status: 'online',
      response_time_ms: 120,
      error_message: null,
      checked_at: '2025-11-24T09:00:00Z',
    },
  ];

  const mockCheckResult: ToolHealthCheckRecord = {
    id: 'check-new',
    tool_id: 'uuid-1',
    status: 'online',
    response_time_ms: 80,
    error_message: null,
    checked_at: '2025-11-24T10:05:00Z',
  };

  beforeEach(async () => {
    healthServiceSpy = {
      getOverallStatus: jest.fn().mockReturnValue(of(mockSummary)),
      getToolHistory: jest.fn().mockReturnValue(of(mockHistory)),
      triggerHealthCheck: jest.fn().mockReturnValue(of(mockCheckResult)),
    } as unknown as jest.Mocked<ToolHealthService>;

    adminServiceSpy = {
      listTools: jest.fn().mockReturnValue(of(mockTools)),
    } as unknown as jest.Mocked<ToolAdminService>;

    snackBarSpy = {
      open: jest.fn(),
    } as unknown as jest.Mocked<MatSnackBar>;

    libraryLoaderSpy = {
      loadChartJS: jest.fn().mockResolvedValue(undefined),
      isLoaded: jest.fn().mockReturnValue(false),
      loadPrism: jest.fn(),
      loadKaTeX: jest.fn(),
      loadMermaid: jest.fn(),
      getLoadedLibraries: jest.fn().mockReturnValue([]),
      isLoading: jest.fn().mockReturnValue(false),
    } as unknown as jest.Mocked<LibraryLoaderService>;

    // Set up window.Chart mock
    const mockChart = jest.fn().mockImplementation(() => ({
      data: {
        labels: [] as string[],
        datasets: [{ data: [] as number[] }, { data: [] as number[] }],
      },
      update: jest.fn(),
      destroy: jest.fn(),
    }));
    (window as unknown as { Chart: typeof mockChart }).Chart = mockChart;

    await TestBed.configureTestingModule({
      imports: [
        ToolHealthComponent,
        FormsModule,
        RouterTestingModule,
        NoopAnimationsModule,
        MatButtonModule,
        MatCardModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatSelectModule,
        MatSlideToggleModule,
        MatSnackBarModule,
        MatSortModule,
        MatTableModule,
        MatTooltipModule,
      ],
      providers: [
        { provide: ToolHealthService, useValue: healthServiceSpy },
        { provide: ToolAdminService, useValue: adminServiceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolHealthComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    delete (window as unknown as { Chart?: unknown }).Chart;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should load data on init', () => {
      fixture.detectChanges();

      expect(healthServiceSpy.getOverallStatus).toHaveBeenCalled();
      expect(adminServiceSpy.listTools).toHaveBeenCalled();
    });

    it('should set summary data after load', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.summary()).toEqual(mockSummary);
    }));

    it('should set tools data after load', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.tools().length).toBe(3);
    }));

    it('should set isLoading to false after load', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.isLoading).toBe(false);
    }));
  });

  describe('error handling', () => {
    it('should set isLoading to false on error', fakeAsync(() => {
      healthServiceSpy.getOverallStatus.mockReturnValue(
        throwError(() => new Error('Network error'))
      );

      fixture.detectChanges();
      tick();

      expect(component.isLoading).toBe(false);
    }));
  });

  describe('refresh', () => {
    it('should reload data on refresh', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      healthServiceSpy.getOverallStatus.mockClear();
      adminServiceSpy.listTools.mockClear();

      component.onRefresh();
      tick();

      expect(healthServiceSpy.getOverallStatus).toHaveBeenCalled();
      expect(adminServiceSpy.listTools).toHaveBeenCalled();
    }));
  });

  describe('tool selection', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should set selected tool on selection', () => {
      const tool = component.tools()[0];
      component.onToolSelect(tool);

      expect(component.selectedTool()).toEqual(tool);
    });

    it('should load history for selected tool', fakeAsync(() => {
      const tool = component.tools()[0];
      component.onToolSelect(tool);
      tick();

      expect(healthServiceSpy.getToolHistory).toHaveBeenCalledWith(tool.id, 24);
    }));

    it('should set history data after load', fakeAsync(() => {
      const tool = component.tools()[0];
      component.onToolSelect(tool);
      tick();

      expect(component.healthHistory()).toEqual(mockHistory);
    }));
  });

  describe('time range change', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      component.onToolSelect(component.tools()[0]);
      tick();
    }));

    it('should reload history with new time range', fakeAsync(() => {
      healthServiceSpy.getToolHistory.mockClear();
      component.selectedTimeRange = 72;
      component.onTimeRangeChange();
      tick();

      expect(healthServiceSpy.getToolHistory).toHaveBeenCalledWith(
        component.tools()[0].id,
        72
      );
    }));
  });

  describe('trigger health check', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should call triggerHealthCheck service method', fakeAsync(() => {
      const tool = component.tools()[0];
      const event = new Event('click');
      component.onTriggerCheck(tool, event);

      expect(healthServiceSpy.triggerHealthCheck).toHaveBeenCalledWith(tool.id);
    }));

    it('should add tool to checking set initially', () => {
      const tool = component.tools()[0];
      expect(component.isChecking(tool.id)).toBe(false);

      component.checkingToolIds.add(tool.id);
      expect(component.isChecking(tool.id)).toBe(true);

      component.checkingToolIds.delete(tool.id);
      expect(component.isChecking(tool.id)).toBe(false);
    });
  });

  describe('status helpers', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should return "unknown" for tools with no last_health_check', () => {
      // Our mock tools don't have last_health_check set
      const tool = component.tools()[0];
      expect(component.getStatus(tool)).toBe('unknown');
    });

    it('should return "disabled" for disabled tool', () => {
      const tool = component.tools()[2];
      expect(component.getStatus(tool)).toBe('disabled');
    });

    it('should return correct icon for disabled status', () => {
      const tool = component.tools()[2];
      expect(component.getStatusIcon(tool)).toBe('power-off');
    });

    it('should return circle-help icon for unknown status', () => {
      const tool = component.tools()[0];
      expect(component.getStatusIcon(tool)).toBe('circle-help');
    });
  });

  describe('formatLastCheck', () => {
    it('should return "Never" for null timestamp', () => {
      expect(component.formatLastCheck(null)).toBe('Never');
    });

    it('should return relative time for recent timestamp', () => {
      const now = new Date();
      const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000);
      expect(component.formatLastCheck(fiveMinAgo.toISOString())).toBe(
        '5m ago'
      );
    });

    it('should return "Just now" for very recent timestamp', () => {
      const now = new Date();
      expect(component.formatLastCheck(now.toISOString())).toBe('Just now');
    });
  });

  describe('sorting', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should sort by name ascending', () => {
      component.onSort({ active: 'name', direction: 'asc' });
      const sorted = component.sortedTools();
      expect(sorted[0].name).toBe('Disabled Tool');
    });

    it('should sort by name descending', () => {
      component.onSort({ active: 'name', direction: 'desc' });
      const sorted = component.sortedTools();
      expect(sorted[0].name).toBe('Test Tool 2');
    });

    it('should reset sort when direction is empty', () => {
      component.onSort({ active: 'name', direction: '' });
      const sorted = component.sortedTools();
      expect(sorted).toEqual(component.tools());
    });
  });

  describe('getLatestCheck', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should return null when no history', () => {
      expect(component.getLatestCheck()).toBeNull();
    });

    it('should return first record when history exists', fakeAsync(() => {
      component.onToolSelect(component.tools()[0]);
      tick();

      const latest = component.getLatestCheck();
      expect(latest).toEqual(mockHistory[0]);
    }));
  });

  describe('auto-refresh', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should not auto-refresh when disabled', fakeAsync(() => {
      healthServiceSpy.getOverallStatus.mockClear();
      component.autoRefreshEnabled = false;
      component.onAutoRefreshChange();
      tick(35000);

      expect(healthServiceSpy.getOverallStatus).not.toHaveBeenCalled();
    }));
  });

  describe('ngOnDestroy', () => {
    it('should clean up subscriptions', () => {
      fixture.detectChanges();
      const destroySpy = jest.spyOn(component['destroy$'], 'next');

      component.ngOnDestroy();

      expect(destroySpy).toHaveBeenCalled();
    });
  });
});
