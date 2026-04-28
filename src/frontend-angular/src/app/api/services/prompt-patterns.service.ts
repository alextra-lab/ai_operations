/**
 * Prompt Pattern Library Service
 * Provides HTTP client methods for pattern library operations
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  ApplyPatternRequest,
  ApplyPatternResponse,
  PromptPattern,
  PromptPatternListResponse,
} from '../models/prompt-patterns.models';

@Injectable({
  providedIn: 'root',
})
export class PromptPatternsService {
  private readonly baseUrl = '/api/v1/patterns';

  constructor(private http: HttpClient) {}

  /**
   * List and search prompt patterns with pagination
   */
  listPatterns(params: {
    category?: string;
    search?: string;
    tags?: string[];
    page?: number;
    page_size?: number;
    sort_by?: 'name' | 'category' | 'use_count' | 'created_at';
    sort_order?: 'asc' | 'desc';
  }): Observable<PromptPatternListResponse> {
    let httpParams = new HttpParams();

    if (params.category) {
      httpParams = httpParams.set('category', params.category);
    }
    if (params.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params.tags && params.tags.length > 0) {
      params.tags.forEach((tag) => {
        httpParams = httpParams.append('tags', tag);
      });
    }
    if (params.page) {
      httpParams = httpParams.set('page', params.page.toString());
    }
    if (params.page_size) {
      httpParams = httpParams.set('page_size', params.page_size.toString());
    }
    if (params.sort_by) {
      httpParams = httpParams.set('sort_by', params.sort_by);
    }
    if (params.sort_order) {
      httpParams = httpParams.set('sort_order', params.sort_order);
    }

    return this.http.get<PromptPatternListResponse>(this.baseUrl, {
      params: httpParams,
    });
  }

  /**
   * Get detailed information about a specific pattern
   */
  getPattern(patternId: string): Observable<PromptPattern> {
    return this.http.get<PromptPattern>(`${this.baseUrl}/${patternId}`);
  }

  /**
   * Apply a pattern with variable substitutions
   */
  applyPattern(
    patternId: string,
    variables: Record<string, string> = {}
  ): Observable<ApplyPatternResponse> {
    const request: ApplyPatternRequest = {
      pattern_id: patternId,
      variables,
    };
    return this.http.post<ApplyPatternResponse>(
      `${this.baseUrl}/apply`,
      request
    );
  }

  /**
   * Get list of all available categories
   */
  getCategories(): Observable<string[]> {
    // This could be enhanced to fetch from backend, but for now use static list
    return new Observable((observer) => {
      observer.next([
        'reasoning',
        'rag',
        'learning',
        'tools',
        'json',
        'role',
        'soc',
        'safety',
        'workflow',
        'context',
        'evaluation',
        'classification',
      ]);
      observer.complete();
    });
  }

  /**
   * Get patterns by category
   */
  getPatternsByCategory(
    category: string
  ): Observable<PromptPatternListResponse> {
    return this.listPatterns({
      category,
      page_size: 100,
      sort_by: 'use_count',
      sort_order: 'desc',
    });
  }

  /**
   * Search patterns by name or description
   */
  searchPatterns(query: string): Observable<PromptPatternListResponse> {
    return this.listPatterns({ search: query, page_size: 50 });
  }
}
