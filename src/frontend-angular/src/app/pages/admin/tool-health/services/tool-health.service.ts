/**
 * Tool Health Service
 *
 * Handles API communication for T6-F2 Tool Health Monitoring Dashboard.
 * Provides methods for fetching health status, history, and triggering checks.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  HealthSummary,
  ToolHealthCheckRecord,
} from '../models/tool-health.models';

@Injectable({
  providedIn: 'root',
})
export class ToolHealthService {
  private readonly baseUrl = '/api/v1/tools/health';
  private readonly http = inject(HttpClient);

  /**
   * Get overall health status summary for all enabled tools
   */
  getOverallStatus(): Observable<HealthSummary> {
    return this.http.get<HealthSummary>(`${this.baseUrl}/status`);
  }

  /**
   * Get health check history for a specific tool
   * @param toolId - UUID of the tool
   * @param hours - Number of hours of history (1-168, default 24)
   */
  getToolHistory(
    toolId: string,
    hours = 24
  ): Observable<ToolHealthCheckRecord[]> {
    const params = new HttpParams().set('hours', hours.toString());
    return this.http.get<ToolHealthCheckRecord[]>(
      `${this.baseUrl}/${toolId}/history`,
      { params }
    );
  }

  /**
   * Trigger an immediate health check for a specific tool
   * @param toolId - UUID of the tool
   */
  triggerHealthCheck(toolId: string): Observable<ToolHealthCheckRecord> {
    return this.http.post<ToolHealthCheckRecord>(
      `${this.baseUrl}/${toolId}/check`,
      {}
    );
  }
}
