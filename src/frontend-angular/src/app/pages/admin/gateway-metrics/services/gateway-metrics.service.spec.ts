/**
 * Unit tests for Gateway Metrics Service
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  GatewayMetrics,
  MetricsFilters,
  ModelMetrics,
  ProviderMetrics,
  TimeSeriesData,
} from '../models/gateway-metrics.models';
import { GatewayMetricsService } from './gateway-metrics.service';

describe('GatewayMetricsService', () => {
  let service: GatewayMetricsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [GatewayMetricsService],
    });

    service = TestBed.inject(GatewayMetricsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getAggregateMetrics', () => {
    it('should fetch aggregate metrics with correct params', () => {
      const filters: MetricsFilters = { hours: 24 };
      const mockData: GatewayMetrics = {
        total_requests: 100,
        successful_requests: 95,
        failed_requests: 5,
        success_rate: 95.0,
        total_tokens: 50000,
        total_cost_eur: 0.5,
        avg_latency_ms: 150.0,
        p50_latency_ms: 120.0,
        p95_latency_ms: 200.0,
        p99_latency_ms: 250.0,
        unique_models: 3,
        unique_users: 10,
        streaming_requests: 40,
      };

      service.getAggregateMetrics(filters).subscribe((data) => {
        expect(data).toEqual(mockData);
      });

      const req = httpMock.expectOne(
        (req) =>
          req.url === '/api/admin/gateway/metrics/aggregate' &&
          req.params.get('hours') === '24'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });

    it('should include provider filter if provided', () => {
      const filters: MetricsFilters = { hours: 6, provider: 'OpenAI' };

      service.getAggregateMetrics(filters).subscribe();

      const req = httpMock.expectOne(
        (req) =>
          req.url === '/api/admin/gateway/metrics/aggregate' &&
          req.params.get('hours') === '6' &&
          req.params.get('provider') === 'OpenAI'
      );
      expect(req.request.method).toBe('GET');
      req.flush({});
    });
  });

  describe('getTimeSeriesData', () => {
    it('should fetch time-series data with calculated interval', () => {
      const filters: MetricsFilters = { hours: 24 };
      const mockData: TimeSeriesData = {
        latency: [
          { timestamp: '2025-11-06T10:00:00', value: 150.0, label: null },
        ],
        tokens: [
          { timestamp: '2025-11-06T10:00:00', value: 5000, label: null },
        ],
        cost: [{ timestamp: '2025-11-06T10:00:00', value: 0.05, label: null }],
        requests: [
          { timestamp: '2025-11-06T10:00:00', value: 10, label: null },
        ],
      };

      service.getTimeSeriesData(filters).subscribe((data) => {
        expect(data).toEqual(mockData);
      });

      const req = httpMock.expectOne(
        (req) =>
          req.url === '/api/admin/gateway/metrics/timeseries' &&
          req.params.get('hours') === '24' &&
          req.params.get('interval_minutes') === '60' // For 24 hours
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });
  });

  describe('getMetricsByProvider', () => {
    it('should fetch provider metrics', () => {
      const mockData: ProviderMetrics[] = [
        {
          provider_name: 'OpenAI',
          request_count: 50,
          success_rate: 98.0,
          avg_latency_ms: 120.0,
          total_cost_eur: 0.25,
          total_tokens: 25000,
        },
      ];

      service.getMetricsByProvider(24).subscribe((data) => {
        expect(data).toEqual(mockData);
        expect(data.length).toBe(1);
        expect(data[0].provider_name).toBe('OpenAI');
      });

      const req = httpMock.expectOne(
        '/api/admin/gateway/metrics/by-provider?hours=24'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });
  });

  describe('getMetricsByModel', () => {
    it('should fetch model metrics', () => {
      const mockData: ModelMetrics[] = [
        {
          model_name: 'gpt-4',
          request_count: 40,
          total_tokens: 30000,
          total_cost_eur: 0.3,
          avg_latency_ms: 150.0,
        },
      ];

      service.getMetricsByModel(24).subscribe((data) => {
        expect(data).toEqual(mockData);
        expect(data.length).toBe(1);
        expect(data[0].model_name).toBe('gpt-4');
      });

      const req = httpMock.expectOne(
        '/api/admin/gateway/metrics/by-model?hours=24'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockData);
    });
  });

  describe('calculateInterval', () => {
    it('should calculate correct intervals for different time ranges', () => {
      // Access private method through service cast
      const calculateInterval = (service as any).calculateInterval.bind(
        service
      );

      expect(calculateInterval(1)).toBe(5); // 1 hour -> 5 min intervals
      expect(calculateInterval(6)).toBe(15); // 6 hours -> 15 min intervals
      expect(calculateInterval(24)).toBe(60); // 24 hours -> 1 hour intervals
      expect(calculateInterval(168)).toBe(360); // 7 days -> 6 hour intervals
      expect(calculateInterval(720)).toBe(1440); // 30 days -> 24 hour intervals
    });
  });
});
