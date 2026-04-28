import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import {
  UseCase,
  UseCaseConfig,
  UseCaseHistory,
  UseCaseHistoryRequest,
  UseCaseHistoryResponse,
  UseCaseListResponse,
} from '../models/use-case.models';

@Injectable({
  providedIn: 'root',
})
export class UseCaseService {
  private readonly baseUrl = '/api/v1/use-cases';
  private readonly cache = new Map<
    string,
    { data: any; timestamp: number; ttl: number }
  >();
  private readonly defaultCacheTTL = 300000; // 5 minutes

  // Real-time use case tracking
  private readonly useCases$ = new BehaviorSubject<UseCase[]>([]);
  private readonly categories$ = new BehaviorSubject<string[]>([]);

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Use Case Management
  // ============================================================================

  /**
   * Get all available use cases for the current user (RBAC-filtered)
   */
  getAvailableUseCases(): Observable<UseCase[]> {
    const cacheKey = 'available_use_cases';
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http.get<UseCaseListResponse>(`${this.baseUrl}/available`).pipe(
      map((response) => response.use_cases),
      tap((useCases) => {
        this.cacheData(cacheKey, useCases);
        this.useCases$.next(useCases);
        this.updateCategories(useCases);
      }),
      catchError((error) =>
        this.handleError(error, 'Failed to fetch available use cases')
      )
    );
  }

  /**
   * Get a specific use case by ID
   */
  getUseCase(useCaseId: string): Observable<UseCase> {
    const cacheKey = `use_case_${useCaseId}`;
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http.get<UseCase>(`${this.baseUrl}/${useCaseId}`).pipe(
      tap((useCase) => this.cacheData(cacheKey, useCase)),
      catchError((error) =>
        this.handleError(error, `Failed to fetch use case ${useCaseId}`)
      )
    );
  }

  /**
   * Get use case configuration
   */
  getUseCaseConfig(useCaseId: string): Observable<UseCaseConfig> {
    const cacheKey = `use_case_config_${useCaseId}`;
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http
      .get<{
        use_case_id: string;
        name: string;
        description: string;
        category: string;
        intent_type: string;
        config: any;
      }>(`${this.baseUrl}/${useCaseId}/config`)
      .pipe(
        map((response) => {
          // Transform backend response to match UseCaseConfig interface
          const config = response.config;

          return {
            use_case_id: response.use_case_id,
            name: response.name,
            description: response.description || '',
            category: response.category || '',
            intent_type: response.intent_type,
            template_config: {
              input_fields: config.input_fields || [],
              output_format: config.output_format || 'text',
              validation_rules: config.validation_rules || [],
              examples: config.examples || [],
            },
            visibility_config: {
              roles: config.visibility?.roles ?? [],
              tags: config.visibility?.tags ?? [],
              is_public: config.visibility?.is_public ?? false,
            },
            execution_config: {
              default_model: config.models?.llm ?? '',
              default_temperature: config.generation_params?.temperature ?? 0.7,
              default_top_k: config.rag?.top_k ?? 10,
              default_similarity_threshold:
                config.rag?.similarity_threshold ?? 0.7,
              supports_streaming: config.policies?.streaming_enabled ?? false,
              max_execution_time_ms: 30000,
            },
            ui_config: {
              icon: 'description',
              color: 'primary',
              layout: 'single',
              show_metrics: true,
              show_sources: true,
              show_suggestions: false,
              enable_history: true,
            },
            output_contract: config.output_contract
              ? {
                  format: config.output_contract.format ?? 'text',
                  validation_mode:
                    config.output_contract.validation_mode ?? 'best_effort',
                  output_schema: config.output_contract.output_schema ?? null,
                  template_id: config.output_contract.template_id ?? null,
                }
              : undefined,
          } as UseCaseConfig;
        }),
        tap((config) => this.cacheData(cacheKey, config)),
        catchError((error) =>
          this.handleError(
            error,
            `Failed to fetch config for use case ${useCaseId}`
          )
        )
      );
  }

  /**
   * Search use cases by query, category, or tags
   */
  searchUseCases(
    query: string,
    filters?: {
      category?: string;
      tags?: string[];
      intent_type?: string;
    }
  ): Observable<UseCase[]> {
    let params = new HttpParams();
    params = params.set('query', query);

    if (filters?.category) {
      params = params.set('category', filters.category);
    }
    if (filters?.tags?.length) {
      params = params.set('tags', filters.tags.join(','));
    }
    if (filters?.intent_type) {
      params = params.set('intent_type', filters.intent_type);
    }

    return this.http
      .get<UseCaseListResponse>(`${this.baseUrl}/search`, { params })
      .pipe(
        map((response) => response.use_cases),
        catchError((error) =>
          this.handleError(error, 'Failed to search use cases')
        )
      );
  }

  /**
   * Get use cases by category
   */
  getUseCasesByCategory(category: string): Observable<UseCase[]> {
    const cacheKey = `use_cases_category_${category}`;
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http
      .get<UseCaseListResponse>(`${this.baseUrl}/category/${category}`)
      .pipe(
        map((response) => response.use_cases),
        tap((useCases) => this.cacheData(cacheKey, useCases)),
        catchError((error) =>
          this.handleError(
            error,
            `Failed to fetch use cases for category ${category}`
          )
        )
      );
  }

  /**
   * Get all available categories
   */
  getCategories(): Observable<string[]> {
    const cacheKey = 'use_case_categories';
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    return this.http.get<string[]>(`${this.baseUrl}/categories`).pipe(
      tap((categories) => {
        this.cacheData(cacheKey, categories);
        this.categories$.next(categories);
      }),
      catchError((error) =>
        this.handleError(error, 'Failed to fetch categories')
      )
    );
  }

  // ============================================================================
  // Use Case History Management
  // ============================================================================

  /**
   * Get execution history for a use case
   */
  getUseCaseHistory(
    request: UseCaseHistoryRequest = {}
  ): Observable<UseCaseHistoryResponse> {
    const cacheKey = this.generateCacheKey('history', request);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    let params = new HttpParams();
    if (request.use_case_id)
      params = params.set('use_case_id', request.use_case_id);
    if (request.user_id) params = params.set('user_id', request.user_id);
    if (request.status) params = params.set('status', request.status);
    if (request.limit) params = params.set('limit', request.limit.toString());
    if (request.offset)
      params = params.set('offset', request.offset.toString());
    if (request.sort_by) params = params.set('sort_by', request.sort_by);
    if (request.sort_order)
      params = params.set('sort_order', request.sort_order);
    if (request.tags?.length)
      params = params.set('tags', request.tags.join(','));
    if (request.is_favorite !== undefined)
      params = params.set('is_favorite', request.is_favorite.toString());
    if (request.date_range) {
      params = params.set('start_date', request.date_range.start_date);
      params = params.set('end_date', request.date_range.end_date);
    }

    return this.http
      .get<UseCaseHistoryResponse>(`${this.baseUrl}/history`, { params })
      .pipe(
        tap((response) => this.cacheData(cacheKey, response)),
        catchError((error) =>
          this.handleError(error, 'Failed to fetch use case history')
        )
      );
  }

  /**
   * Get a specific history entry
   */
  getHistoryEntry(historyId: string): Observable<UseCaseHistory> {
    return this.http
      .get<UseCaseHistory>(`${this.baseUrl}/history/${historyId}`)
      .pipe(
        catchError((error) =>
          this.handleError(error, `Failed to fetch history entry ${historyId}`)
        )
      );
  }

  /**
   * Fork a history entry (create new execution with modifications)
   */
  forkHistoryEntry(
    historyId: string,
    modifications: any
  ): Observable<UseCaseHistory> {
    return this.http
      .post<UseCaseHistory>(
        `${this.baseUrl}/history/${historyId}/fork`,
        modifications
      )
      .pipe(
        tap(() => this.invalidateCache('history')),
        catchError((error) =>
          this.handleError(error, `Failed to fork history entry ${historyId}`)
        )
      );
  }

  /**
   * Update history entry (tags, favorites, etc.)
   */
  updateHistoryEntry(
    historyId: string,
    updates: Partial<UseCaseHistory>
  ): Observable<UseCaseHistory> {
    return this.http
      .patch<UseCaseHistory>(`${this.baseUrl}/history/${historyId}`, updates)
      .pipe(
        tap(() => this.invalidateCache('history')),
        catchError((error) =>
          this.handleError(error, `Failed to update history entry ${historyId}`)
        )
      );
  }

  /**
   * Delete history entry
   */
  deleteHistoryEntry(historyId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/history/${historyId}`).pipe(
      tap(() => this.invalidateCache('history')),
      catchError((error) =>
        this.handleError(error, `Failed to delete history entry ${historyId}`)
      )
    );
  }

  // ============================================================================
  // Observable Streams
  // ============================================================================

  /**
   * Get observable stream of use cases
   */
  getUseCasesStream(): Observable<UseCase[]> {
    return this.useCases$.asObservable();
  }

  /**
   * Get observable stream of categories
   */
  getCategoriesStream(): Observable<string[]> {
    return this.categories$.asObservable();
  }

  // ============================================================================
  // Cache Management
  // ============================================================================

  /**
   * Clear all cached data
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Invalidate cache for specific prefix
   */
  invalidateCache(prefix: string, suffix?: string): void {
    const keysToDelete: string[] = [];
    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        if (!suffix || key.endsWith(suffix)) {
          keysToDelete.push(key);
        }
      }
    }
    keysToDelete.forEach((key) => this.cache.delete(key));
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Get cached data if valid
   */
  private getCachedData(key: string): any | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < cached.ttl) {
      return cached.data;
    }
    if (cached) {
      this.cache.delete(key);
    }
    return null;
  }

  /**
   * Cache data with TTL
   */
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

  /**
   * Generate cache key from prefix and data
   */
  private generateCacheKey(prefix: string, data: any): string {
    return `${prefix}:${JSON.stringify(data)}`;
  }

  /**
   * Update categories from use cases
   */
  private updateCategories(useCases: UseCase[]): void {
    const categories = Array.from(
      new Set(useCases.map((uc) => uc.category))
    ).sort();
    this.categories$.next(categories);
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: any, message: string): Observable<never> {
    console.error('UseCase Service Error:', error);
    return throwError(() => new Error(error.message || message));
  }
}
