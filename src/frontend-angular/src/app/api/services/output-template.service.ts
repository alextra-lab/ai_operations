/**
 * Output Template API Service
 *
 * HTTP client for custom output visualization template CRUD.
 * Works alongside TemplateRegistryService, which merges
 * built-in and custom templates at runtime.
 *
 * @see ADR-066: Domain-Neutral Visualization Template Architecture
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  environment,
} from '../../../environments/environment';

/** Response shape from the backend. */
export interface OutputTemplateApiResponse {
  id: string;
  template_id: string;
  name: string;
  description: string;
  is_builtin: boolean;
  data_schema: Record<string, unknown>;
  layout: Record<string, unknown>;
  export_formats: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

/** Paginated list response. */
export interface OutputTemplateListApiResponse {
  templates: OutputTemplateApiResponse[];
  total: number;
  page: number;
  page_size: number;
}

/** Create payload. */
export interface OutputTemplateCreatePayload {
  template_id: string;
  name: string;
  description?: string;
  data_schema: Record<string, unknown>;
  layout: Record<string, unknown>;
  export_formats?: string[];
}

/** Update payload (all optional). */
export interface OutputTemplateUpdatePayload {
  name?: string;
  description?: string;
  data_schema?: Record<string, unknown>;
  layout?: Record<string, unknown>;
  export_formats?: string[];
}

@Injectable({
  providedIn: 'root',
})
export class OutputTemplateApiService {
  private readonly baseUrl =
    `${environment.apiBaseUrl}/admin/output-templates`;

  constructor(private http: HttpClient) {}

  /**
   * List all output templates.
   *
   * @param page - Page number (1-based)
   * @param pageSize - Items per page
   */
  list(
    page = 1,
    pageSize = 100
  ): Observable<OutputTemplateListApiResponse> {
    const params = new HttpParams()
      .set('page', page.toString())
      .set('page_size', pageSize.toString());
    return this.http.get<OutputTemplateListApiResponse>(
      this.baseUrl,
      { params }
    );
  }

  /** Get a single template by slug. */
  get(
    templateId: string
  ): Observable<OutputTemplateApiResponse> {
    return this.http.get<OutputTemplateApiResponse>(
      `${this.baseUrl}/${templateId}`
    );
  }

  /** Create a custom template. */
  create(
    payload: OutputTemplateCreatePayload
  ): Observable<OutputTemplateApiResponse> {
    return this.http.post<OutputTemplateApiResponse>(
      this.baseUrl,
      payload
    );
  }

  /** Update a custom template. */
  update(
    templateId: string,
    payload: OutputTemplateUpdatePayload
  ): Observable<OutputTemplateApiResponse> {
    return this.http.put<OutputTemplateApiResponse>(
      `${this.baseUrl}/${templateId}`,
      payload
    );
  }

  /** Delete a custom template. */
  delete(templateId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/${templateId}`
    );
  }
}
