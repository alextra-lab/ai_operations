/**
 * Tool Admin Service Tests
 */

import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import {
  Tool,
  ToolFilters,
  ToolHealthCheckResult,
  ToolListItem,
  ToolUpdateRequest,
} from '../models/tool-management.models';
import { ToolAdminService } from './tool-admin.service';

describe('ToolAdminService', () => {
  let service: ToolAdminService;
  let httpClientMock: jest.Mocked<HttpClient>;

  beforeEach(() => {
    httpClientMock = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
    } as any;

    TestBed.configureTestingModule({
      providers: [
        ToolAdminService,
        { provide: HttpClient, useValue: httpClientMock },
      ],
    });

    service = TestBed.inject(ToolAdminService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('listTools', () => {
    it('should list tools without filters', (done) => {
      const mockTools: ToolListItem[] = [
        {
          id: '1',
          tool_id: 'test-tool',
          name: 'Test Tool',
          description: 'Test description',
          category: 'database',
          is_enabled: true,
          is_healthy: true,
          requires_authentication: false,
        },
      ];

      httpClientMock.get.mockReturnValue(of(mockTools));

      service.listTools().subscribe({
        next: (tools) => {
          expect(tools).toEqual(mockTools);
          expect(httpClientMock.get).toHaveBeenCalledWith(
            '/api/v1/admin/tools/',
            expect.any(Object)
          );
          done();
        },
      });
    });

    it('should list tools with filters', (done) => {
      const filters: ToolFilters = {
        category: 'database',
        enabled_only: true,
        healthy_only: true,
      };
      const mockTools: ToolListItem[] = [];

      httpClientMock.get.mockReturnValue(of(mockTools));

      service.listTools(filters).subscribe({
        next: (tools) => {
          expect(tools).toEqual(mockTools);
          expect(httpClientMock.get).toHaveBeenCalled();
          done();
        },
      });
    });
  });

  describe('getTool', () => {
    it('should get a tool by ID', (done) => {
      const mockTool: Tool = {
        id: '1',
        tool_id: 'test-tool',
        name: 'Test Tool',
        description: 'Test description',
        category: 'database',
        provider: null,
        tool_purpose: 'orchestrator',
        service_location: 'orchestrator',
        mcp_server_type: 'http',
        mcp_command: null,
        mcp_endpoint: 'https://example.com',
        mcp_protocol_version: '2024-11-05',
        capabilities: null,
        parameters_schema: null,
        requires_authentication: false,
        authentication_type: null,
        secret_name: null,
        config_options: null,
        timeout_seconds: 30,
        rate_limit_per_minute: null,
        max_concurrent_calls: 5,
        is_enabled: true,
        health_check_interval_seconds: 300,
        version: null,
        documentation_url: null,
        tags: [],
        is_healthy: true,
        last_health_check: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        created_by: null,
        updated_by: null,
      };

      httpClientMock.get.mockReturnValue(of(mockTool));

      service.getTool('1').subscribe({
        next: (tool) => {
          expect(tool).toEqual(mockTool);
          expect(httpClientMock.get).toHaveBeenCalledWith(
            '/api/v1/admin/tools/1'
          );
          done();
        },
      });
    });
  });

  describe('updateTool', () => {
    it('should update a tool', (done) => {
      const updateRequest: ToolUpdateRequest = {
        name: 'Updated Tool',
        description: 'Updated description',
        timeout_seconds: 60,
      };
      const mockTool: Tool = {
        id: '1',
        tool_id: 'test-tool',
        name: 'Updated Tool',
        description: 'Updated description',
        category: 'database',
        provider: null,
        tool_purpose: 'orchestrator',
        service_location: 'orchestrator',
        mcp_server_type: 'http',
        mcp_command: null,
        mcp_endpoint: 'https://example.com',
        mcp_protocol_version: '2024-11-05',
        capabilities: null,
        parameters_schema: null,
        requires_authentication: false,
        authentication_type: null,
        secret_name: null,
        config_options: null,
        timeout_seconds: 60,
        rate_limit_per_minute: null,
        max_concurrent_calls: 5,
        is_enabled: true,
        health_check_interval_seconds: 300,
        version: null,
        documentation_url: null,
        tags: [],
        is_healthy: true,
        last_health_check: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        created_by: null,
        updated_by: null,
      };

      httpClientMock.put.mockReturnValue(of(mockTool));

      service.updateTool('1', updateRequest).subscribe({
        next: (tool) => {
          expect(tool).toEqual(mockTool);
          expect(httpClientMock.put).toHaveBeenCalledWith(
            '/api/v1/admin/tools/1',
            updateRequest
          );
          done();
        },
      });
    });
  });

  describe('deleteTool', () => {
    it('should delete a tool', (done) => {
      httpClientMock.delete.mockReturnValue(of(undefined));

      service.deleteTool('1').subscribe({
        next: () => {
          expect(httpClientMock.delete).toHaveBeenCalledWith(
            '/api/v1/admin/tools/1'
          );
          done();
        },
      });
    });
  });

  describe('enableTool', () => {
    it('should enable a tool', (done) => {
      const mockTool: Tool = {
        id: '1',
        tool_id: 'test-tool',
        name: 'Test Tool',
        description: null,
        category: 'database',
        provider: null,
        tool_purpose: 'orchestrator',
        service_location: 'orchestrator',
        mcp_server_type: 'http',
        mcp_command: null,
        mcp_endpoint: 'https://example.com',
        mcp_protocol_version: '2024-11-05',
        capabilities: null,
        parameters_schema: null,
        requires_authentication: false,
        authentication_type: null,
        secret_name: null,
        config_options: null,
        timeout_seconds: 30,
        rate_limit_per_minute: null,
        max_concurrent_calls: 5,
        is_enabled: true,
        health_check_interval_seconds: 300,
        version: null,
        documentation_url: null,
        tags: [],
        is_healthy: true,
        last_health_check: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        created_by: null,
        updated_by: null,
      };

      httpClientMock.post.mockReturnValue(of(mockTool));

      service.enableTool('1').subscribe({
        next: (tool) => {
          expect(tool.is_enabled).toBe(true);
          expect(httpClientMock.post).toHaveBeenCalledWith(
            '/api/v1/admin/tools/1/enable',
            {}
          );
          done();
        },
      });
    });
  });

  describe('disableTool', () => {
    it('should disable a tool', (done) => {
      const mockTool: Tool = {
        id: '1',
        tool_id: 'test-tool',
        name: 'Test Tool',
        description: null,
        category: 'database',
        provider: null,
        tool_purpose: 'orchestrator',
        service_location: 'orchestrator',
        mcp_server_type: 'http',
        mcp_command: null,
        mcp_endpoint: 'https://example.com',
        mcp_protocol_version: '2024-11-05',
        capabilities: null,
        parameters_schema: null,
        requires_authentication: false,
        authentication_type: null,
        secret_name: null,
        config_options: null,
        timeout_seconds: 30,
        rate_limit_per_minute: null,
        max_concurrent_calls: 5,
        is_enabled: false,
        health_check_interval_seconds: 300,
        version: null,
        documentation_url: null,
        tags: [],
        is_healthy: true,
        last_health_check: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        created_by: null,
        updated_by: null,
      };

      httpClientMock.post.mockReturnValue(of(mockTool));

      service.disableTool('1').subscribe({
        next: (tool) => {
          expect(tool.is_enabled).toBe(false);
          expect(httpClientMock.post).toHaveBeenCalledWith(
            '/api/v1/admin/tools/1/disable',
            {}
          );
          done();
        },
      });
    });
  });

  describe('triggerHealthCheck', () => {
    it('should trigger a health check', (done) => {
      const mockResult: ToolHealthCheckResult = {
        tool_id: '1',
        status: 'online',
        response_time_ms: 100,
        error_message: null,
        checked_at: '2025-01-01T00:00:00Z',
      };

      httpClientMock.post.mockReturnValue(of(mockResult));

      service.triggerHealthCheck('1').subscribe({
        next: (result) => {
          expect(result).toEqual(mockResult);
          expect(httpClientMock.post).toHaveBeenCalledWith(
            '/api/v1/tools/health/1/check',
            {}
          );
          done();
        },
      });
    });
  });
});
