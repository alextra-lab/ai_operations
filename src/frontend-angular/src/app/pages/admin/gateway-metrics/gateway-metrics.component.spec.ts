/// <reference types="jest" />
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { GatewayMetricsComponent } from './gateway-metrics.component';
import type {
  GatewayMetrics,
  ModelMetrics,
  ProviderMetrics,
  TimeSeriesData,
} from './models/gateway-metrics.models';
import { GatewayMetricsService } from './services/gateway-metrics.service';

describe('GatewayMetricsComponent', () => {
  let component: GatewayMetricsComponent;
  let fixture: ComponentFixture<GatewayMetricsComponent>;
  let mockService: Partial<GatewayMetricsService>;

  const mockAggregateMetrics: GatewayMetrics = {
    total_requests: 100,
    successful_requests: 95,
    failed_requests: 5,
    success_rate: 95.0,
    total_input_tokens: 5000,
    total_output_tokens: 3000,
    total_cost_eur: 0.5,
    avg_latency_ms: 250.5,
    p50_latency_ms: 200.0,
    p95_latency_ms: 400.0,
    p99_latency_ms: 500.0,
    unique_models: 3,
    unique_users: 10,
    streaming_requests: 20,
  };

  const mockTimeSeriesData: TimeSeriesData = {
    latency: [{ timestamp: '2025-11-06T12:00:00Z', value: 250 }],
    tokens: [{ timestamp: '2025-11-06T12:00:00Z', value: 100 }],
    cost: [{ timestamp: '2025-11-06T12:00:00Z', value: 0.01 }],
    requests: [{ timestamp: '2025-11-06T12:00:00Z', value: 10 }],
  };

  const mockProviderMetrics: ProviderMetrics[] = [
    {
      provider_name: 'OpenAI',
      request_count: 50,
      success_rate: 96.0,
      avg_latency_ms: 230.0,
      total_cost_eur: 0.3,
      total_tokens: 4000,
    },
  ];

  const mockModelMetrics: ModelMetrics[] = [
    {
      model_name: 'gpt-4',
      request_count: 30,
      total_tokens: 2500,
      total_cost_eur: 0.2,
      avg_latency_ms: 280.0,
    },
  ];

  beforeEach(async () => {
    mockService = {
      getAggregateMetrics: jest.fn().mockReturnValue(of(mockAggregateMetrics)),
      getTimeSeriesData: jest.fn().mockReturnValue(of(mockTimeSeriesData)),
      getMetricsByProvider: jest.fn().mockReturnValue(of(mockProviderMetrics)),
      getMetricsByModel: jest.fn().mockReturnValue(of(mockModelMetrics)),
      exportMetricsCSV: jest.fn(),
      exportMetricsJSON: jest.fn(),
    };

    const snackBarMock = { open: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        GatewayMetricsComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        MatCardModule,
        MatSelectModule,
        MatButtonModule,
        MatTabsModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MatTableModule,
      ],
      providers: [
        { provide: GatewayMetricsService, useValue: mockService },
        { provide: MatSnackBar, useValue: snackBarMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(GatewayMetricsComponent);
    component = fixture.componentInstance;
    (component as unknown as { snackBar: { open: jest.Mock } }).snackBar =
      snackBarMock;
  });

  it('should create the component', () => {
    expect(component).toBeDefined();
  });

  it('should load metrics on init', (done) => {
    fixture.detectChanges();

    setTimeout(() => {
      expect(component.aggregateMetrics).toEqual(mockAggregateMetrics);
      expect(component.timeSeriesData).toEqual(mockTimeSeriesData);
      expect(component.providerMetrics).toEqual(mockProviderMetrics);
      expect(component.modelMetrics).toEqual(mockModelMetrics);
      expect(component.isLoading).toBe(false);
      done();
    }, 100);
  });

  it('should handle API errors gracefully', (done) => {
    mockService.getAggregateMetrics = jest
      .fn()
      .mockReturnValue(throwError(() => new Error('API Error')));

    fixture.detectChanges();

    setTimeout(() => {
      expect(component.error).toContain('Failed to load metrics');
      expect(component.isLoading).toBe(false);
      done();
    }, 100);
  });

  it('should refresh metrics when requested', () => {
    component.refreshMetrics();

    expect(mockService.getAggregateMetrics).toHaveBeenCalled();
    expect(mockService.getTimeSeriesData).toHaveBeenCalled();
    expect(mockService.getMetricsByProvider).toHaveBeenCalled();
    expect(mockService.getMetricsByModel).toHaveBeenCalled();
  });

  it('should reload metrics when time range changes', () => {
    component.selectedTimeRange = '7d';
    component.onTimeRangeChange();

    expect(component.selectedTimeRange).toBe('7d');
    expect(mockService.getAggregateMetrics).toHaveBeenCalled();
  });

  it('should export data as CSV', () => {
    component.aggregateMetrics = mockAggregateMetrics;
    component.providerMetrics = mockProviderMetrics;
    component.modelMetrics = mockModelMetrics;

    const createElementSpy = jest.spyOn(document, 'createElement');
    const linkMock = {
      click: jest.fn(),
      href: '',
      download: '',
    };
    createElementSpy.mockReturnValue(linkMock as any);

    component.exportCSV();

    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(linkMock.click).toHaveBeenCalled();
  });

  it('should export data as JSON', () => {
    component.aggregateMetrics = mockAggregateMetrics;
    component.timeSeriesData = mockTimeSeriesData;
    component.providerMetrics = mockProviderMetrics;
    component.modelMetrics = mockModelMetrics;

    const createElementSpy = jest.spyOn(document, 'createElement');
    const linkMock = {
      click: jest.fn(),
      href: '',
      download: '',
    };
    createElementSpy.mockReturnValue(linkMock as any);

    component.exportJSON();

    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(linkMock.click).toHaveBeenCalled();
  });

  it('should format numbers with commas', () => {
    expect(component.formatNumber(1000)).toBe('1,000');
    expect(component.formatNumber(1000000)).toBe('1,000,000');
    expect(component.formatNumber(0)).toBe('0');
  });

  it('should format cost with EUR symbol', () => {
    expect(component.formatCost(1.5)).toBe('€1.500000');
    expect(component.formatCost(0.000123)).toBe('€0.000123');
  });

  it('should clean up subscriptions on destroy', () => {
    const nextSpy = jest.spyOn(component['destroy$'], 'next');
    const completeSpy = jest.spyOn(component['destroy$'], 'complete');

    component.ngOnDestroy();

    expect(nextSpy).toHaveBeenCalled();
    expect(completeSpy).toHaveBeenCalled();
  });
});
