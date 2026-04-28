/**
 * Admin Analytics Service
 *
 * Service for fetching admin-only analytics data including token usage,
 * cost tracking, and system metrics.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AllCentersUsageSummaryResponse,
  CenterUsageSummaryResponse,
  UserUsageResponse,
} from '../models/token-usage.models';

@Injectable({
  providedIn: 'root',
})
export class AdminAnalyticsService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiBaseUrl;

  /**
   * Get token usage summary for all centers
   */
  getAllCentersTokenUsage(
    startDate?: string,
    endDate?: string
  ): Observable<AllCentersUsageSummaryResponse> {
    let params = new HttpParams();
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }

    return this.http
      .get<AllCentersUsageSummaryResponse>(
        `${this.apiUrl}/admin/token-usage/by-center`,
        { params }
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Get token usage summary for a specific center
   */
  getCenterTokenUsage(
    centerId: string,
    startDate?: string,
    endDate?: string
  ): Observable<CenterUsageSummaryResponse> {
    let params = new HttpParams();
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }

    return this.http
      .get<CenterUsageSummaryResponse>(
        `${this.apiUrl}/admin/token-usage/by-center/${centerId}`,
        { params }
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Get token usage summary for a specific user
   */
  getUserTokenUsage(
    userId: string,
    startDate?: string,
    endDate?: string
  ): Observable<UserUsageResponse> {
    let params = new HttpParams();
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }

    return this.http
      .get<UserUsageResponse>(
        `${this.apiUrl}/admin/token-usage/by-user/${userId}`,
        { params }
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Get current user's own token usage
   */
  getMyTokenUsage(
    startDate?: string,
    endDate?: string
  ): Observable<UserUsageResponse> {
    let params = new HttpParams();
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }

    return this.http
      .get<UserUsageResponse>(`${this.apiUrl}/admin/token-usage/me`, { params })
      .pipe(catchError(this.handleError));
  }

  private handleError(error: any): Observable<never> {
    console.error('Admin Analytics Service Error:', error);

    let errorMessage = 'An error occurred while fetching admin analytics data';

    if (error.status === 403) {
      errorMessage = 'Access denied. Admin privileges required.';
    } else if (error.status === 404) {
      errorMessage = 'Requested data not found.';
    } else if (error.status >= 500) {
      errorMessage = 'Server error. Please try again later.';
    } else if (error.error?.detail) {
      errorMessage = error.error.detail;
    }

    return throwError(() => new Error(errorMessage));
  }
}
