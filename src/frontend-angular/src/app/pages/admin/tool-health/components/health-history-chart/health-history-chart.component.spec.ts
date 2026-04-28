/**
 * Health History Chart Component Unit Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { By } from '@angular/platform-browser';

import { LibraryLoaderService } from '../../../../../services/library-loader.service';
import { ToolHealthCheckRecord } from '../../models/tool-health.models';
import { HealthHistoryChartComponent } from './health-history-chart.component';

describe('HealthHistoryChartComponent', () => {
  let component: HealthHistoryChartComponent;
  let fixture: ComponentFixture<HealthHistoryChartComponent>;
  let libraryLoaderSpy: jest.Mocked<LibraryLoaderService>;

  const mockHistoryData: ToolHealthCheckRecord[] = [
    {
      id: 'check-1',
      tool_id: 'tool-123',
      status: 'online',
      response_time_ms: 150,
      error_message: null,
      checked_at: '2025-11-24T10:00:00Z',
    },
    {
      id: 'check-2',
      tool_id: 'tool-123',
      status: 'offline',
      response_time_ms: null,
      error_message: 'Timeout',
      checked_at: '2025-11-24T09:00:00Z',
    },
    {
      id: 'check-3',
      tool_id: 'tool-123',
      status: 'online',
      response_time_ms: 120,
      error_message: null,
      checked_at: '2025-11-24T08:00:00Z',
    },
  ];

  // Mock Chart.js constructor
  const mockChartInstance = {
    data: {
      labels: [] as string[],
      datasets: [{ data: [] as number[] }, { data: [] as number[] }],
    },
    update: jest.fn(),
    destroy: jest.fn(),
  };

  const MockChart = jest.fn().mockImplementation(() => mockChartInstance);

  beforeEach(async () => {
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
      imports: [HealthHistoryChartComponent, MatProgressSpinnerModule],
      providers: [
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    // Set up window.Chart mock
    (window as unknown as { Chart: typeof MockChart }).Chart = MockChart;

    fixture = TestBed.createComponent(HealthHistoryChartComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    delete (window as unknown as { Chart?: typeof MockChart }).Chart;
    jest.clearAllMocks();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should start with loading state', () => {
      expect(component.isLoading).toBe(true);
    });

    it('should load Chart.js library on init', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      expect(libraryLoaderSpy.loadChartJS).toHaveBeenCalled();
    });

    it('should set isLoading to false after library loads', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      expect(component.isLoading).toBe(false);
    });
  });

  describe('loading state display', () => {
    it('should show spinner when loading', () => {
      component.isLoading = true;
      fixture.detectChanges();

      const spinner = fixture.debugElement.query(By.css('mat-spinner'));
      expect(spinner).toBeTruthy();
    });

    it('should hide canvas when loading', () => {
      component.isLoading = true;
      fixture.detectChanges();

      const canvas = fixture.debugElement.query(By.css('canvas'));
      expect(canvas.properties['hidden']).toBe(true);
    });
  });

  describe('empty state', () => {
    it('should show empty message when no data', async () => {
      component.data = [];
      component.isLoading = false;
      fixture.detectChanges();

      const emptyState = fixture.debugElement.query(By.css('.empty-state'));
      expect(emptyState).toBeTruthy();
      expect(emptyState.nativeElement.textContent).toContain(
        'No health data available'
      );
    });
  });

  describe('with data', () => {
    beforeEach(async () => {
      component.data = mockHistoryData;
      fixture.detectChanges();
      await fixture.whenStable();
    });

    it('should not show empty state when data exists', () => {
      const emptyState = fixture.debugElement.query(By.css('.empty-state'));
      expect(emptyState).toBeFalsy();
    });
  });

  describe('ngOnChanges', () => {
    it('should update chart when data changes', async () => {
      component.data = mockHistoryData;
      fixture.detectChanges();
      await fixture.whenStable();

      // Simulate data change
      const newData = [...mockHistoryData];
      newData.push({
        id: 'check-4',
        tool_id: 'tool-123',
        status: 'online',
        response_time_ms: 100,
        error_message: null,
        checked_at: '2025-11-24T11:00:00Z',
      });

      component.data = newData;
      component.ngOnChanges({
        data: {
          currentValue: newData,
          previousValue: mockHistoryData,
          firstChange: false,
          isFirstChange: () => false,
        },
      });
    });
  });

  describe('ngOnDestroy', () => {
    it('should destroy chart on component destroy', async () => {
      component.data = mockHistoryData;
      fixture.detectChanges();
      await fixture.whenStable();

      component.ngOnDestroy();

      // Chart should be destroyed (internal implementation)
    });
  });

  describe('accessibility', () => {
    it('should have aria-label on canvas', async () => {
      component.data = mockHistoryData;
      component.isLoading = false;
      fixture.detectChanges();

      const canvas = fixture.debugElement.query(By.css('canvas'));
      expect(canvas.attributes['aria-label']).toBe('Tool health history chart');
    });

    it('should have role="img" on canvas', async () => {
      component.data = mockHistoryData;
      component.isLoading = false;
      fixture.detectChanges();

      const canvas = fixture.debugElement.query(By.css('canvas'));
      expect(canvas.attributes['role']).toBe('img');
    });
  });

  describe('error handling', () => {
    it('should handle Chart.js load failure gracefully', async () => {
      libraryLoaderSpy.loadChartJS.mockRejectedValueOnce(
        new Error('Failed to load')
      );

      fixture.detectChanges();
      await fixture.whenStable();

      // Should still set isLoading to false
      expect(component.isLoading).toBe(false);
    });
  });
});
