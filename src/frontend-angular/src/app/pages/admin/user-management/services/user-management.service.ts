/**
 * User Management Service
 *
 * Provides API wrapper methods for user administration operations.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import {
  SessionInfo,
  UpdateUserRolesRequest,
  UserCreateRequest,
  UserDetailResponse,
  UserFilters,
  UserListResponse,
  UserRolesResponse,
  UserUpdateRequest,
} from '../models/user-management.models';

@Injectable({
  providedIn: 'root',
})
export class UserManagementService {
  private readonly apiUrl = `${environment.apiBaseUrl}/auth/users`;

  constructor(private http: HttpClient) {}

  listUsers(filters?: UserFilters): Observable<UserListResponse> {
    let params = new HttpParams();

    if (filters) {
      if (filters.search) params = params.set('search', filters.search);
      if (filters.role) params = params.set('role', filters.role);
      if (filters.status) params = params.set('status', filters.status);
      if (filters.limit) params = params.set('limit', filters.limit.toString());
      if (filters.offset)
        params = params.set('offset', filters.offset.toString());
    }

    return this.http.get<UserListResponse>(this.apiUrl, { params });
  }

  getUserDetails(userId: string): Observable<UserDetailResponse> {
    return this.http.get<UserDetailResponse>(`${this.apiUrl}/${userId}`);
  }

  createUser(request: UserCreateRequest): Observable<any> {
    return this.http.post(this.apiUrl, request);
  }

  updateUser(userId: string, updates: UserUpdateRequest): Observable<any> {
    return this.http.put(`${this.apiUrl}/${userId}`, updates);
  }

  deactivateUser(userId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${userId}`);
  }

  resetPassword(
    userId: string,
    newPassword: string,
    forceLogout = true
  ): Observable<any> {
    return this.http.post(`${this.apiUrl}/${userId}/reset-password`, null, {
      params: {
        new_password: newPassword,
        force_logout: forceLogout.toString(),
      },
    });
  }

  getUserSessions(userId: string): Observable<SessionInfo[]> {
    return this.http.get<SessionInfo[]>(`${this.apiUrl}/${userId}/sessions`);
  }

  forceLogout(userId: string, sessionId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${userId}/sessions/${sessionId}`);
  }

  // RBAC V2: User role management
  getUserRoles(userId: string): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(
      `${environment.apiBaseUrl}/admin/users/${userId}/roles`
    );
  }

  updateUserRoles(
    userId: string,
    request: UpdateUserRolesRequest
  ): Observable<UserRolesResponse> {
    return this.http.put<UserRolesResponse>(
      `${environment.apiBaseUrl}/admin/users/${userId}/roles`,
      request
    );
  }
}
