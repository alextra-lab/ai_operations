/**
 * Analytics Service
 *
 * Service for fetching usage analytics and performance metrics from the backend.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AnalyticsParams,
  HotDocumentsResponse,
  SecurityMetricsResponse,
  UsageStatsResponse,
} from '../models/analytics.models';

@Injectable({
  providedIn: 'root',
})
export class AnalyticsService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiBaseUrl;

  /**
   * Get hot documents analytics
   *
   * @param params - Analytics parameters (hours, limit)
   * @returns Observable of hot documents response
   */
  getHotDocuments(
    params: AnalyticsParams = {}
  ): Observable<HotDocumentsResponse> {
    const httpParams = new HttpParams()
      .set('limit', params.limit?.toString() || '10')
      .set('hours', params.hours?.toString() || '24');

    return this.http
      .get<HotDocumentsResponse>(`${this.apiUrl}/analytics/documents/hot`, {
        params: httpParams,
      })
      .pipe(
        catchError((error) => {
          console.error('Error fetching hot documents:', error);
          return throwError(() => new Error('Failed to fetch hot documents'));
        })
      );
  }

  /**
   * Get usage statistics
   *
   * @param params - Analytics parameters (hours)
   * @returns Observable of usage statistics response
   */
  getUsageStats(params: AnalyticsParams = {}): Observable<UsageStatsResponse> {
    const httpParams = new HttpParams().set(
      'hours',
      params.hours?.toString() || '24'
    );

    return this.http
      .get<UsageStatsResponse>(`${this.apiUrl}/analytics/usage/stats`, {
        params: httpParams,
      })
      .pipe(
        catchError((error) => {
          console.error('Error fetching usage statistics:', error);
          return throwError(
            () => new Error('Failed to fetch usage statistics')
          );
        })
      );
  }

  /**
   * Get security metrics
   *
   * @returns Observable of security metrics response
   */
  getSecurityMetrics(): Observable<SecurityMetricsResponse> {
    return this.http
      .get<SecurityMetricsResponse>(
        `${environment.apiBaseUrl}/security/metrics`
      )
      .pipe(
        catchError((error) => {
          console.error('Error fetching security metrics:', error);
          return throwError(
            () => new Error('Failed to fetch security metrics')
          );
        })
      );
  }

  /**
   * Calculate percentage change between two values
   *
   * @param current - Current value
   * @param previous - Previous value
   * @returns Percentage change
   */
  calculatePercentageChange(current: number, previous: number): number {
    if (previous === 0) return 0;
    return ((current - previous) / previous) * 100;
  }

  /**
   * Format large numbers with K, M suffixes
   *
   * @param num - Number to format
   * @returns Formatted string
   */
  formatNumber(num: number): string {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }
}
