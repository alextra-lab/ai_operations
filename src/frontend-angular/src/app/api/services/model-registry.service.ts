import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import {
  Model,
  ModelDetailedResponse,
  ModelListResponse,
  ModelRecommendation,
  ModelSelectionRequest,
} from '../models/model-registry.models';

@Injectable({
  providedIn: 'root',
})
export class ModelRegistryService {
  private readonly baseUrl = '/api/v1/models';
  private readonly cache = new Map<
    string,
    { data: any; timestamp: number; ttl: number }
  >();
  private readonly defaultCacheTTL = 300000; // 5 minutes

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Model Registry Operations
  // ============================================================================

  /**
   * List available models with filtering and pagination
   */
  listModels(
    provider?: string,
    modelType?: string,
    availableOnly = true,
    includeDeprecated = false,
    includeHidden = false,
    page = 1,
    size = 50
  ): Observable<ModelListResponse> {
    const cacheKey = `models_list_${provider}_${modelType}_${availableOnly}_${includeDeprecated}_${includeHidden}_${page}_${size}`;
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    let params = new HttpParams()
      .set('available_only', availableOnly.toString())
      .set('include_deprecated', includeDeprecated.toString())
      .set('include_hidden', includeHidden.toString())
      .set('page', page.toString())
      .set('size', size.toString());

    if (provider) {
      params = params.set('provider', provider);
    }
    if (modelType) {
      params = params.set('model_type', modelType);
    }

    return this.http.get<ModelListResponse>(this.baseUrl, { params }).pipe(
      tap((response) => this.cacheData(cacheKey, response)),
      catchError((error) => this.handleError(error, 'Failed to fetch models'))
    );
  }

  /**
   * Get detailed model information by database ID (UUID)
   */
  getModel(id: string): Observable<ModelDetailedResponse> {
    const cacheKey = `model_${id}`;
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http.get<ModelDetailedResponse>(`${this.baseUrl}/${id}`).pipe(
      tap((model) => this.cacheData(cacheKey, model)),
      catchError((error) =>
        this.handleError(error, `Failed to fetch model with ID ${id}`)
      )
    );
  }

  /**
   * Get model recommendations for use case
   */
  recommendModels(
    request: ModelSelectionRequest
  ): Observable<ModelRecommendation[]> {
    return this.http
      .post<ModelRecommendation[]>(`${this.baseUrl}/recommend`, request)
      .pipe(
        catchError((error) =>
          this.handleError(error, 'Failed to get model recommendations')
        )
      );
  }

  /**
   * Sync models with inference server (admin only)
   */
  syncModels(): Observable<{
    status: string;
    synced_models: number;
    message: string;
  }> {
    return this.http
      .post<{
        status: string;
        synced_models: number;
        message: string;
      }>(`${this.baseUrl}/sync`, {})
      .pipe(
        tap(() => this.clearCache()), // Clear cache after sync
        catchError((error) => this.handleError(error, 'Failed to sync models'))
      );
  }

  /**
   * Update model metadata (admin only) by database ID (UUID)
   */
  updateModelMetadata(
    id: string,
    updates: any
  ): Observable<ModelDetailedResponse> {
    return this.http
      .patch<ModelDetailedResponse>(`${this.baseUrl}/${id}/metadata`, updates)
      .pipe(
        tap(() => {
          this.clearModelCache(id);
          this.clearCache(); // Clear list cache too
        }),
        catchError((error) =>
          this.handleError(error, 'Failed to update model metadata')
        )
      );
  }

  /**
   * Delete a model from registry (admin only) by database ID (UUID)
   */
  deleteModel(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`).pipe(
      tap(() => {
        this.clearModelCache(id);
        this.clearCache();
      }),
      catchError((error) => this.handleError(error, 'Failed to delete model'))
    );
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Get all available LLM models (convenience method)
   */
  getLLMModels(): Observable<Model[]> {
    return this.listModels(undefined, 'llm', true, false, false, 1, 100).pipe(
      map((response) => response.models)
    );
  }

  /**
   * Get all embedding models (convenience method)
   */
  getEmbeddingModels(): Observable<Model[]> {
    return this.listModels(
      undefined,
      'embedding',
      true,
      false,
      false,
      1,
      100
    ).pipe(map((response) => response.models));
  }

  /**
   * Clear all cached data
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Clear cached data for specific model
   */
  clearModelCache(modelId: string): void {
    this.cache.delete(`model_${modelId}`);
  }

  // ============================================================================
  // Private Helpers
  // ============================================================================

  private getCachedData(key: string): any | null {
    const cached = this.cache.get(key);
    if (!cached) {
      return null;
    }

    const now = Date.now();
    if (now - cached.timestamp > cached.ttl) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  private cacheData(
    key: string,
    data: any,
    ttl: number = this.defaultCacheTTL
  ): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  private handleError(error: any, userMessage: string): Observable<never> {
    console.error(`${userMessage}:`, error);
    throw error;
  }
}
