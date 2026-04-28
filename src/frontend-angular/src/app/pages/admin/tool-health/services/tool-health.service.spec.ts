/**
 * Tool Health Service Unit Tests
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  HealthSummary,
  ToolHealthCheckRecord,
} from '../models/tool-health.models';
import { ToolHealthService } from './tool-health.service';

describe('ToolHealthService', () => {
  let service: ToolHealthService;
  let httpMock: HttpTestingController;

  const mockSummary: HealthSummary = {
    total_tools: 5,
    online: 4,
    offline: 1,
    health_percentage: 80.0,
    last_check: '2025-11-24T10:00:00Z',
  };

  const mockHistoryRecords: ToolHealthCheckRecord[] = [
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
      error_message: 'Connection timeout',
      checked_at: '2025-11-24T09:30:00Z',
    },
  ];

  const mockCheckResult: ToolHealthCheckRecord = {
    id: 'check-new',
    tool_id: 'tool-123',
    status: 'online',
    response_time_ms: 120,
    error_message: null,
    checked_at: '2025-11-24T10:05:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ToolHealthService],
    });

    service = TestBed.inject(ToolHealthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('getOverallStatus', () => {
    it('should return health summary', () => {
      service.getOverallStatus().subscribe((summary) => {
        expect(summary).toEqual(mockSummary);
        expect(summary.total_tools).toBe(5);
        expect(summary.online).toBe(4);
        expect(summary.offline).toBe(1);
        expect(summary.health_percentage).toBe(80.0);
      });

      const req = httpMock.expectOne('/api/v1/tools/health/status');
      expect(req.request.method).toBe('GET');
      req.flush(mockSummary);
    });

    it('should handle empty response', () => {
      const emptySummary: HealthSummary = {
        total_tools: 0,
        online: 0,
        offline: 0,
        health_percentage: 0,
        last_check: null,
      };

      service.getOverallStatus().subscribe((summary) => {
        expect(summary.total_tools).toBe(0);
        expect(summary.last_check).toBeNull();
      });

      const req = httpMock.expectOne('/api/v1/tools/health/status');
      req.flush(emptySummary);
    });
  });

  describe('getToolHistory', () => {
    it('should return tool history with default hours', () => {
      service.getToolHistory('tool-123').subscribe((history) => {
        expect(history).toEqual(mockHistoryRecords);
        expect(history.length).toBe(2);
      });

      const req = httpMock.expectOne(
        '/api/v1/tools/health/tool-123/history?hours=24'
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.params.get('hours')).toBe('24');
      req.flush(mockHistoryRecords);
    });

    it('should return tool history with custom hours', () => {
      service.getToolHistory('tool-123', 72).subscribe((history) => {
        expect(history).toEqual(mockHistoryRecords);
      });

      const req = httpMock.expectOne(
        '/api/v1/tools/health/tool-123/history?hours=72'
      );
      expect(req.request.params.get('hours')).toBe('72');
      req.flush(mockHistoryRecords);
    });

    it('should handle empty history', () => {
      service.getToolHistory('tool-456').subscribe((history) => {
        expect(history).toEqual([]);
        expect(history.length).toBe(0);
      });

      const req = httpMock.expectOne(
        '/api/v1/tools/health/tool-456/history?hours=24'
      );
      req.flush([]);
    });
  });

  describe('triggerHealthCheck', () => {
    it('should trigger health check and return result', () => {
      service.triggerHealthCheck('tool-123').subscribe((result) => {
        expect(result).toEqual(mockCheckResult);
        expect(result.status).toBe('online');
        expect(result.response_time_ms).toBe(120);
      });

      const req = httpMock.expectOne('/api/v1/tools/health/tool-123/check');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({});
      req.flush(mockCheckResult);
    });

    it('should return offline status on failure', () => {
      const offlineResult: ToolHealthCheckRecord = {
        id: 'check-fail',
        tool_id: 'tool-123',
        status: 'offline',
        response_time_ms: null,
        error_message: 'Connection refused',
        checked_at: '2025-11-24T10:05:00Z',
      };

      service.triggerHealthCheck('tool-123').subscribe((result) => {
        expect(result.status).toBe('offline');
        expect(result.error_message).toBe('Connection refused');
      });

      const req = httpMock.expectOne('/api/v1/tools/health/tool-123/check');
      req.flush(offlineResult);
    });
  });
});
