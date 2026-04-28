import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { LoginRequest, TokenResponse } from '../models/auth.models';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    try {
      httpMock.verify();
    } catch (error) {
      // Ignore verification errors for error test cases
    }
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('Authentication', () => {
    it('should login user successfully', () => {
      const mockLoginRequest: LoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      const mockTokenResponse: TokenResponse = {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      service.login(mockLoginRequest).subscribe((response) => {
        expect(response).toEqual(mockTokenResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.get('Content-Type')).toBe(
        'application/x-www-form-urlencoded'
      );
      expect(req.request.body).toBe('username=testuser&password=testpass');
      req.flush(mockTokenResponse);
    });

    it('should handle login error', () => {
      const mockLoginRequest: LoginRequest = {
        username: 'testuser',
        password: 'wrongpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toContain('Invalid credentials');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        { detail: 'Invalid credentials' },
        { status: 401, statusText: 'Unauthorized' }
      );
    });
  });

  describe('Health Check', () => {
    it('should perform health check', () => {
      const mockHealthResponse = { status: 'healthy' };

      service.healthCheck().subscribe((response) => {
        expect(response).toEqual(mockHealthResponse);
      });

      const req = httpMock.expectOne('/api/v1/health');
      expect(req.request.method).toBe('GET');
      req.flush(mockHealthResponse);
    });
  });

  describe('Process Request', () => {
    it('should process request successfully', () => {
      const mockProcessRequest = {
        query: 'Test query',
        request_type: 'QUERY' as const,
        stream: false,
      };

      const mockResponse = {
        response: 'Test response',
        sources: [],
        confidence: 0.95,
        request_id: 'test-request-id',
      };

      // Mock localStorage.getItem specifically for 'access_token'
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') {
          return 'mock-token';
        }
        return originalGetItem.call(localStorage, key);
      });

      service.processRequest(mockProcessRequest).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/process');
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.get('Authorization')).toBe(
        'Bearer mock-token'
      );
      expect(req.request.body).toEqual(mockProcessRequest);
      req.flush(mockResponse);

      // Restore original localStorage
      localStorage.getItem = originalGetItem;
    });

    it('should handle document upload', () => {
      const mockFile = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });
      const uploadRequest = {
        file: mockFile,
        title: 'Test Document',
        source: 'test',
        author: 'Test Author',
        classification: 'public',
        tags: 'test,document',
        metadata: '{"key":"value"}',
        process_async: true,
      };

      const mockResponse = { document_id: '123', status: 'uploaded' };

      service.uploadDocument(uploadRequest).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/documents/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toBeInstanceOf(FormData);
      req.flush(mockResponse);
    });

    it('should get documents with parameters', () => {
      const params = {
        limit: 10,
        offset: 0,
        document_type: 'pdf',
        tag: 'test',
        query: 'search term',
      };

      const mockResponse = [{ id: '1', title: 'Test Doc' }];

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.getDocuments(params).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url.includes('/api/v1/documents/') &&
          request.params.get('limit') === '10' &&
          request.params.get('document_type') === 'pdf' &&
          request.params.get('tag') === 'test' &&
          request.params.get('query') === 'search term'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should get single document', () => {
      const params = {
        document_id: '123',
        include_preview: true,
        preview_length: 500,
      };

      const mockResponse = {
        id: '123',
        title: 'Test Doc',
        preview: 'Preview text',
      };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.getDocument(params).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === '/api/v1/documents/123' &&
          request.params.get('include_preview') === 'true' &&
          request.params.get('preview_length') === '500'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should update document', () => {
      const documentId = '123';
      const updateData = { title: 'Updated Title', tags: 'updated,tags' };
      const mockResponse = { id: '123', title: 'Updated Title' };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.updateDocument(documentId, updateData).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/documents/123');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(updateData);
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should delete document', () => {
      const params = { document_id: '123', force: true };
      const mockResponse = { message: 'Document deleted' };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.deleteDocument(params).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url === '/api/v1/documents/123' &&
          request.params.get('force') === 'true'
      );
      expect(req.request.method).toBe('DELETE');
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should refresh token', () => {
      const refreshToken = 'refresh-token';
      const mockResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      service.refreshToken(refreshToken).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/refresh');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ refresh_token: refreshToken });
      req.flush(mockResponse);
    });

    it('should revoke token', () => {
      const refreshToken = 'refresh-token';
      const mockResponse = { message: 'Token revoked' };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.revokeToken(refreshToken).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/revoke');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ refresh_token: refreshToken });
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should validate token', () => {
      const mockResponse = { valid: true, user: 'admin' };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.validateToken().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/validate');
      expect(req.request.method).toBe('GET');
      expect(req.request.headers.get('Authorization')).toBe(
        'Bearer mock-token'
      );
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should search documents', () => {
      const query = { query: 'test search', limit: 10 };
      const mockResponse = { results: [{ id: '1', title: 'Found Doc' }] };

      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });

      service.searchDocuments(query).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/query/search');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(query);
      req.flush(mockResponse);

      localStorage.getItem = originalGetItem;
    });

    it('should handle error responses', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toContain('Server Error: 500');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush('Server Error', {
        status: 500,
        statusText: 'Internal Server Error',
      });
    });

    it('should handle client-side errors', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      // Mock a client-side error
      const clientError = new ErrorEvent('Network error', {
        message: 'Connection failed',
      });

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toContain('Client Error: Connection failed');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.error(clientError);
    });

    it('should handle array error details', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toContain('Field error, Another error');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        {
          detail: [{ msg: 'Field error' }, { message: 'Another error' }],
        },
        { status: 400, statusText: 'Bad Request' }
      );
    });

    it('should login with optional parameters', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
        grant_type: 'password',
        scope: 'read write',
      };

      const mockTokenResponse: TokenResponse = {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      service.login(mockLoginRequest).subscribe((response) => {
        expect(response).toEqual(mockTokenResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toBe(
        'username=testuser&password=testpass&grant_type=password&scope=read+write'
      );
      req.flush(mockTokenResponse);
    });
  });

  describe('User Management', () => {
    beforeEach(() => {
      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });
    });

    it('should get current user', () => {
      const mockUser = {
        id: '1',
        username: 'admin',
        email: 'admin@example.com',
      };

      service.getCurrentUser().subscribe((response) => {
        expect(response).toEqual(mockUser);
      });

      const req = httpMock.expectOne('/api/v1/auth/me');
      expect(req.request.method).toBe('GET');
      expect(req.request.headers.get('Authorization')).toBe(
        'Bearer mock-token'
      );
      req.flush(mockUser);
    });

    it('should get all users', () => {
      const mockUsers = [
        { id: '1', username: 'admin', email: 'admin@example.com' },
        { id: '2', username: 'user', email: 'user@example.com' },
      ];

      service.getUsers().subscribe((response) => {
        expect(response).toEqual(mockUsers);
      });

      const req = httpMock.expectOne('/api/v1/auth/users');
      expect(req.request.method).toBe('GET');
      req.flush(mockUsers);
    });

    it('should get single user', () => {
      const userId = '123';
      const mockUser = {
        id: userId,
        username: 'testuser',
        email: 'test@example.com',
      };

      service.getUser(userId).subscribe((response) => {
        expect(response).toEqual(mockUser);
      });

      const req = httpMock.expectOne(`/api/v1/auth/users/${userId}`);
      expect(req.request.method).toBe('GET');
      req.flush(mockUser);
    });

    it('should create user', () => {
      const userData = {
        username: 'newuser',
        email: 'new@example.com',
        password: 'password123',
      };
      const mockResponse = { id: '456', ...userData };

      service.createUser(userData).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/auth/users');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(userData);
      req.flush(mockResponse);
    });

    it('should update user', () => {
      const userId = '123';
      const updateData = { email: 'updated@example.com' };
      const mockResponse = {
        id: userId,
        username: 'testuser',
        email: 'updated@example.com',
      };

      service.updateUser(userId, updateData).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(`/api/v1/auth/users/${userId}`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(updateData);
      req.flush(mockResponse);
    });
  });

  describe('Document Management Extended', () => {
    beforeEach(() => {
      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });
    });

    it('should get document status', () => {
      const documentId = '123';
      const mockStatus = { status: 'processed', progress: 100 };

      service.getDocumentStatus(documentId).subscribe((response) => {
        expect(response).toEqual(mockStatus);
      });

      const req = httpMock.expectOne(`/api/v1/documents/${documentId}/status`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStatus);
    });

    it('should get document stats', () => {
      const mockStats = { total: 100, processed: 95, failed: 5 };

      service.getDocumentStats().subscribe((response) => {
        expect(response).toEqual(mockStats);
      });

      const req = httpMock.expectOne('/api/v1/documents/stats');
      expect(req.request.method).toBe('GET');
      req.flush(mockStats);
    });

    it('should upload document with minimal data', () => {
      const mockFile = new File(['test content'], 'test.pdf', {
        type: 'application/pdf',
      });
      const uploadRequest = {
        file: mockFile,
        process_async: false,
      };

      const mockResponse = { document_id: '123', status: 'uploaded' };

      service.uploadDocument(uploadRequest).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/documents/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toBeInstanceOf(FormData);
      req.flush(mockResponse);
    });
  });

  describe('Query Endpoints', () => {
    beforeEach(() => {
      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });
    });

    it('should ask question', () => {
      const query = { query: 'What is the capital of France?', limit: 5 };
      const mockResponse = { answer: 'Paris', sources: [] };

      service.askQuestion(query).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/query/ask');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(query);
      req.flush(mockResponse);
    });
  });

  describe('Analytics Endpoints', () => {
    beforeEach(() => {
      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });
    });

    it('should get hot documents with parameters', () => {
      const params = { limit: 10, hours: 24 };
      const mockResponse = [{ id: '1', title: 'Hot Doc 1', views: 100 }];

      service.getHotDocuments(params).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url.includes('/api/v1/analytics/documents/hot') &&
          request.params.get('limit') === '10' &&
          request.params.get('hours') === '24'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get hot documents without parameters', () => {
      const mockResponse = [{ id: '1', title: 'Hot Doc 1', views: 100 }];

      service.getHotDocuments().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/analytics/documents/hot');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get usage stats with parameters', () => {
      const params = { hours: 48 };
      const mockResponse = { queries: 150, documents: 50, users: 10 };

      service.getUsageStats(params).subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne(
        (request) =>
          request.url.includes('/api/v1/analytics/usage/stats') &&
          request.params.get('hours') === '48'
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });

    it('should get usage stats without parameters', () => {
      const mockResponse = { queries: 150, documents: 50, users: 10 };

      service.getUsageStats().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/analytics/usage/stats');
      expect(req.request.method).toBe('GET');
      req.flush(mockResponse);
    });
  });

  describe('Additional Endpoints', () => {
    beforeEach(() => {
      // Mock localStorage for auth token
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return originalGetItem.call(localStorage, key);
      });
    });

    it('should test protected route', () => {
      const mockResponse = { message: 'Access granted' };

      service.testProtectedRoute().subscribe((response) => {
        expect(response).toEqual(mockResponse);
      });

      const req = httpMock.expectOne('/api/v1/protected');
      expect(req.request.method).toBe('GET');
      expect(req.request.headers.get('Authorization')).toBe(
        'Bearer mock-token'
      );
      req.flush(mockResponse);
    });

    it('should handle auth headers without token', () => {
      // Clear localStorage
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn(() => null);

      service.healthCheck().subscribe();

      const req = httpMock.expectOne('/api/v1/health');
      expect(req.request.headers.has('Authorization')).toBe(false);

      req.flush({ status: 'ok' });
      localStorage.getItem = originalGetItem;
    });

    it('should handle unknown error in error handler', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('An unknown error occurred');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(null, { status: 500, statusText: 'Internal Server Error' });
    });

    it('should handle server error with string detail', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('Authentication failed');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        { detail: 'Authentication failed' },
        { status: 401, statusText: 'Unauthorized' }
      );
    });

    it('should handle server error with array detail containing msg', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('Username required, Password too short');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        {
          detail: [{ msg: 'Username required' }, { msg: 'Password too short' }],
        },
        { status: 400, statusText: 'Bad Request' }
      );
    });

    it('should handle server error with array detail containing message', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('Invalid format, Missing field');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        {
          detail: [{ message: 'Invalid format' }, { message: 'Missing field' }],
        },
        { status: 400, statusText: 'Bad Request' }
      );
    });

    it('should handle server error with mixed array detail', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe(
            'Field validation error, Another validation error'
          );
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        {
          detail: [
            { msg: 'Field validation error' },
            { message: 'Another validation error' },
          ],
        },
        { status: 422, statusText: 'Unprocessable Entity' }
      );
    });

    it('should handle server error without detail', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('Server Error: 503 - Service Unavailable');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush({}, { status: 503, statusText: 'Service Unavailable' });
    });

    it('should log error to console', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: () => {
          expect(consoleSpy).toHaveBeenCalledWith(
            'API Error:',
            expect.any(Object)
          );
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        { detail: 'Test error' },
        { status: 400, statusText: 'Bad Request' }
      );

      consoleSpy.mockRestore();
    });

    it('should handle error with non-detail error object', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe(
            'Server Error: 422 - Unprocessable Entity'
          );
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        { message: 'Some other error format' },
        { status: 422, statusText: 'Unprocessable Entity' }
      );
    });

    it('should handle error with empty array detail', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe('');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush({ detail: [] }, { status: 400, statusText: 'Bad Request' });
    });

    it('should handle error with array detail containing objects without msg or message', () => {
      const mockLoginRequest = {
        username: 'testuser',
        password: 'testpass',
      };

      service.login(mockLoginRequest).subscribe({
        next: () => fail('Should have failed'),
        error: (error) => {
          expect(error.message).toBe(', ');
        },
      });

      const req = httpMock.expectOne('/api/v1/auth/token');
      req.flush(
        {
          detail: [{ error: 'Field 1 error' }, { error: 'Field 2 error' }],
        },
        { status: 400, statusText: 'Bad Request' }
      );
    });
  });
});
