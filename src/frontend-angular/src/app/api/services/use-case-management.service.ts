/**
 * Use Case Management Service for AI Operations Platform
 *
 * Handles all HTTP communication with the backend use case management API.
 * Provides methods for CRUD operations, lifecycle management, version control,
 * and use case execution.
 *
 * Reference: USE_CASE_MANAGEMENT_PLAN.md
 * Architecture: ADR-018 Use Case Owned Architecture
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

import {
  CloneRequest,
  LifecycleState,
  RollbackRequest,
  StateTransitionRequest,
  UseCaseCreate,
  UseCaseListFilters,
  UseCaseListResponse,
  UseCaseResponse,
  UseCaseUpdate,
  VersionHistoryResponse,
} from '../models/use-case-management.models';

@Injectable({
  providedIn: 'root',
})
export class UseCaseManagementService {
  private readonly adminBaseUrl = `${environment.apiBaseUrl}/admin/use-cases`;
  private readonly publicBaseUrl = `${environment.apiBaseUrl}/use-cases`;

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Use Case CRUD Operations (Admin)
  // ============================================================================

  /**
   * List all use cases with optional filtering and pagination (admin)
   */
  listUseCases(
    filters: UseCaseListFilters = {}
  ): Observable<UseCaseListResponse> {
    let params = new HttpParams();

    if (filters.use_case_id_filter) {
      params = params.set('use_case_id_filter', filters.use_case_id_filter);
    }
    if (filters.category) {
      params = params.set('category', filters.category);
    }
    if (filters.lifecycle_state) {
      params = params.set('lifecycle_state', filters.lifecycle_state);
    }
    if (filters.is_active !== undefined) {
      params = params.set('is_active', filters.is_active.toString());
    }
    if (filters.active_only !== undefined) {
      params = params.set('active_only', filters.active_only.toString());
    }
    if (filters.intent_type) {
      params = params.set('intent_type', filters.intent_type);
    }
    if (filters.search_query) {
      params = params.set('search_query', filters.search_query);
    }
    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.page_size) {
      params = params.set('page_size', filters.page_size.toString());
    }

    return this.http
      .get<UseCaseListResponse>(this.adminBaseUrl, { params })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get a specific use case by ID (admin)
   */
  getUseCase(
    useCaseId: string,
    includePrompts = true
  ): Observable<UseCaseResponse> {
    let params = new HttpParams();
    if (includePrompts) {
      params = params.set('include_prompts', 'true');
    }

    return this.http
      .get<UseCaseResponse>(`${this.adminBaseUrl}/${useCaseId}`, { params })
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new use case (admin)
   */
  createUseCase(useCase: UseCaseCreate): Observable<UseCaseResponse> {
    return this.http
      .post<UseCaseResponse>(this.adminBaseUrl, useCase)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update an existing use case (admin)
   */
  updateUseCase(
    useCaseId: string,
    updates: UseCaseUpdate
  ): Observable<UseCaseResponse> {
    return this.http
      .put<UseCaseResponse>(`${this.adminBaseUrl}/${useCaseId}`, updates)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a use case (admin)
   */
  deleteUseCase(useCaseId: string): Observable<{ message: string }> {
    return this.http
      .delete<{ message: string }>(`${this.adminBaseUrl}/${useCaseId}`)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Lifecycle Management
  // ============================================================================

  /**
   * Transition use case to a new lifecycle state (admin)
   * Validates state machine: draft → review → published → archived
   */
  transitionState(
    useCaseId: string,
    request: StateTransitionRequest
  ): Observable<UseCaseResponse> {
    return this.http
      .post<UseCaseResponse>(
        `${this.adminBaseUrl}/${useCaseId}/transition`,
        request
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Helper methods for common state transitions
   */
  sendToReview(useCaseId: string): Observable<UseCaseResponse> {
    return this.transitionState(useCaseId, { to_state: LifecycleState.REVIEW });
  }

  publish(
    useCaseId: string,
    approvalNotes?: string
  ): Observable<UseCaseResponse> {
    return this.transitionState(useCaseId, {
      to_state: LifecycleState.PUBLISHED,
      approval_notes: approvalNotes,
    });
  }

  archive(useCaseId: string): Observable<UseCaseResponse> {
    return this.transitionState(useCaseId, {
      to_state: LifecycleState.ARCHIVED,
    });
  }

  returnToDraft(useCaseId: string): Observable<UseCaseResponse> {
    return this.transitionState(useCaseId, { to_state: LifecycleState.DRAFT });
  }

  // ============================================================================
  // Version Control
  // ============================================================================

  /**
   * Get version history for a use case (admin)
   */
  getVersionHistory(useCaseId: string): Observable<VersionHistoryResponse> {
    return this.http
      .get<VersionHistoryResponse>(`${this.adminBaseUrl}/${useCaseId}/versions`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Rollback use case to a previous version (admin)
   */
  rollbackToVersion(
    useCaseId: string,
    versionNumber: number
  ): Observable<UseCaseResponse> {
    const request: RollbackRequest = { to_version: versionNumber };
    return this.http
      .post<UseCaseResponse>(
        `${this.adminBaseUrl}/${useCaseId}/rollback`,
        request
      )
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Clone Operations
  // ============================================================================

  /**
   * Clone a use case (admin)
   */
  cloneUseCase(
    useCaseId: string,
    newId: string,
    newName?: string
  ): Observable<UseCaseResponse> {
    const request: CloneRequest = {
      new_use_case_id: newId,
      new_name: newName,
    };
    return this.http
      .post<UseCaseResponse>(`${this.adminBaseUrl}/${useCaseId}/clone`, request)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Public Operations (Non-Admin)
  // ============================================================================

  /**
   * List available use cases for execution (RBAC-filtered)
   */
  getAvailableUseCases(): Observable<UseCaseListResponse> {
    return this.http
      .get<UseCaseListResponse>(`${this.publicBaseUrl}/available`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get use case details (public)
   */
  getUseCasePublic(useCaseId: string): Observable<UseCaseResponse> {
    return this.http
      .get<UseCaseResponse>(`${this.publicBaseUrl}/${useCaseId}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get use case configuration (public)
   */
  getUseCaseConfig(useCaseId: string): Observable<any> {
    return this.http
      .get<any>(`${this.publicBaseUrl}/${useCaseId}/config`)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Handle HTTP errors
   */
  private handleError(error: any): Observable<never> {
    console.error('Use Case Management service error:', error);
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Client Error: ${error.error.message}`;
    } else if (error.error && error.error.detail) {
      // Backend error with detail
      errorMessage = error.error.detail;
    } else if (error.message) {
      // Generic error message
      errorMessage = error.message;
    }

    return throwError(() => new Error(errorMessage));
  }

  /**
   * Get lifecycle state badge class for UI styling
   */
  getLifecycleStateClass(state: string): string {
    const stateMap: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      review: 'bg-yellow-100 text-yellow-800',
      published: 'bg-green-100 text-green-800',
      archived: 'bg-red-100 text-red-800',
    };
    return stateMap[state] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Get lifecycle state display name
   */
  getLifecycleStateName(state: string): string {
    const stateMap: Record<string, string> = {
      draft: 'Draft',
      review: 'In Review',
      published: 'Published',
      archived: 'Archived',
    };
    return stateMap[state] || state;
  }

  /**
   * Get lifecycle state icon
   */
  getLifecycleStateIcon(state: string): string {
    const iconMap: Record<string, string> = {
      draft: 'pencil',
      review: 'clock',
      published: 'circle-check',
      archived: 'archive',
    };
    return iconMap[state] || 'circle-help';
  }

  /**
   * Validate state transition
   * State machine: draft → review → published → archived
   * Matches backend validation in use_case_management.py
   */
  canTransitionTo(currentState: string, targetState: string): boolean {
    const transitions: Record<string, string[]> = {
      draft: ['review'],
      review: ['published', 'draft'], // Can reject back to draft
      published: ['archived'],
      archived: [], // Terminal state
    };
    return transitions[currentState]?.includes(targetState) || false;
  }

  /**
   * Get allowed next states for current state
   * State machine: draft → review → published → archived
   * Matches backend validation in use_case_management.py
   */
  getAllowedNextStates(currentState: string): string[] {
    const transitions: Record<string, string[]> = {
      draft: ['review'],
      review: ['published', 'draft'], // Can reject back to draft
      published: ['archived'],
      archived: [], // Terminal state
    };
    return transitions[currentState] || [];
  }
}
