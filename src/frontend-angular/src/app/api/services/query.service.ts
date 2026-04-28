import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError, timer } from 'rxjs';
import { catchError, retry, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  QueryConfiguration,
  QueryError,
  QueryHistory,
  QueryHistoryRequest,
  QueryHistoryResponse,
  QueryProgressUpdate,
  QueryStatus,
  QueryType,
  SemanticSearchRequest,
  SemanticSearchResponse,
} from '../models/query.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class QueryService {
  private readonly queryBaseUrl = `${environment.apiBaseUrl}/query`;
  private readonly historyBaseUrl = `${environment.apiBaseUrl}/query-history`;
  private readonly cache = new Map<
    string,
    { data: any; timestamp: number; ttl: number }
  >();
  private readonly defaultCacheTTL = 300000; // 5 minutes

  // Real-time query tracking
  private readonly activeQueries = new Map<
    string,
    BehaviorSubject<QueryProgressUpdate>
  >();
  private readonly queryProgress$ = new BehaviorSubject<QueryProgressUpdate[]>(
    []
  );

  constructor(
    private http: HttpClient,
    private apiService: ApiService
  ) {}

  // Semantic Search Methods
  search(request: SemanticSearchRequest): Observable<SemanticSearchResponse> {
    const cacheKey = this.generateCacheKey('search', request);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    // Start tracking query progress
    const queryId = this.generateQueryId();
    this.startQueryTracking(queryId, 'SEMANTIC_SEARCH');

    // Use the /query/search endpoint for retrieval-only semantic search (no LLM)
    const searchRequest = {
      query: request.query,
      limit: request.limit || 10,
      filters: request.filters,
      threshold: request.threshold ?? 0.0,
    };

    return this.http
      .post<SemanticSearchResponse>(
        `${environment.apiBaseUrl}/query/search`,
        searchRequest
      )
      .pipe(
        tap((response) => {
          this.updateQueryProgress(
            queryId,
            'COMPLETED',
            100,
            'Search completed'
          );
          this.cacheData(cacheKey, response);
        }),
        catchError((error) => {
          this.updateQueryProgress(
            queryId,
            'FAILED',
            0,
            'Search failed',
            error
          );
          return this.handleQueryError(error, 'Semantic search failed');
        }),
        retry(2)
      );
  }

  // Transformation logic removed - backend ResponseTransformer now provides
  // frontend-compatible format directly from /query/search endpoint

  // Query History Methods
  getQueryHistory(
    request: QueryHistoryRequest = {}
  ): Observable<QueryHistoryResponse> {
    const cacheKey = this.generateCacheKey('history', request);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    let params = new HttpParams();
    if (request.limit) params = params.set('limit', request.limit.toString());
    if (request.offset)
      params = params.set('offset', request.offset.toString());
    if (request.use_case_id)
      params = params.set('use_case_id', request.use_case_id);
    if (request.intent_type)
      params = params.set('intent_type', request.intent_type);
    if (request.response_status)
      params = params.set('response_status', request.response_status);
    if (request.search_query)
      params = params.set('search_query', request.search_query);

    return this.http
      .get<QueryHistoryResponse>(`${this.historyBaseUrl}`, { params })
      .pipe(
        tap((response) => this.cacheData(cacheKey, response)),
        catchError((error) =>
          this.handleQueryError(error, 'Failed to fetch query history')
        ),
        retry(2)
      );
  }

  /**
   * @deprecated ADR-030: History write operations are disabled in Core Edition.
   * History is now recorded by the orchestrator pipeline internally.
   * This method will return 501 Not Implemented from the backend.
   */
  saveQueryToHistory(
    queryData: Partial<QueryHistory>
  ): Observable<QueryHistory> {
    console.warn(
      'saveQueryToHistory is deprecated (ADR-030): ' +
        'History is recorded by orchestrator pipeline in Core Edition.'
    );
    return this.http
      .post<QueryHistory>(`${this.historyBaseUrl}`, queryData)
      .pipe(
        tap((query) => {
          // Invalidate cache
          this.invalidateCache('history');
          this.invalidateCache('query', query.id);
        }),
        catchError((error) =>
          this.handleQueryError(error, 'Failed to save query to history')
        ),
        retry(2)
      );
  }

  // Configuration Methods
  getQueryConfiguration(): Observable<QueryConfiguration> {
    const cacheKey = this.generateCacheKey('config', 'global');
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    // Return default configuration for now
    const defaultConfig: QueryConfiguration = {
      default_search_type: 'SEMANTIC_SEARCH',
      default_limit: 25,
      max_limit: 100,
      default_filters: {},
      available_sort_options: [
        { field: 'relevance', order: 'RELEVANCE' },
        { field: 'date', order: 'DATE_DESC' },
        { field: 'title', order: 'TITLE_ASC' },
      ],
      supported_file_types: ['PDF', 'DOCX', 'TXT', 'MD'],
      max_query_length: 1000,
      cache_settings: {
        enabled: true,
        ttl_seconds: 300,
        max_entries: 100,
      },
      real_time_settings: {
        enabled: true,
        update_interval_ms: 1000,
        max_concurrent_queries: 5,
      },
    };

    return of(defaultConfig);
  }

  // Utility Methods
  searchSuggestions(query: string, limit = 10): Observable<string[]> {
    if (!query || query.length < 2) {
      return of([]);
    }

    const cacheKey = this.generateCacheKey('suggestions', query);
    const cached = this.getCachedData(cacheKey);

    if (cached) {
      return of(cached);
    }

    // Mock suggestions for now
    const mockSuggestions = [
      'security vulnerabilities in network protocols',
      'cybersecurity best practices',
      'threat intelligence analysis',
      'incident response procedures',
      'data breach prevention',
    ]
      .filter((s) => s.toLowerCase().includes(query.toLowerCase()))
      .slice(0, limit);

    return of(mockSuggestions);
  }

  // Cache Management
  clearCache(): void {
    this.cache.clear();
  }

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

  private generateCacheKey(prefix: string, data: any): string {
    return `${prefix}:${JSON.stringify(data)}`;
  }

  private invalidateCache(prefix: string, suffix?: string): void {
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

  private generateQueryId(): string {
    return `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private startQueryTracking(queryId: string, queryType: QueryType): void {
    const progressUpdate: QueryProgressUpdate = {
      query_id: queryId,
      status: 'PENDING',
      progress_percentage: 0,
      current_step: 'Initializing query...',
    };

    const subject = new BehaviorSubject<QueryProgressUpdate>(progressUpdate);
    this.activeQueries.set(queryId, subject);
    this.updateQueryProgressList();

    // Simulate progress updates for demo purposes
    this.simulateProgress(queryId);
  }

  private updateQueryProgress(
    queryId: string,
    status: QueryStatus,
    progress: number,
    step: string,
    error?: any
  ): void {
    const subject = this.activeQueries.get(queryId);
    if (subject) {
      const update: QueryProgressUpdate = {
        query_id: queryId,
        status,
        progress_percentage: progress,
        current_step: step,
        error: error
          ? {
              code: error.status?.toString() || 'UNKNOWN_ERROR',
              message: error.message || 'An error occurred',
              timestamp: new Date().toISOString(),
              query_id: queryId,
            }
          : undefined,
      };

      subject.next(update);
      this.updateQueryProgressList();

      // Clean up completed/failed queries after 30 seconds
      if (status === 'COMPLETED' || status === 'FAILED') {
        timer(30000).subscribe(() => {
          this.activeQueries.delete(queryId);
          this.updateQueryProgressList();
        });
      }
    }
  }

  private updateQueryProgressList(): void {
    const allProgress = Array.from(this.activeQueries.values()).map(
      (subject) => subject.value
    );
    this.queryProgress$.next(allProgress);
  }

  private simulateProgress(queryId: string): void {
    const steps = [
      { progress: 10, step: 'Parsing query...' },
      { progress: 25, step: 'Searching documents...' },
      { progress: 50, step: 'Processing results...' },
      { progress: 75, step: 'Ranking results...' },
      { progress: 90, step: 'Finalizing response...' },
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        this.updateQueryProgress(
          queryId,
          'PROCESSING',
          steps[currentStep].progress,
          steps[currentStep].step
        );
        currentStep++;
      } else {
        clearInterval(interval);
      }
    }, 500);
  }

  // ============================================================================
  // Query Management Methods (Deprecated - ADR-030)
  // These methods are disabled in Core Edition. The backend returns 501.
  // ============================================================================

  /**
   * @deprecated ADR-030: Fork operations disabled in Core Edition.
   */
  forkQuery(queryId: string, modifications: any): Observable<QueryHistory> {
    console.warn(
      'forkQuery is deprecated (ADR-030): Disabled in Core Edition.'
    );
    const request = {
      parent_query_id: queryId,
      modifications: modifications,
    };

    return this.http
      .post<QueryHistory>(`${this.historyBaseUrl}/fork`, request)
      .pipe(
        catchError((error) =>
          this.handleQueryError(error, 'Failed to fork query')
        ),
        retry(2)
      );
  }

  /**
   * @deprecated ADR-030: Update operations disabled in Core Edition.
   */
  updateQuery(queryId: string, updates: any): Observable<QueryHistory> {
    console.warn(
      'updateQuery is deprecated (ADR-030): Disabled in Core Edition.'
    );
    return this.http
      .patch<QueryHistory>(`${this.historyBaseUrl}/${queryId}`, updates)
      .pipe(
        tap(() => {
          // Invalidate cache
          this.invalidateCache('history');
          this.invalidateCache('query', queryId);
        }),
        catchError((error) =>
          this.handleQueryError(error, 'Failed to update query')
        ),
        retry(2)
      );
  }

  /**
   * @deprecated ADR-030: Delete operations disabled in Core Edition.
   */
  deleteQuery(queryId: string): Observable<void> {
    console.warn(
      'deleteQuery is deprecated (ADR-030): Disabled in Core Edition.'
    );
    return this.http.delete<void>(`${this.historyBaseUrl}/${queryId}`).pipe(
      tap(() => {
        // Invalidate cache
        this.invalidateCache('history');
        this.invalidateCache('query', queryId);
      }),
      catchError((error) =>
        this.handleQueryError(error, 'Failed to delete query')
      ),
      retry(2)
    );
  }

  private handleQueryError(error: any, message: string): Observable<never> {
    console.error('Query Service Error:', error);
    const queryError: QueryError = {
      code: error.status?.toString() || 'UNKNOWN_ERROR',
      message: error.message || message,
      timestamp: new Date().toISOString(),
      details: error,
    };
    return throwError(() => queryError);
  }
}
