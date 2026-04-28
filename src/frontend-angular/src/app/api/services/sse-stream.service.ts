import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Server-Sent Events (SSE) Streaming Service
 *
 * Handles streaming responses from backend using SSE format.
 * Backend endpoint: POST /api/v1/process with stream=true
 * Response format: text/event-stream with "data: {...}" lines
 */

export interface SseStreamOptions {
  query: string;
  sessionId?: string | null; // Client-owned session ID for ephemeral cache
  threadId?: string | null; // Deprecated in stateless v1
  discussionId?: string;
  useCaseId?: string;
  requestType?: string;
  context?: Record<string, any>;
}

export interface SseStreamChunk {
  response: string;
  sources?: any[];
  confidence?: number;
  metrics?: any;
  suggested_actions?: any;
  request_id?: string;
}

@Injectable({
  providedIn: 'root',
})
export class SseStreamService {
  private readonly baseUrl = '/api/v1/process';

  constructor() {}

  /**
   * Stream query response using Server-Sent Events
   *
   * @param options - Stream configuration
   * @param token - JWT bearer token for authentication
   * @returns Observable of response chunks
   */
  streamQuery(
    options: SseStreamOptions,
    token: string
  ): Observable<SseStreamChunk> {
    return new Observable<SseStreamChunk>((observer) => {
      let isCompleted = false;

      // Build request body (stateless with ephemeral cache)
      const requestBody = {
        query: options.query,
        stream: true,
        session_id: options.sessionId || null, // Client-owned session ID for cache
        // Removed: thread_id (stateless architecture - ADR-030)
        discussion_id: options.discussionId || null,
        use_case_id: options.useCaseId || null,
        request_type: options.requestType || null,
        context: options.context || null,
      };

      // Use Fetch API for SSE streaming
      fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(requestBody),
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          if (!response.body) {
            throw new Error('No response body available');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                if (!isCompleted) {
                  observer.complete();
                  isCompleted = true;
                }
                break;
              }

              // Decode chunk and add to buffer
              buffer += decoder.decode(value, { stream: true });

              // Process complete lines
              const lines = buffer.split('\n');
              buffer = lines.pop() || ''; // Keep incomplete line

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const jsonStr = line.substring(6); // Remove "data: "
                    const chunk: SseStreamChunk = JSON.parse(jsonStr);
                    observer.next(chunk);
                  } catch (parseError) {
                    console.error('SSE parse error:', parseError, line);
                    // Continue processing other chunks
                  }
                }
                // Ignore comment lines and empty lines
              }
            }
          } catch (readError) {
            if (!isCompleted) {
              observer.error(readError);
              isCompleted = true;
            }
          }
        })
        .catch((error) => {
          if (!isCompleted) {
            observer.error(error);
            isCompleted = true;
          }
        });

      // Cleanup function for unsubscribe
      return () => {
        // Note: Fetch API doesn't support request cancellation well
        // In production, consider using AbortController
        if (!isCompleted) {
          isCompleted = true;
        }
      };
    });
  }

  /**
   * Stream query with cancellation support using AbortController
   *
   * @param options - Stream configuration
   * @param token - JWT bearer token
   * @param signal - AbortSignal for cancellation
   * @returns Observable of response chunks
   */
  streamQueryWithCancellation(
    options: SseStreamOptions,
    token: string,
    signal: AbortSignal
  ): Observable<SseStreamChunk> {
    return new Observable<SseStreamChunk>((observer) => {
      let isCompleted = false;

      // Build request body (stateless with ephemeral cache)
      const requestBody = {
        query: options.query,
        stream: true,
        session_id: options.sessionId || null, // Client-owned session ID for cache
        // Removed: thread_id (stateless architecture - ADR-030)
        discussion_id: options.discussionId || null,
        use_case_id: options.useCaseId || null,
        request_type: options.requestType || null,
        context: options.context || null,
      };

      fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(requestBody),
        signal: signal, // AbortSignal for cancellation
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          if (!response.body) {
            throw new Error('No response body available');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                if (!isCompleted) {
                  observer.complete();
                  isCompleted = true;
                }
                break;
              }

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const jsonStr = line.substring(6);
                    const chunk: SseStreamChunk = JSON.parse(jsonStr);
                    observer.next(chunk);
                  } catch (parseError) {
                    console.error('SSE parse error:', parseError);
                  }
                }
              }
            }
          } catch (readError) {
            if (!isCompleted) {
              observer.error(readError);
              isCompleted = true;
            }
          }
        })
        .catch((error) => {
          if (!isCompleted) {
            // AbortError is normal when cancelled
            if (error.name === 'AbortError') {
              observer.complete();
            } else {
              observer.error(error);
            }
            isCompleted = true;
          }
        });

      return () => {
        if (!isCompleted) {
          isCompleted = true;
        }
      };
    });
  }
}
