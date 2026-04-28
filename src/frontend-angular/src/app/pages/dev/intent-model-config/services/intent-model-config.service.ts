/**
 * Intent Model Configuration Service
 *
 * Service for managing intent-to-model configuration via Development API (ADR-069).
 * Requires developer role or higher.
 */

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  AvailableModel,
  IntentModelDefault,
  IntentModelDefaultWithModel,
  IntentModelSummary,
  UpdateIntentModelRequest,
  IntentModelHistoryEntry,
} from '../models/intent-model-config.models';

@Injectable({
  providedIn: 'root',
})
export class IntentModelConfigService {
  private readonly baseUrl = '/api/v1/development/intent-models';

  constructor(private http: HttpClient) {}

  /**
   * Get summary of all intents with their current model configurations
   */
  getIntentModelSummary(): Observable<IntentModelSummary[]> {
    return this.http.get<IntentModelSummary[]>(`${this.baseUrl}/summary`);
  }

  /**
   * Get list of models available for intent configuration
   */
  getAvailableModels(): Observable<AvailableModel[]> {
    return this.http.get<AvailableModel[]>(
      `${this.baseUrl}/available-models`
    );
  }

  /**
   * Get current active default for a specific intent
   */
  getIntentModelDefault(
    intentCode: string
  ): Observable<IntentModelDefaultWithModel | null> {
    return this.http.get<IntentModelDefaultWithModel | null>(
      `${this.baseUrl}/${intentCode}`
    );
  }

  /**
   * Update the default model for an intent
   */
  updateIntentModelDefault(
    intentCode: string,
    request: UpdateIntentModelRequest
  ): Observable<IntentModelDefault> {
    return this.http.put<IntentModelDefault>(
      `${this.baseUrl}/${intentCode}`,
      request
    );
  }

  /**
   * Get configuration history for an intent
   */
  getIntentModelHistory(
    intentCode: string
  ): Observable<IntentModelHistoryEntry[]> {
    return this.http.get<IntentModelHistoryEntry[]>(
      `${this.baseUrl}/${intentCode}/history`
    );
  }

  /**
   * Refresh the ModelSelector's in-memory cache
   */
  refreshCache(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/refresh-cache`, {});
  }
}
