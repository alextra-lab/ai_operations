/**
 * Usage By Center Chart Component Tests
 *
 * Unit tests for T6-F3 UsageByCenterChartComponent.
 */

import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { LibraryLoaderService } from '../../../../../services/library-loader.service';
import { CenterUsage } from '../../models/tool-analytics.models';
import { UsageByCenterChartComponent } from './usage-by-center-chart.component';

describe('UsageByCenterChartComponent', () => {
  let component: UsageByCenterChartComponent;
  let fixture: ComponentFixture<UsageByCenterChartComponent>;
  let libraryLoaderSpy: jest.Mocked<LibraryLoaderService>;

  const mockChartJS = jest.fn().mockImplementation(() => ({
    data: { labels: [], datasets: [{ data: [] }] },
    options: { scales: { x: { title: {} } } },
    update: jest.fn(),
    destroy: jest.fn(),
  }));

  const mockData: CenterUsage[] = [
    { center_id: 'center-a', total_calls: 100, total_cost: 0.5 },
    { center_id: 'center-b', total_calls: 75, total_cost: 0.35 },
    { center_id: 'center-c', total_calls: 50, total_cost: 0.25 },
  ];

  beforeEach(async () => {
    libraryLoaderSpy = {
      loadChartJS: jest.fn().mockResolvedValue(mockChartJS),
      isLoaded: jest.fn().mockReturnValue(false),
      loadPrism: jest.fn(),
      loadKaTeX: jest.fn(),
      loadMermaid: jest.fn(),
      getLoadedLibraries: jest.fn().mockReturnValue([]),
      isLoading: jest.fn().mockReturnValue(false),
    } as unknown as jest.Mocked<LibraryLoaderService>;

    await TestBed.configureTestingModule({
      imports: [
        UsageByCenterChartComponent,
        MatButtonToggleModule,
        MatProgressSpinnerModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UsageByCenterChartComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('initialization', () => {
    it('should start in loading state', () => {
      expect(component.isLoading).toBe(true);
    });

    it('should load Chart.js library on init', fakeAsync(() => {
      component.data = mockData;
      fixture.detectChanges();
      tick();

      expect(libraryLoaderSpy.loadChartJS).toHaveBeenCalled();
    }));

    it('should attempt to load chart library', fakeAsync(() => {
      component.data = mockData;
      fixture.detectChanges();
      tick();

      expect(libraryLoaderSpy.loadChartJS).toHaveBeenCalled();
    }));
  });

  describe('metric toggle', () => {
    it('should default to calls metric', () => {
      expect(component.metric).toBe('calls');
    });

    it('should emit metricChange when metric changes', () => {
      const emitSpy = jest.spyOn(component.metricChange, 'emit');

      component.onMetricChange('cost');

      expect(component.metric).toBe('cost');
      expect(emitSpy).toHaveBeenCalledWith('cost');
    });

    it('should switch between calls and cost metrics', () => {
      component.onMetricChange('cost');
      expect(component.metric).toBe('cost');

      component.onMetricChange('calls');
      expect(component.metric).toBe('calls');
    });
  });

  describe('data binding', () => {
    beforeEach(fakeAsync(() => {
      component.data = mockData;
      fixture.detectChanges();
      tick();
    }));

    it('should accept data input', () => {
      expect(component.data).toEqual(mockData);
    });

    it('should handle data changes', () => {
      const newData: CenterUsage[] = [
        { center_id: 'new-center', total_calls: 200, total_cost: 1.0 },
      ];

      component.data = newData;
      component.ngOnChanges({
        data: {
          currentValue: newData,
          previousValue: mockData,
          firstChange: false,
          isFirstChange: () => false,
        },
      });

      expect(component.data).toEqual(newData);
    });
  });

  describe('empty state', () => {
    it('should show empty state when no data', fakeAsync(() => {
      component.data = [];
      component.isLoading = false;
      fixture.detectChanges();
      tick();

      const emptyState = fixture.nativeElement.querySelector('.empty-state');
      expect(emptyState).toBeTruthy();
      expect(emptyState.textContent).toContain(
        'No center usage data available'
      );
    }));
  });

  describe('loading state', () => {
    it('should show spinner when loading', () => {
      component.isLoading = true;
      fixture.detectChanges();

      const spinner = fixture.nativeElement.querySelector('mat-spinner');
      expect(spinner).toBeTruthy();
    });

    it('should hide canvas when loading', () => {
      component.isLoading = true;
      fixture.detectChanges();

      const canvas = fixture.nativeElement.querySelector('canvas');
      expect(canvas.hidden).toBe(true);
    });
  });

  describe('cleanup', () => {
    it('should destroy chart on component destroy', fakeAsync(() => {
      component.data = mockData;
      fixture.detectChanges();
      tick();

      // Manually create a mock chart instance
      const mockChart = {
        destroy: jest.fn(),
        data: { labels: [], datasets: [] },
        options: {},
        update: jest.fn(),
      };
      (component as unknown as { chart: typeof mockChart }).chart = mockChart;

      component.ngOnDestroy();

      expect(mockChart.destroy).toHaveBeenCalled();
      expect((component as unknown as { chart: null }).chart).toBeNull();
    }));
  });
});
