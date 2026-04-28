/**
 * CostChartComponent Unit Tests
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { ExecutionMetrics } from '../../../api/models/query-config.models';
import { LibraryLoaderService } from '../../../services/library-loader.service';
import { CostChartComponent } from './cost-chart.component';

describe('CostChartComponent', () => {
  let component: CostChartComponent;
  let fixture: ComponentFixture<CostChartComponent>;
  let libraryLoaderService: any;

  const mockExecutionHistory: ExecutionMetrics[] = [
    {
      timing: { total_time_ms: 1000 },
      tokens: { input_tokens: 100, output_tokens: 200, total_tokens: 300 },
      cost: {
        input_cost: 0.004,
        output_cost: 0.006,
        total_cost: 0.01,
        currency: 'USD',
      },
    },
    {
      timing: { total_time_ms: 1200 },
      tokens: { input_tokens: 120, output_tokens: 220, total_tokens: 340 },
      cost: {
        input_cost: 0.0048,
        output_cost: 0.0072,
        total_cost: 0.012,
        currency: 'USD',
      },
    },
    {
      timing: { total_time_ms: 950 },
      tokens: { input_tokens: 95, output_tokens: 190, total_tokens: 285 },
      cost: {
        input_cost: 0.0038,
        output_cost: 0.0057,
        total_cost: 0.0095,
        currency: 'USD',
      },
    },
  ];

  beforeEach(async () => {
    const libraryLoaderSpy = {
      loadChartJS: jest.fn().mockResolvedValue(undefined),
    };

    await TestBed.configureTestingModule({
      imports: [CostChartComponent, NoopAnimationsModule],
      providers: [
        { provide: LibraryLoaderService, useValue: libraryLoaderSpy },
      ],
    }).compileComponents();

    libraryLoaderService = TestBed.inject(LibraryLoaderService) as any;

    // Mock Chart.js on window
    const mockChart = {
      data: {
        labels: [],
        datasets: [{ data: [] }, { data: [] }],
      },
      update: jest.fn(),
      destroy: jest.fn(),
    };
    const chartConstructorSpy = jest.fn().mockReturnValue(mockChart);
    (window as any).Chart = chartConstructorSpy;
    (window as any).__mockChart = mockChart;
    (window as any).__chartConstructorSpy = chartConstructorSpy;

    fixture = TestBed.createComponent(CostChartComponent);
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

  it('should create dual-axis line chart', async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    const chartConstructorSpy = (window as any).__chartConstructorSpy;
    expect(chartConstructorSpy).toHaveBeenCalled();
    const chartConfig = chartConstructorSpy.mock.calls[0][1];
    expect(chartConfig.type).toBe('line');
    expect(chartConfig.data.datasets.length).toBe(2);
    expect(chartConfig.data.datasets[0].label).toBe('Per Query Cost');
    expect(chartConfig.data.datasets[1].label).toBe('Cumulative Cost');
  });

  it('should configure dual y-axes', async () => {
    fixture.detectChanges();
    await fixture.whenStable();

    const chartConstructorSpy = (window as any).__chartConstructorSpy;
    const chartConfig = chartConstructorSpy.mock.calls[0][1];
    expect(chartConfig.options.scales.y).toBeDefined();
    expect(chartConfig.options.scales.y1).toBeDefined();
    expect(chartConfig.options.scales.y.position).toBe('left');
    expect(chartConfig.options.scales.y1.position).toBe('right');
  });

  it('should calculate cumulative costs correctly', async () => {
    component.executionHistory = mockExecutionHistory;
    fixture.detectChanges();
    await fixture.whenStable();

    // Trigger update
    component['updateChart']();

    // Cumulative should be: 0.01, 0.022, 0.0315
    const chart = component['chart'];
    if (chart && chart.data && chart.data.datasets[1]) {
      const cumulativeData = chart.data.datasets[1].data;
      expect(cumulativeData[0]).toBeCloseTo(0.01, 4);
      expect(cumulativeData[1]).toBeCloseTo(0.022, 4);
      expect(cumulativeData[2]).toBeCloseTo(0.0315, 4);
    }
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
        cost: {
          input_cost: 0.0044,
          output_cost: 0.0066,
          total_cost: 0.011,
          currency: 'USD',
        },
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

  it('should handle missing cost data', async () => {
    component.executionHistory = [
      {
        timing: { total_time_ms: 1000 },
        tokens: { input_tokens: 100, output_tokens: 200, total_tokens: 300 },
        // No cost data
      },
    ];

    fixture.detectChanges();
    await fixture.whenStable();

    // Should not throw error
    expect(component).toBeTruthy();
  });
});
