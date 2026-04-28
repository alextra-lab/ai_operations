/**
 * Tool Analytics Service Tests
 *
 * Unit tests for T6-F3 ToolAnalyticsService.
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  CenterUsage,
  ToolUsageSummary,
} from '../../pages/admin/tool-analytics/models/tool-analytics.models';
import { ToolAnalyticsService } from './tool-analytics.service';

describe('ToolAnalyticsService', () => {
  let service: ToolAnalyticsService;
  let httpMock: HttpTestingController;

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

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ToolAnalyticsService],
    });

    service = TestBed.inject(ToolAnalyticsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('getUsageSummary', () => {
    it('should fetch usage summary without date filters', () => {
      service.getUsageSummary().subscribe((result) => {
        expect(result).toEqual(mockUsageSummary);
        expect(result.length).toBe(2);
      });

      const req = httpMock.expectOne('/api/v1/tools/analytics/usage/summary');
      expect(req.request.method).toBe('GET');
      req.flush(mockUsageSummary);
    });

    it('should fetch usage summary with start date', () => {
      const startDate = new Date('2025-11-01');

      service.getUsageSummary(startDate).subscribe((result) => {
        expect(result).toEqual(mockUsageSummary);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === '/api/v1/tools/analytics/usage/summary' &&
          request.params.has('start_date')
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('start_date')).toBe(
        startDate.toISOString()
      );
      req.flush(mockUsageSummary);
    });

    it('should fetch usage summary with date range', () => {
      const startDate = new Date('2025-11-01');
      const endDate = new Date('2025-11-25');

      service.getUsageSummary(startDate, endDate).subscribe((result) => {
        expect(result).toEqual(mockUsageSummary);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === '/api/v1/tools/analytics/usage/summary' &&
          request.params.has('start_date') &&
          request.params.has('end_date')
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('start_date')).toBe(
        startDate.toISOString()
      );
      expect(req.request.params.get('end_date')).toBe(endDate.toISOString());
      req.flush(mockUsageSummary);
    });
  });

  describe('getUsageByCenter', () => {
    it('should fetch usage by center with default days', () => {
      service.getUsageByCenter().subscribe((result) => {
        expect(result).toEqual(mockCenterUsage);
        expect(result.length).toBe(2);
      });

      const req = httpMock.expectOne(
        '/api/v1/tools/analytics/usage/by-center?days=30'
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('days')).toBe('30');
      req.flush(mockCenterUsage);
    });

    it('should fetch usage by center with custom days', () => {
      service.getUsageByCenter(7).subscribe((result) => {
        expect(result).toEqual(mockCenterUsage);
      });

      const req = httpMock.expectOne(
        '/api/v1/tools/analytics/usage/by-center?days=7'
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('days')).toBe('7');
      req.flush(mockCenterUsage);
    });
  });

  describe('getUsageSummaryByDays', () => {
    it('should calculate date range from days and call getUsageSummary', () => {
      const days = 7;

      service.getUsageSummaryByDays(days).subscribe((result) => {
        expect(result).toEqual(mockUsageSummary);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === '/api/v1/tools/analytics/usage/summary' &&
          request.params.has('start_date') &&
          request.params.has('end_date')
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockUsageSummary);
    });
  });

  describe('error handling', () => {
    it('should propagate HTTP errors', () => {
      service.getUsageSummary().subscribe({
        error: (error) => {
          expect(error.status).toBe(500);
        },
      });

      const req = httpMock.expectOne('/api/v1/tools/analytics/usage/summary');
      req.flush('Server error', {
        status: 500,
        statusText: 'Internal Server Error',
      });
    });
  });
});
