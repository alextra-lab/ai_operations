/**
 * Unit tests for AuditLogsService
 */

import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../../environments/environment';
import { AuditLogFilters } from '../models/audit-logs.models';
import { AuditLogsService } from './audit-logs.service';

describe('AuditLogsService', () => {
  let service: AuditLogsService;
  let httpMock: HttpTestingController;
  const baseUrl = `${environment.apiBaseUrl}/admin/audit-logs`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuditLogsService],
    });
    service = TestBed.inject(AuditLogsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('listAuditLogs', () => {
    it('should fetch audit logs with default parameters', () => {
      const mockResponse = {
        total: 10,
        page: 1,
        page_size: 50,
        total_pages: 1,
        logs: [],
      };

      service.listAuditLogs().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(baseUrl);
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include pagination parameters', () => {
      const filters: AuditLogFilters = {
        page: 2,
        page_size: 25,
      };
      const mockResponse = {
        total: 0,
        page: 2,
        page_size: 25,
        total_pages: 0,
        logs: [],
      };

      service.listAuditLogs(filters).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === baseUrl &&
          request.params.get('page') === '2' &&
          request.params.get('page_size') === '25'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include filter parameters', () => {
      const filters: AuditLogFilters = {
        action: 'POST',
        resource_type: 'use_case',
        success: true,
      };
      const mockResponse = {
        total: 0,
        page: 1,
        page_size: 50,
        total_pages: 0,
        logs: [],
      };

      service.listAuditLogs(filters).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === baseUrl &&
          request.params.get('action') === 'POST' &&
          request.params.get('resource_type') === 'use_case' &&
          request.params.get('success') === 'true'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should include search parameter', () => {
      const filters: AuditLogFilters = {
        search: 'test query',
      };
      const mockResponse = {
        total: 0,
        page: 1,
        page_size: 50,
        total_pages: 0,
        logs: [],
      };

      service.listAuditLogs(filters).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === baseUrl &&
          request.params.get('search') === 'test query'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('getAuditLog', () => {
    it('should fetch a single audit log', () => {
      const logId = '123e4567-e89b-12d3-a456-426614174000';
      const mockLog = {
        id: logId,
        event_time: '2025-10-27T12:00:00Z',
        actor_user_id: '123e4567-e89b-12d3-a456-426614174001',
        actor_username: 'testuser',
        actor_roles: ['admin'],
        action: 'GET /api/v1/test',
        resource_type: 'http_request',
        resource_id: '/api/v1/test',
        use_case_id: null,
        use_case_name: null,
        request_id: 'req-123',
        client_ip: '127.0.0.1',
        user_agent: 'Test Agent',
        success: true,
        details: {},
        created_at: '2025-10-27T12:00:00Z',
      };

      service.getAuditLog(logId).subscribe((log) => {
        expect(log).toEqual(mockLog);
      });

      const req = httpMock.expectOne(`${baseUrl}/${logId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockLog);
    });
  });

  describe('getStats', () => {
    it('should fetch audit log statistics', () => {
      const mockStats = {
        total_events: 100,
        success_count: 95,
        failure_count: 5,
        unique_users: 10,
        unique_resource_types: 5,
        date_range_start: '2025-10-01T00:00:00Z',
        date_range_end: '2025-10-27T23:59:59Z',
        top_actions: [],
        top_resource_types: [],
      };

      service.getStats().subscribe((stats) => {
        expect(stats).toEqual(mockStats);
      });

      const req = httpMock.expectOne(`${baseUrl}/stats`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });

    it('should include filter parameters for stats', () => {
      const filters: AuditLogFilters = {
        start_date: '2025-10-01T00:00:00Z',
        end_date: '2025-10-27T23:59:59Z',
        resource_type: 'use_case',
      };
      const mockResponse = {
        total_events: 0,
        success_count: 0,
        failure_count: 0,
        unique_users: 0,
        unique_resource_types: 0,
        date_range_start: null,
        date_range_end: null,
        top_actions: [],
        top_resource_types: [],
      };

      service.getStats(filters).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === `${baseUrl}/stats` &&
          request.params.get('start_date') === '2025-10-01T00:00:00Z' &&
          request.params.get('end_date') === '2025-10-27T23:59:59Z' &&
          request.params.get('resource_type') === 'use_case'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });
});
