/**
 * Tool Admin Service
 *
 * Handles API communication for Tools Track admin management.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  Tool,
  ToolFilters,
  ToolHealthCheckResult,
  ToolListItem,
  ToolUpdateRequest,
} from '../models/tool-management.models';

@Injectable({
  providedIn: 'root',
})
export class ToolAdminService {
  private readonly baseUrl = '/api/v1/admin/tools';

  constructor(private http: HttpClient) {}

  /**
   * List all tools with optional filters
   */
  listTools(filters?: ToolFilters): Observable<ToolListItem[]> {
    let params = new HttpParams();

    if (filters) {
      if (filters.category) {
        params = params.set('category', filters.category);
      }
      if (filters.enabled_only !== undefined) {
        params = params.set('enabled_only', filters.enabled_only.toString());
      }
      if (filters.healthy_only !== undefined) {
        params = params.set('healthy_only', filters.healthy_only.toString());
      }
    }

    return this.http.get<ToolListItem[]>(`${this.baseUrl}/`, { params });
  }

  /**
   * Get a specific tool by ID
   */
  getTool(toolId: string): Observable<Tool> {
    return this.http.get<Tool>(`${this.baseUrl}/${toolId}`);
  }

  /**
   * Update an existing tool
   */
  updateTool(toolId: string, request: ToolUpdateRequest): Observable<Tool> {
    return this.http.put<Tool>(`${this.baseUrl}/${toolId}`, request);
  }

  /**
   * Delete a tool
   */
  deleteTool(toolId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${toolId}`);
  }

  /**
   * Enable a tool
   */
  enableTool(toolId: string): Observable<Tool> {
    return this.http.post<Tool>(`${this.baseUrl}/${toolId}/enable`, {});
  }

  /**
   * Disable a tool
   */
  disableTool(toolId: string): Observable<Tool> {
    return this.http.post<Tool>(`${this.baseUrl}/${toolId}/disable`, {});
  }

  /**
   * Trigger manual health check for a tool
   */
  triggerHealthCheck(toolId: string): Observable<ToolHealthCheckResult> {
    return this.http.post<ToolHealthCheckResult>(
      `/api/v1/tools/health/${toolId}/check`,
      {}
    );
  }
}
