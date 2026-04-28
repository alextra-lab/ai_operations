/**
 * Tool Analytics Service
 *
 * Handles API communication for T6-F3 Tool Analytics Dashboard.
 * Provides methods for fetching usage statistics and center aggregations.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  CenterUsage,
  ToolUsageSummary,
} from '../../pages/admin/tool-analytics/models/tool-analytics.models';

@Injectable({
  providedIn: 'root',
})
export class ToolAnalyticsService {
  private readonly baseUrl = '/api/v1/tools/analytics';
  private readonly http = inject(HttpClient);

  /**
   * Get usage summary for all tools
   * @param startDate - Optional start date for filtering (ISO 8601)
   * @param endDate - Optional end date for filtering (ISO 8601)
   */
  getUsageSummary(
    startDate?: Date,
    endDate?: Date
  ): Observable<ToolUsageSummary[]> {
    let params = new HttpParams();

    if (startDate) {
      params = params.set('start_date', startDate.toISOString());
    }
    if (endDate) {
      params = params.set('end_date', endDate.toISOString());
    }

    return this.http.get<ToolUsageSummary[]>(`${this.baseUrl}/usage/summary`, {
      params,
    });
  }

  /**
   * Get usage aggregated by center
   * @param days - Number of days to look back (1-365, default 30)
   */
  getUsageByCenter(days = 30): Observable<CenterUsage[]> {
    const params = new HttpParams().set('days', days.toString());
    return this.http.get<CenterUsage[]>(`${this.baseUrl}/usage/by-center`, {
      params,
    });
  }

  /**
   * Get usage summary for a specific date range (days ago)
   * @param days - Number of days to look back
   */
  getUsageSummaryByDays(days: number): Observable<ToolUsageSummary[]> {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    return this.getUsageSummary(startDate, endDate);
  }
}
