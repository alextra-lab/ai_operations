import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { TokenType, UserProfile } from '../../core/auth/auth.models';
import { SecureStorageService } from '../../core/services/secure-storage.service';
import {
  ClientInfo,
  ExecutionProgress,
  ExecutionResponse,
  StreamingResponse,
  UseCaseExecution,
} from '../models/use-case.models';
import { SseStreamChunk, SseStreamService } from './sse-stream.service';

@Injectable({
  providedIn: 'root',
})
export class UseCaseExecutionService {
  private readonly baseUrl = '/api/v1/use-cases';
  private readonly wsUrl = 'ws://localhost:8000/ws/use-cases';

  // Real-time execution tracking
  private readonly activeExecutions = new Map<
    string,
    BehaviorSubject<ExecutionProgress>
  >();
  private readonly executionProgress$ = new BehaviorSubject<
    ExecutionProgress[]
  >([]);

  // WebSocket connection for streaming
  private wsConnection?: WebSocket;
  private wsReconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectInterval = 3000;

  constructor(
    private http: HttpClient,
    private storage: SecureStorageService,
    private sseStreamService: SseStreamService
  ) { }

  // ============================================================================
  // Use Case Execution
  // ============================================================================

  /**
   * Execute a use case with standard (non-streaming) response
   */
  executeUseCase(
    execution: UseCaseExecution,
    clientInfo?: ClientInfo
  ): Observable<ExecutionResponse> {
    // Extract use_case_id from execution for the URL path
    const useCaseId = execution.use_case_id;
    if (!useCaseId) {
      return throwError(() => new Error('use_case_id is required'));
    }

    // Build request body with only inputs and overrides (not use_case_id)
    const requestBody = {
      inputs: execution.inputs,
      overrides: execution.overrides,
    };

    // Start tracking execution progress
    const requestId = this.generateRequestId();
    this.startExecutionTracking(requestId, 'STANDARD');

    return this.http
      .post<ExecutionResponse>(
        `${this.baseUrl}/${useCaseId}/execute`,
        requestBody
      )
      .pipe(
        tap((response) => {
          this.updateExecutionProgress(
            requestId,
            'completed',
            100,
            'Execution completed'
          );
          this.cleanupExecution(requestId);
        }),
        catchError((error) => {
          this.updateExecutionProgress(
            requestId,
            'failed',
            0,
            'Execution failed',
            error
          );
          this.cleanupExecution(requestId);
          return this.handleError(error, 'Failed to execute use case');
        })
      );
  }

  /**
   * Execute a use case with streaming response using SSE
   */
  executeUseCaseStreaming(
    execution: UseCaseExecution,
    clientInfo?: ClientInfo
  ): Observable<StreamingResponse> {
    // Start tracking execution progress
    const requestId = this.generateRequestId();
    this.startExecutionTracking(requestId, 'STREAMING');

    // Get auth token
    const token = this.storage.getToken(TokenType.Access);
    if (!token) {
      return throwError(() => new Error('No authentication token'));
    }

    // Extract use_case_id
    const useCaseId = execution.use_case_id;

    // Accumulate full response
    let fullResponse = '';
    let lastChunk: SseStreamChunk | null = null;

    // Use SSE streaming
    return this.sseStreamService
      .streamQuery(
        {
          query: this.extractQueryFromInputs(execution.inputs),
          useCaseId: useCaseId || undefined,
        },
        token
      )
      .pipe(
        map((chunk: SseStreamChunk) => {
          // Accumulate response
          fullResponse += chunk.response || '';
          lastChunk = chunk;

          // Update progress
          this.updateExecutionProgress(
            requestId,
            'processing',
            50,
            'Generating response...'
          );

          // Convert SSE chunk to StreamingResponse format
          const streamingResp: StreamingResponse = {
            type: 'chunk',
            data: chunk.response || '',
            request_id: chunk.request_id || requestId,
            full_response: fullResponse,
            sources: chunk.sources,
            metrics: chunk.metrics,
          };

          return streamingResp;
        }),
        tap({
          complete: () => {
            // Emit final completion event
            this.updateExecutionProgress(
              requestId,
              'completed',
              100,
              'Execution completed'
            );
            this.cleanupExecution(requestId);
          },
          error: (error) => {
            this.updateExecutionProgress(
              requestId,
              'failed',
              0,
              'Execution failed',
              error
            );
            this.cleanupExecution(requestId);
          },
        }),
        catchError((error) =>
          this.handleError(error, 'Failed to stream use case execution')
        )
      );
  }

  /**
   * Extract query text from execution inputs
   */
  private extractQueryFromInputs(inputs: Record<string, any>): string {
    if (!inputs) return '';

    // Try common field names
    if (inputs['query']) return inputs['query'];
    if (inputs['question']) return inputs['question'];
    if (inputs['prompt']) return inputs['prompt'];
    if (inputs['text']) return inputs['text'];

    // Fallback: concatenate all string values
    return Object.values(inputs)
      .filter((v) => typeof v === 'string')
      .join(' ');
  }

  /**
   * Cancel an ongoing execution
   */
  cancelExecution(requestId: string): Observable<void> {
    return this.http
      .post<void>(`${this.baseUrl}/execute/${requestId}/cancel`, {})
      .pipe(
        tap(() => {
          this.updateExecutionProgress(
            requestId,
            'failed',
            0,
            'Execution cancelled'
          );
          this.cleanupExecution(requestId);
        }),
        catchError((error) =>
          this.handleError(error, `Failed to cancel execution ${requestId}`)
        )
      );
  }

  /**
   * Get execution status
   */
  getExecutionStatus(requestId: string): Observable<ExecutionProgress> {
    return this.http
      .get<ExecutionProgress>(`${this.baseUrl}/execute/${requestId}/status`)
      .pipe(
        tap((progress) => {
          const subject = this.activeExecutions.get(requestId);
          if (subject) {
            subject.next(progress);
          }
        }),
        catchError((error) =>
          this.handleError(error, `Failed to get execution status ${requestId}`)
        )
      );
  }

  // ============================================================================
  // Execution History Integration
  // ============================================================================

  // ADR-030: saveExecutionToHistory() removed - history is now recorded by
  // the orchestrator pipeline, not via direct frontend API calls.
  // This enforces the stateless architecture for Core Edition.

  // ============================================================================
  // Observable Streams
  // ============================================================================

  /**
   * Get observable stream of execution progress
   */
  getExecutionProgressStream(): Observable<ExecutionProgress[]> {
    return this.executionProgress$.asObservable();
  }

  /**
   * Get observable stream for specific execution
   */
  getExecutionProgressStreamById(
    requestId: string
  ): Observable<ExecutionProgress | null> {
    const subject = this.activeExecutions.get(requestId);
    return subject
      ? subject.asObservable()
      : new Observable((observer) => observer.next(null));
  }

  // ============================================================================
  // WebSocket Management
  // ============================================================================

  /**
   * Connect to WebSocket for streaming
   */
  private connectWebSocket(): void {
    try {
      this.wsConnection = new WebSocket(this.wsUrl);

      this.wsConnection.onopen = () => {
        this.wsReconnectAttempts = 0;
      };

      this.wsConnection.onclose = (event) => {
        if (this.wsReconnectAttempts < this.maxReconnectAttempts) {
          setTimeout(() => {
            this.wsReconnectAttempts++;
            this.connectWebSocket();
          }, this.reconnectInterval);
        }
      };

      this.wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = undefined;
    }
  }

  // ============================================================================
  // Execution Tracking
  // ============================================================================

  /**
   * Start tracking execution progress
   */
  private startExecutionTracking(
    requestId: string,
    executionType: 'STANDARD' | 'STREAMING'
  ): void {
    const progress: ExecutionProgress = {
      request_id: requestId,
      status: 'pending',
      progress_percentage: 0,
      current_step: `Initializing ${executionType.toLowerCase()} execution...`,
    };

    const subject = new BehaviorSubject<ExecutionProgress>(progress);
    this.activeExecutions.set(requestId, subject);
    this.updateExecutionProgressList();

    // Simulate initial progress
    setTimeout(() => {
      this.updateExecutionProgress(
        requestId,
        'processing',
        10,
        'Validating inputs...'
      );
    }, 100);
  }

  /**
   * Update execution progress
   */
  private updateExecutionProgress(
    requestId: string,
    status: ExecutionProgress['status'],
    progress: number,
    step: string,
    error?: any
  ): void {
    const subject = this.activeExecutions.get(requestId);
    if (subject) {
      const update: ExecutionProgress = {
        request_id: requestId,
        status,
        progress_percentage: progress,
        current_step: step,
        error: error
          ? {
            code: error.status?.toString() || 'EXECUTION_ERROR',
            message: error.message || 'An error occurred during execution',
            timestamp: new Date().toISOString(),
            request_id: requestId,
          }
          : undefined,
      };

      subject.next(update);
      this.updateExecutionProgressList();
    }
  }

  /**
   * Update execution progress list
   */
  private updateExecutionProgressList(): void {
    const allProgress = Array.from(this.activeExecutions.values()).map(
      (subject) => subject.value
    );
    this.executionProgress$.next(allProgress);
  }

  /**
   * Cleanup execution tracking
   */
  private cleanupExecution(requestId: string): void {
    const subject = this.activeExecutions.get(requestId);
    if (subject) {
      subject.complete();
      this.activeExecutions.delete(requestId);
      this.updateExecutionProgressList();
    }

    // Clean up after 30 seconds for completed/failed executions
    setTimeout(() => {
      if (this.activeExecutions.has(requestId)) {
        this.cleanupExecution(requestId);
      }
    }, 30000);
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current user ID from auth service
   */
  private getCurrentUserId(): string {
    // Get user profile from secure storage
    const userProfile = this.storage.getUserProfile<UserProfile>();
    if (userProfile && userProfile.id && this.isValidUUID(userProfile.id)) {
      return userProfile.id;
    }

    // Return a default UUID for anonymous users (testuser)
    return '004b53ae-0d85-45e3-8e6d-f1806baa2640';
  }

  /**
   * Check if a string is a valid UUID
   */
  private isValidUUID(uuid: string): boolean {
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  }

  /**
   * Convert metrics to dictionary format
   */
  private convertMetricsToDict(metrics: any): Record<string, any> {
    if (!metrics) return {};
    if (typeof metrics === 'object' && !Array.isArray(metrics)) {
      return metrics;
    }
    return {};
  }

  /**
   * Convert sources array to dictionary format
   */
  private convertSourcesToDict(sources: any): Record<string, any> {
    if (!sources) return {};
    if (Array.isArray(sources)) {
      return {
        sources: sources,
        count: sources.length,
      };
    }
    if (typeof sources === 'object' && !Array.isArray(sources)) {
      return sources;
    }
    return {};
  }

  /**
   * Get default client info
   */
  private getDefaultClientInfo(): ClientInfo {
    return {
      user_agent: navigator.userAgent,
      client_version: '1.0.0',
    };
  }

  /**
   * Extract query text from execution and response
   */
  private extractQueryText(
    execution: UseCaseExecution,
    response: ExecutionResponse
  ): string {
    // Try to extract from inputs first
    if (execution.inputs && typeof execution.inputs === 'object') {
      const inputs = execution.inputs as any;
      if (inputs.query) return inputs.query;
      if (inputs.question) return inputs.question;
      if (inputs.prompt) return inputs.prompt;
      if (inputs.text) return inputs.text;
    }

    // Fallback to first non-empty string value in inputs
    if (execution.inputs && typeof execution.inputs === 'object') {
      const inputs = execution.inputs as any;
      for (const key in inputs) {
        if (typeof inputs[key] === 'string' && inputs[key].trim().length > 0) {
          return inputs[key];
        }
      }
    }

    // Last resort: use response text or a default
    return response.response || 'Use case execution';
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: any, message: string): Observable<never> {
    console.error('UseCase Execution Service Error:', error);
    return throwError(() => new Error(error.message || message));
  }
}
