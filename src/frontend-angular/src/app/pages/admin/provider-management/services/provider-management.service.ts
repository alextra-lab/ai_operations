/**
 * Provider Management Service
 *
 * Handles API communication for Inference Gateway provider management.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  CreateProviderRequest,
  ProviderConfig,
  ProviderFilters,
  ProviderListResponse,
  ProviderTestResult,
  UpdateProviderRequest,
} from '../models/provider-management.models';

@Injectable({
  providedIn: 'root',
})
export class ProviderManagementService {
  private readonly baseUrl = '/api/admin/gateway/providers';

  constructor(private http: HttpClient) {}

  /**
   * List all providers with optional filters
   */
  listProviders(filters?: ProviderFilters): Observable<ProviderListResponse> {
    let params = new HttpParams();

    if (filters) {
      if (filters.limit !== undefined) {
        params = params.set('limit', filters.limit.toString());
      }
      if (filters.offset !== undefined) {
        params = params.set('offset', filters.offset.toString());
      }
      if (filters.enabled_only !== undefined) {
        params = params.set('enabled_only', filters.enabled_only.toString());
      }
    }

    return this.http.get<ProviderListResponse>(this.baseUrl, { params });
  }

  /**
   * Get a specific provider by ID
   */
  getProvider(providerId: string): Observable<ProviderConfig> {
    return this.http.get<ProviderConfig>(`${this.baseUrl}/${providerId}`);
  }

  /**
   * Create a new provider
   */
  createProvider(request: CreateProviderRequest): Observable<ProviderConfig> {
    return this.http.post<ProviderConfig>(this.baseUrl, request);
  }

  /**
   * Update an existing provider
   */
  updateProvider(
    providerId: string,
    request: UpdateProviderRequest
  ): Observable<ProviderConfig> {
    return this.http.put<ProviderConfig>(
      `${this.baseUrl}/${providerId}`,
      request
    );
  }

  /**
   * Delete a provider
   */
  deleteProvider(providerId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${providerId}`);
  }

  /**
   * Test provider connectivity and health
   */
  testProvider(providerId: string): Observable<ProviderTestResult> {
    return this.http.post<ProviderTestResult>(
      `${this.baseUrl}/${providerId}/test`,
      {}
    );
  }
}
