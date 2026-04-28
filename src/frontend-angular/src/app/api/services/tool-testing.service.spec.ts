import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import {
  ParameterValidationRequest,
  ParameterValidationResult,
  TestExecutionRequest,
  TestExecutionResult,
  ToolTestingService,
} from './tool-testing.service';

describe('ToolTestingService', () => {
  let service: ToolTestingService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ToolTestingService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(ToolTestingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('executeTest', () => {
    it('should call POST /api/v1/tools/test/execute', () => {
      const request: TestExecutionRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        tool_name: 'search',
        parameters: { query: 'test query' },
      };

      const mockResult: TestExecutionResult = {
        success: true,
        status: 'success',
        result: { data: 'test result' },
        duration_ms: 150.5,
      };

      service.executeTest(request).subscribe((result) => {
        expect(result).toEqual(mockResult);
      });

      const req = httpMock.expectOne('/api/v1/tools/test/execute');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResult);
    });

    it('should handle execution failure response', () => {
      const request: TestExecutionRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        tool_name: 'search',
        parameters: { query: '' },
      };

      const mockResult: TestExecutionResult = {
        success: false,
        status: 'error',
        error: 'Invalid parameters',
        duration_ms: 25.3,
      };

      service.executeTest(request).subscribe((result) => {
        expect(result.success).toBe(false);
        expect(result.error).toBe('Invalid parameters');
      });

      const req = httpMock.expectOne('/api/v1/tools/test/execute');
      req.flush(mockResult);
    });

    it('should propagate HTTP errors', () => {
      const request: TestExecutionRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        tool_name: 'search',
        parameters: {},
      };

      service.executeTest(request).subscribe({
        error: (error) => {
          expect(error.status).toBe(404);
        },
      });

      const req = httpMock.expectOne('/api/v1/tools/test/execute');
      req.flush(
        { detail: 'Tool not found' },
        { status: 404, statusText: 'Not Found' }
      );
    });

    it('should handle 403 permission error', () => {
      const request: TestExecutionRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        tool_name: 'search',
        parameters: {},
      };

      service.executeTest(request).subscribe({
        error: (error) => {
          expect(error.status).toBe(403);
        },
      });

      const req = httpMock.expectOne('/api/v1/tools/test/execute');
      req.flush(
        { detail: 'Only admin or developer roles can test tools' },
        { status: 403, statusText: 'Forbidden' }
      );
    });
  });

  describe('validateParameters', () => {
    it('should call POST /api/v1/tools/test/validate-parameters', () => {
      const request: ParameterValidationRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        parameters: { query: 'test' },
      };

      const mockResult: ParameterValidationResult = {
        valid: true,
      };

      service.validateParameters(request).subscribe((result) => {
        expect(result).toEqual(mockResult);
      });

      const req = httpMock.expectOne('/api/v1/tools/test/validate-parameters');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResult);
    });

    it('should handle validation failure', () => {
      const request: ParameterValidationRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        parameters: { invalid_field: 123 },
      };

      const mockResult: ParameterValidationResult = {
        valid: false,
        error: "'query' is a required property",
      };

      service.validateParameters(request).subscribe((result) => {
        expect(result.valid).toBe(false);
        expect(result.error).toBe("'query' is a required property");
      });

      const req = httpMock.expectOne('/api/v1/tools/test/validate-parameters');
      req.flush(mockResult);
    });

    it('should handle no schema defined message', () => {
      const request: ParameterValidationRequest = {
        tool_id: '123e4567-e89b-12d3-a456-426614174000',
        parameters: {},
      };

      const mockResult: ParameterValidationResult = {
        valid: true,
        message: 'No schema defined',
      };

      service.validateParameters(request).subscribe((result) => {
        expect(result.valid).toBe(true);
        expect(result.message).toBe('No schema defined');
      });

      const req = httpMock.expectOne('/api/v1/tools/test/validate-parameters');
      req.flush(mockResult);
    });

    it('should handle tool not found error', () => {
      const request: ParameterValidationRequest = {
        tool_id: 'nonexistent-id',
        parameters: {},
      };

      service.validateParameters(request).subscribe({
        error: (error) => {
          expect(error.status).toBe(404);
        },
      });

      const req = httpMock.expectOne('/api/v1/tools/test/validate-parameters');
      req.flush(
        { detail: 'Tool not found' },
        { status: 404, statusText: 'Not Found' }
      );
    });
  });
});
