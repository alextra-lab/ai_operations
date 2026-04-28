/**
 * Tool Analytics Component Tests
 *
 * Unit tests for T6-F3 ToolAnalyticsComponent.
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
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';

import { ToolAnalyticsService } from '../../../api/services/tool-analytics.service';
import { LibraryLoaderService } from '../../../services/library-loader.service';
import { ToolAdminService } from '../tool-management/services/tool-admin.service';
import {
  CenterUsage,
  DateRangePreset,
  ToolUsageSummary,
} from './models/tool-analytics.models';
import { ToolAnalyticsComponent } from './tool-analytics.component';

describe('ToolAnalyticsComponent', () => {
  let component: ToolAnalyticsComponent;
  let fixture: ComponentFixture<ToolAnalyticsComponent>;
  let analyticsServiceSpy: jest.Mocked<ToolAnalyticsService>;
  let toolAdminServiceSpy: jest.Mocked<ToolAdminService>;
  let snackBarSpy: jest.Mocked<MatSnackBar>;
  let libraryLoaderSpy: jest.Mocked<LibraryLoaderService>;

  const mockUsageSummary: ToolUsageSummary[] = [
    {
      tool_id: 'tool-1',
      tool_name: 'Test Tool 1',
      total_calls: 100,
      successful_calls: 95,
      success_rate: 95.0,
      avg_duration_ms: 250,
      total_cost: 0.5,
    },
    {
      tool_id: 'tool-2',
      tool_name: 'Test Tool 2',
      total_calls: 50,
      successful_calls: 48,
      success_rate: 96.0,
      avg_duration_ms: 180,
      total_cost: 0.25,
    },
  ];

  const mockCenterUsage: CenterUsage[] = [
    { center_id: 'center-a', total_calls: 75, total_cost: 0.35 },
    { center_id: 'center-b', total_calls: 75, total_cost: 0.4 },
  ];

  const mockTools = [
    { id: 'uuid-1', name: 'Test Tool 1', tool_id: 'tool-1', is_enabled: true },
    { id: 'uuid-2', name: 'Test Tool 2', tool_id: 'tool-2', is_enabled: true },
  ];

  beforeEach(async () => {
    analyticsServiceSpy = {
      getUsageSummaryByDays: jest.fn().mockReturnValue(of(mockUsageSummary)),
      getUsageByCenter: jest.fn().mockReturnValue(of(mockCenterUsage)),
      getUsageSummary: jest.fn().mockReturnValue(of(mockUsageSummary)),
    } as unknown as jest.Mocked<ToolAnalyticsService>;

    toolAdminServiceSpy = {
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

    await TestBed.configureTestingModule({
      imports: [
        ToolAnalyticsComponent,
        FormsModule,
        RouterTestingModule,
        MatButtonModule,
        MatCardModule,
        MatIconModule,
        MatMenuModule,
        MatProgressSpinnerModule,
        MatSelectModule,
        MatSnackBarModule,
        MatTabsModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: ToolAnalyticsService, useValue: analyticsServiceSpy },
        { provide: ToolAdminService, useValue: toolAdminServiceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolAnalyticsComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should load data on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(analyticsServiceSpy.getUsageSummaryByDays).toHaveBeenCalled();
      expect(analyticsServiceSpy.getUsageByCenter).toHaveBeenCalled();
      expect(toolAdminServiceSpy.listTools).toHaveBeenCalled();
    }));

    it('should set loading to false after data loads', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.isLoading).toBe(false);
    }));

    it('should calculate aggregates from usage summary', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const aggregates = component.aggregates();
      expect(aggregates).toBeTruthy();
      expect(aggregates!.total_invocations).toBe(150);
      expect(aggregates!.total_cost).toBe(0.75);
    }));

    it('should enrich usage summary with tool names', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const summary = component.usageSummary();
      expect(summary[0].tool_name).toBe('Test Tool 1');
      expect(summary[1].tool_name).toBe('Test Tool 2');
    }));
  });

  describe('time range selection', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should default to month time range', () => {
      expect(component.selectedTimeRange).toBe(DateRangePreset.MONTH);
    });

    it('should reload data when time range changes', fakeAsync(() => {
      analyticsServiceSpy.getUsageSummaryByDays.mockClear();
      analyticsServiceSpy.getUsageByCenter.mockClear();

      component.selectedTimeRange = DateRangePreset.WEEK;
      component.onTimeRangeChange();
      tick();

      expect(analyticsServiceSpy.getUsageSummaryByDays).toHaveBeenCalled();
      expect(analyticsServiceSpy.getUsageByCenter).toHaveBeenCalled();
    }));

    it('should get correct label for time range', () => {
      component.selectedTimeRange = DateRangePreset.WEEK;
      expect(component.getTimeRangeLabel()).toBe('Last 7 days');

      component.selectedTimeRange = DateRangePreset.MONTH;
      expect(component.getTimeRangeLabel()).toBe('Last 30 days');
    });
  });

  describe('refresh', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should reload data when refresh is clicked', fakeAsync(() => {
      analyticsServiceSpy.getUsageSummaryByDays.mockClear();

      component.onRefresh();
      tick();

      expect(analyticsServiceSpy.getUsageSummaryByDays).toHaveBeenCalled();
    }));
  });

  describe('error handling', () => {
    it('should display error message when data fails to load', fakeAsync(() => {
      analyticsServiceSpy.getUsageSummaryByDays.mockReturnValue(
        throwError(() => new Error('API Error'))
      );

      fixture.detectChanges();
      tick();

      expect(component.error).toBeTruthy();
      expect(component.error).toContain('Failed to load analytics');
    }));

    it('should set isLoading to false on error', fakeAsync(() => {
      analyticsServiceSpy.getUsageSummaryByDays.mockReturnValue(
        throwError(() => new Error('API Error'))
      );

      fixture.detectChanges();
      tick();

      expect(component.isLoading).toBe(false);
    }));
  });

  describe('export functionality', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should not throw when exporting CSV with data', () => {
      expect(() => component.exportCSV()).not.toThrow();
    });

    it('should not throw when exporting JSON with data', () => {
      expect(() => component.exportJSON()).not.toThrow();
    });

    it('should handle empty data for export', () => {
      component.usageSummary.set([]);
      expect(() => component.exportCSV()).not.toThrow();
    });
  });

  describe('chart metric', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should default to calls metric', () => {
      expect(component.chartMetric).toBe('calls');
    });

    it('should update chart metric when changed', () => {
      component.onChartMetricChange('cost');
      expect(component.chartMetric).toBe('cost');
    });
  });

  describe('cleanup', () => {
    it('should complete destroy subject on destroy', () => {
      const destroySpy = jest.spyOn(component['destroy$'], 'complete');

      component.ngOnDestroy();

      expect(destroySpy).toHaveBeenCalled();
    });
  });
});
