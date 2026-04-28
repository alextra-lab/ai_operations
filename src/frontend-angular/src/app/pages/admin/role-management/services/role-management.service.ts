/**
 * Role Management Service
 *
 * Provides API wrapper methods for role-based use case assignments.
 * Implements ADR-041 role-based use case permissions.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import {
  RoleInfo,
  RoleUseCaseAssignRequest,
  RoleUseCaseListResponse,
} from '../models/role-management.models';

@Injectable({
  providedIn: 'root',
})
export class RoleManagementService {
  private readonly apiUrl = `${environment.apiBaseUrl}/admin/roles`;

  constructor(private http: HttpClient) {}

  /**
   * Assign a use case to a role.
   */
  assignUseCaseToRole(
    roleName: string,
    request: RoleUseCaseAssignRequest
  ): Observable<any> {
    return this.http.post(`${this.apiUrl}/${roleName}/use-cases`, request);
  }

  /**
   * Revoke a use case from a role.
   */
  revokeUseCaseFromRole(
    roleName: string,
    useCaseId: string,
    permanent = false
  ): Observable<any> {
    const params = new HttpParams().set('permanent', permanent.toString());

    return this.http.delete(
      `${this.apiUrl}/${roleName}/use-cases/${useCaseId}`,
      { params }
    );
  }

  /**
   * Get all use cases assigned to a role.
   */
  getRoleUseCases(
    roleName: string,
    includeInactive = false
  ): Observable<RoleUseCaseListResponse> {
    const params = new HttpParams().set(
      'include_inactive',
      includeInactive.toString()
    );

    return this.http.get<RoleUseCaseListResponse>(
      `${this.apiUrl}/${roleName}/use-cases`,
      { params }
    );
  }

  /**
   * Get all roles that have access to a use case.
   */
  getUseCaseRoles(useCaseId: string): Observable<string[]> {
    return this.http.get<string[]>(
      `${this.apiUrl}/use-cases/${useCaseId}/roles`
    );
  }

  /**
   * Get all available use cases for assignment.
   */
  getAvailableUseCases(): Observable<any> {
    // Use the use case management endpoint to get all use cases
    // Backend max page_size is 100
    return this.http.get<any>(`${environment.apiBaseUrl}/admin/use-cases`, {
      params: new HttpParams().set('page_size', '100'),
    });
  }

  /**
   * Get all system roles with metadata (display names and descriptions).
   * Fetches dynamically from backend API.
   */
  getSystemRoles(): Observable<RoleInfo[]> {
    return this.http.get<RoleInfo[]>(`${this.apiUrl}/system-roles`);
  }
}
