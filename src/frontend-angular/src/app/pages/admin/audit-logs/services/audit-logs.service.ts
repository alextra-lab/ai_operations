/**
 * Service for audit log API operations.
 *
 * Provides methods to query audit logs with filtering, pagination, and statistics.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import {
  AuditLogEntry,
  AuditLogFilters,
  AuditLogListResponse,
  AuditLogStatsResponse,
} from '../models/audit-logs.models';

@Injectable({
  providedIn: 'root',
})
export class AuditLogsService {
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/audit-logs`;

  constructor(private http: HttpClient) {}

  /**
   * Query audit logs with filters and pagination.
   */
  listAuditLogs(
    filters: AuditLogFilters = {}
  ): Observable<AuditLogListResponse> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.page_size) {
      params = params.set('page_size', filters.page_size.toString());
    }
    if (filters.start_date) {
      params = params.set('start_date', filters.start_date);
    }
    if (filters.end_date) {
      params = params.set('end_date', filters.end_date);
    }
    if (filters.actor_user_id) {
      params = params.set('actor_user_id', filters.actor_user_id);
    }
    if (filters.action) {
      params = params.set('action', filters.action);
    }
    if (filters.resource_type) {
      params = params.set('resource_type', filters.resource_type);
    }
    if (filters.use_case_id) {
      params = params.set('use_case_id', filters.use_case_id);
    }
    if (filters.success !== undefined) {
      params = params.set('success', filters.success.toString());
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }

    return this.http.get<AuditLogListResponse>(this.baseUrl, { params });
  }

  /**
   * Get a single audit log entry by ID.
   */
  getAuditLog(logId: string): Observable<AuditLogEntry> {
    return this.http.get<AuditLogEntry>(`${this.baseUrl}/${logId}`);
  }

  /**
   * Get audit log statistics.
   */
  getStats(filters: AuditLogFilters = {}): Observable<AuditLogStatsResponse> {
    let params = new HttpParams();

    if (filters.start_date) {
      params = params.set('start_date', filters.start_date);
    }
    if (filters.end_date) {
      params = params.set('end_date', filters.end_date);
    }
    if (filters.actor_user_id) {
      params = params.set('actor_user_id', filters.actor_user_id);
    }
    if (filters.resource_type) {
      params = params.set('resource_type', filters.resource_type);
    }

    return this.http.get<AuditLogStatsResponse>(`${this.baseUrl}/stats`, {
      params,
    });
  }
}
