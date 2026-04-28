/**
 * Tool Testing Service
 *
 * T6-F4: API client for tool testing endpoints.
 * Provides methods for executing tool tests and validating parameters.
 */

import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Request payload for test execution
 */
export interface TestExecutionRequest {
  tool_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
}

/**
 * Response from test execution endpoint
 */
export interface TestExecutionResult {
  success: boolean;
  status: string;
  result?: unknown;
  error?: string;
  duration_ms: number;
}

/**
 * Request payload for parameter validation
 */
export interface ParameterValidationRequest {
  tool_id: string;
  parameters: Record<string, unknown>;
}

/**
 * Response from parameter validation endpoint
 */
export interface ParameterValidationResult {
  valid: boolean;
  message?: string;
  error?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ToolTestingService {
  private readonly baseUrl = '/api/v1/tools/test';
  private readonly http = inject(HttpClient);

  /**
   * Execute a test call against a tool
   * @param request - Test execution parameters
   * @returns Observable with execution result
   */
  executeTest(request: TestExecutionRequest): Observable<TestExecutionResult> {
    return this.http.post<TestExecutionResult>(
      `${this.baseUrl}/execute`,
      request
    );
  }

  /**
   * Validate parameters against a tool's schema without execution
   * @param request - Validation request
   * @returns Observable with validation result
   */
  validateParameters(
    request: ParameterValidationRequest
  ): Observable<ParameterValidationResult> {
    return this.http.post<ParameterValidationResult>(
      `${this.baseUrl}/validate-parameters`,
      request
    );
  }
}
