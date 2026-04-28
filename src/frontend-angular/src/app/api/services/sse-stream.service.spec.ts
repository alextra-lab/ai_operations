import { TestBed } from '@angular/core/testing';
import { SseStreamChunk, SseStreamService } from './sse-stream.service';

describe('SseStreamService', () => {
  let service: SseStreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SseStreamService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('streamQuery', () => {
    it('should parse SSE data chunks correctly', (done) => {
      const chunks: SseStreamChunk[] = [];

      // Mock fetch for testing
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          body: new ReadableStream({
            start(controller) {
              // Simulate SSE chunks
              const encoder = new TextEncoder();

              controller.enqueue(
                encoder.encode(
                  'data: {"response": "Hello", "request_id": "123"}\n\n'
                )
              );
              controller.enqueue(
                encoder.encode(
                  'data: {"response": " World", "request_id": "123"}\n\n'
                )
              );
              controller.close();
            },
          }),
        } as Response)
      );

      service.streamQuery({ query: 'test query' }, 'test-token').subscribe({
        next: (chunk) => {
          chunks.push(chunk);
        },
        complete: () => {
          expect(chunks.length).toBe(2);
          expect(chunks[0].response).toBe('Hello');
          expect(chunks[1].response).toBe(' World');
          done();
        },
        error: done.fail,
      });
    });

    it('should handle HTTP errors', (done) => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
        } as Response)
      );

      service.streamQuery({ query: 'test query' }, 'test-token').subscribe({
        next: () => done.fail('Should not emit'),
        error: (error) => {
          expect(error.message).toContain('500');
          done();
        },
      });
    });

    it('should handle malformed JSON gracefully', (done) => {
      const chunks: SseStreamChunk[] = [];

      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          body: new ReadableStream({
            start(controller) {
              const encoder = new TextEncoder();

              // Valid chunk
              controller.enqueue(
                encoder.encode('data: {"response": "Valid"}\n\n')
              );

              // Invalid JSON (should be skipped)
              controller.enqueue(encoder.encode('data: {invalid json}\n\n'));

              // Another valid chunk
              controller.enqueue(
                encoder.encode('data: {"response": "Also Valid"}\n\n')
              );

              controller.close();
            },
          }),
        } as Response)
      );

      service.streamQuery({ query: 'test' }, 'token').subscribe({
        next: (chunk) => chunks.push(chunk),
        complete: () => {
          // Should have 2 valid chunks (malformed one skipped)
          expect(chunks.length).toBe(2);
          expect(chunks[0].response).toBe('Valid');
          expect(chunks[1].response).toBe('Also Valid');
          done();
        },
        error: done.fail,
      });
    });
  });

  describe('streamQueryWithCancellation', () => {
    it('should support cancellation via AbortController', (done) => {
      const abortController = new AbortController();

      global.fetch = jest.fn((_url: string, options?: RequestInit) => {
        const signal = options?.signal;
        return new Promise<Response>((_resolve, reject) => {
          const onAbort = (): void => {
            reject(new DOMException('Aborted', 'AbortError'));
          };
          if (signal?.aborted) {
            onAbort();
            return;
          }
          signal?.addEventListener?.('abort', onAbort);
        });
      });

      let emittedChunks = 0;

      service
        .streamQueryWithCancellation(
          { query: 'test' },
          'token',
          abortController.signal
        )
        .subscribe({
          next: () => emittedChunks++,
          complete: () => {
            expect(emittedChunks).toBe(0);
            done();
          },
          error: done.fail,
        });

      setTimeout(() => abortController.abort(), 10);
    });
  });
});
