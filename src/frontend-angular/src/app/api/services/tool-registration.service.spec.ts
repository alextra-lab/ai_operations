import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  RegistrationSessionResponse,
  ToolRegistrationPhase,
  ToolRegistrationRequest,
  ToolRegistrationResponse,
  ToolRegistrationService,
} from './tool-registration.service';

describe('ToolRegistrationService', () => {
  let service: ToolRegistrationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ToolRegistrationService],
    });

    service = TestBed.inject(ToolRegistrationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('processPhase', () => {
    it('should send POST request with correct data', () => {
      const request: ToolRegistrationRequest = {
        session_id: null,
        phase: ToolRegistrationPhase.BASIC_INFO,
        data: {
          tool_id: 'test_tool',
          name: 'Test Tool',
          category: 'database',
          tool_purpose: 'orchestrator',
          service_location: 'orchestrator',
        },
      };

      const mockResponse: ToolRegistrationResponse = {
        session_id: 'test_session_123',
        current_phase: ToolRegistrationPhase.BASIC_INFO,
        next_phase: ToolRegistrationPhase.MCP_CONFIG,
        validation_errors: {},
        can_proceed: true,
        message: 'Basic info validated',
      };

      service.processPhase(request).subscribe((response) => {
        expect(response).toEqual(mockResponse);
        expect(response.session_id).toBe('test_session_123');
        expect(response.can_proceed).toBe(true);
      });

      const req = httpMock.expectOne('/api/v1/admin/tools/register');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(request);
      req.flush(mockResponse);
    });

    it('should handle validation errors', () => {
      const request: ToolRegistrationRequest = {
        session_id: 'test_session_123',
        phase: ToolRegistrationPhase.BASIC_INFO,
        data: {
          tool_id: 'INVALID',
        },
      };

      const mockResponse: ToolRegistrationResponse = {
        session_id: 'test_session_123',
        current_phase: ToolRegistrationPhase.BASIC_INFO,
        next_phase: null,
        validation_errors: {
          tool_id: ['Invalid format'],
        },
        can_proceed: false,
        message: 'Validation failed',
      };

      service.processPhase(request).subscribe((response) => {
        expect(response.can_proceed).toBe(false);
        expect(response.validation_errors).toEqual({
          tool_id: ['Invalid format'],
        });
      });

      const req = httpMock.expectOne('/api/v1/admin/tools/register');
      req.flush(mockResponse);
    });
  });

  describe('getSession', () => {
    it('should send GET request for session', () => {
      const sessionId = 'test_session_123';
      const mockResponse: RegistrationSessionResponse = {
        session_id: sessionId,
        current_phase: ToolRegistrationPhase.MCP_CONFIG,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-01T01:00:00Z',
        collected_data: {
          basic_info: { tool_id: 'test_tool' },
        },
        validation_status: {
          basic_info: true,
        },
      };

      service.getSession(sessionId).subscribe((response) => {
        expect(response).toEqual(mockResponse);
        expect(response.session_id).toBe(sessionId);
      });

      const req = httpMock.expectOne(
        `/api/v1/admin/tools/register/session/${sessionId}`
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('cancelRegistration', () => {
    it('should send DELETE request to cancel registration', () => {
      const sessionId = 'test_session_123';

      service.cancelRegistration(sessionId).subscribe((response) => {
        expect(response).toBeUndefined();
      });

      const req = httpMock.expectOne(
        `/api/v1/admin/tools/register/session/${sessionId}`
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(null);
    });
  });
});
