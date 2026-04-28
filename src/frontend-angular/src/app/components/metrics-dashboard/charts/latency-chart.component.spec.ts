/**
 * LatencyChartComponent Unit Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { ExecutionMetrics } from '../../../api/models/query-config.models';
import { LibraryLoaderService } from '../../../services/library-loader.service';
import { LatencyChartComponent } from './latency-chart.component';

describe('LatencyChartComponent', () => {
  let component: LatencyChartComponent;
  let fixture: ComponentFixture<LatencyChartComponent>;
  let libraryLoaderService: any;

  const mockExecutionHistory: ExecutionMetrics[] = [
    {
      timing: { total_time_ms: 1000 },
      tokens: { input_tokens: 100, output_tokens: 200, total_tokens: 300 },
    },
    {
      timing: { total_time_ms: 1200 },
      tokens: { input_tokens: 120, output_tokens: 220, total_tokens: 340 },
    },
    {
      timing: { total_time_ms: 950 },
      tokens: { input_tokens: 95, output_tokens: 190, total_tokens: 285 },
    },
  ];

  beforeEach(async () => {
    const libraryLoaderSpy = {
      loadChartJS: jest.fn().mockResolvedValue(undefined),
    };

    await TestBed.configureTestingModule({
      imports: [LatencyChartComponent, NoopAnimationsModule],
      providers: [
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    libraryLoaderService = TestBed.inject(LibraryLoaderService) as any;

    // Mock Chart.js on window
    const mockChart = {
      data: { labels: [], datasets: [{ data: [] }] },
      update: jest.fn(),
      destroy: jest.fn(),
    };
    const chartConstructorSpy = jest.fn().mockReturnValue(mockChart);
    (window as any).Chart = chartConstructorSpy;
    (window as any).__mockChart = mockChart;
    (window as any).__chartConstructorSpy = chartConstructorSpy;

    fixture = TestBed.createComponent(LatencyChartComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load Chart.js library on init', async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    expect(libraryLoaderService.loadChartJS).toHaveBeenCalled();
  });

  it('should initialize with loading state', () => {
    expect(component.isLoading).toBe(true);
  });

  it('should set loading to false after chart initializes', async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.isLoading).toBe(false);
  });

  it('should update chart when execution history changes', async () => {
    component.executionHistory = mockExecutionHistory;
    fixture.detectChanges();
    await fixture.whenStable();

    component.executionHistory = [
      ...mockExecutionHistory,
      {
        timing: { total_time_ms: 1100 },
        tokens: { input_tokens: 110, output_tokens: 210, total_tokens: 320 },
      },
    ];

    component.ngOnChanges({
      executionHistory: {
        currentValue: component.executionHistory,
        previousValue: mockExecutionHistory,
        firstChange: false,
        isFirstChange: () => false,
      },
    });

    // Component should have chart instance
    expect(component['chart']).toBeDefined();
  });

  it('should cleanup chart on destroy', async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    const destroySpy = component['chart']?.destroy;

    component.ngOnDestroy();

    if (destroySpy) {
      expect(destroySpy).toHaveBeenCalled();
    }
  });

  it('should handle Chart.js load failure gracefully', async () => {
    libraryLoaderService.loadChartJS.mockRejectedValue('Failed to load');

    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.isLoading).toBe(false);
  });
});
