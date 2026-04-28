import { HttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ExecutionResponse, UseCaseExecution } from '../models/use-case.models';
import { UseCaseExecutionService } from './use-case-execution.service';

describe('UseCaseExecutionService', () => {
  let service: UseCaseExecutionService;
  let httpClientSpy: {
    get: jest.Mock;
    post: jest.Mock;
  };

  const mockExecution: UseCaseExecution = {
    use_case_id: 'threat-analysis',
    inputs: {
      query: 'Test query',
    },
    overrides: {
      temperature: 0.7,
      top_k: 10,
      streaming: false,
    },
  };

  const mockExecutionResponse: ExecutionResponse = {
    response: 'Test response',
    sources: [
      {
        document_id: 'doc1',
        title: 'Test Document',
        source: 'test.pdf',
        similarity_score: 0.85,
        chunk_text: 'Test chunk text',
        chunk_index: 0,
        document_type: 'PDF',
        created_at: '2025-01-01T00:00:00Z',
      },
    ],
    metrics: {
      retrieval: {
        top_k: 10,
        hits: 5,
        avg_similarity: 0.8,
        min_similarity: 0.6,
        max_similarity: 0.9,
        retrieval_time_ms: 150,
        total_documents_searched: 1000,
        filtered_documents: 50,
      },
      guard: {
        risk_score: 0.2,
        modified: false,
        processing_time_ms: 50,
      },
      model: {
        model_id: 'gpt-4',
        tokens_in: 100,
        tokens_out: 50,
        latency_ms: 2000,
        temperature: 0.7,
        max_tokens: 1000,
      },
      confidence_score: 0.85,
      overall_status: 'success',
    },
    suggested_actions: [],
    request_id: 'req123',
    execution_time_ms: 2200,
    timestamp: '2025-01-01T00:00:00Z',
  };

  beforeEach(() => {
    const spy = {
      get: jest.fn(),
      post: jest.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        UseCaseExecutionService,
        { provide: HttpClient, useValue: spy },
      ],
    });

    service = TestBed.inject(UseCaseExecutionService);
    httpClientSpy = TestBed.inject(HttpClient) as typeof spy;

    // Mock localStorage
    jest
      .spyOn(localStorage, 'getItem')
      .mockReturnValue('{"user_id": "test-user"}');
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('executeUseCase', () => {
    it('should execute use case and return response', (done) => {
      httpClientSpy.post.mockReturnValue(of(mockExecutionResponse));

      service.executeUseCase(mockExecution).subscribe({
        next: (response) => {
          expect(response).toEqual(mockExecutionResponse);
          expect(httpClientSpy.post).toHaveBeenCalledWith(
            '/api/v1/use-cases/threat-analysis/execute',
            {
              inputs: mockExecution.inputs,
              overrides: mockExecution.overrides,
            }
          );
          done();
        },
        error: done.fail,
      });
    });

    it('should handle execution errors', (done) => {
      const errorResponse = new Error('Execution failed');
      httpClientSpy.post.mockReturnValue(throwError(() => errorResponse));

      service.executeUseCase(mockExecution).subscribe({
        next: done.fail,
        error: (error) => {
          expect(error).toBeInstanceOf(Error);
          done();
        },
      });
    });
  });

  describe('executeUseCaseStreaming', () => {
    it('should return observable for streaming execution', () => {
      const result = service.executeUseCaseStreaming(mockExecution);
      expect(result).toBeDefined();
      expect(typeof result.subscribe).toBe('function');
    });
  });

  describe('cancelExecution', () => {
    it('should cancel execution', (done) => {
      const requestId = 'req123';
      httpClientSpy.post.mockReturnValue(of({}));

      service.cancelExecution(requestId).subscribe({
        next: (response) => {
          expect(response).toEqual({});
          expect(httpClientSpy.post).toHaveBeenCalledWith(
            `/api/v1/use-cases/execute/${requestId}/cancel`,
            {}
          );
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('getExecutionStatus', () => {
    it('should get execution status', (done) => {
      const requestId = 'req123';
      const status = {
        request_id: requestId,
        status: 'processing',
        progress_percentage: 50,
        current_step: 'Processing...',
      };

      httpClientSpy.get.mockReturnValue(of(status));

      service.getExecutionStatus(requestId).subscribe({
        next: (execStatus) => {
          expect(execStatus).toEqual(status);
          expect(httpClientSpy.get).toHaveBeenCalledWith(
            `/api/v1/use-cases/execute/${requestId}/status`
          );
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('ADR-030 compliance', () => {
    it('should not have saveExecutionToHistory method (removed per ADR-030)', () => {
      // ADR-030: History write operations are disabled in Core Edition.
      // The saveExecutionToHistory method has been removed.
      expect(
        (service as Record<string, unknown>)['saveExecutionToHistory']
      ).toBeUndefined();
    });
  });

  describe('observable streams', () => {
    it('should provide execution progress stream', (done) => {
      service.getExecutionProgressStream().subscribe({
        next: (progress) => {
          expect(Array.isArray(progress)).toBeTruthy();
          done();
        },
        error: done.fail,
      });
    });

    it('should provide specific execution progress stream', (done) => {
      const requestId = 'req123';
      service.getExecutionProgressStream(requestId).subscribe({
        next: (progress) => {
          // Should return null initially or progress object
          expect(
            progress === null || typeof progress === 'object'
          ).toBeTruthy();
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('utility methods', () => {
    it('should disconnect WebSocket', () => {
      // This is a void method, just ensure it doesn't throw
      expect(() => service.disconnectWebSocket()).not.toThrow();
    });
  });
});
