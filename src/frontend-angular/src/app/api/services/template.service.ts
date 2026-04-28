/**
 * Template Management Service for AI Operations Platform
 *
 * Handles all HTTP communication with the backend template management API.
 * Provides methods for CRUD operations, version control, and approval workflows.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

import {
  TemplateActivationRequest,
  TemplateApprovalRequest,
  TemplateCreate,
  TemplateDiffRequest,
  TemplateDiffResponse,
  TemplateListFilters,
  TemplateListResponse,
  TemplateRejectionRequest,
  TemplateResponse,
  TemplateUpdate,
  TemplateVersionCreate,
  TemplateVersionListResponse,
} from '../models/template.models';

@Injectable({
  providedIn: 'root',
})
export class TemplateService {
  private readonly baseUrl = `${environment.apiBaseUrl}/templates`;

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Template CRUD Operations
  // ============================================================================

  /**
   * List all templates with optional filtering and pagination
   */
  listTemplates(
    filters: TemplateListFilters = {}
  ): Observable<TemplateListResponse> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.page_size) {
      params = params.set('page_size', filters.page_size.toString());
    }
    if (filters.template_id_filter) {
      params = params.set('template_id_filter', filters.template_id_filter);
    }
    if (filters.deployment_status) {
      params = params.set('deployment_status', filters.deployment_status);
    }
    if (filters.active_only !== undefined) {
      params = params.set('active_only', filters.active_only.toString());
    }

    return this.http
      .get<TemplateListResponse>(this.baseUrl, { params })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get a specific template by ID
   */
  getTemplate(
    templateId: string,
    version?: number
  ): Observable<TemplateResponse> {
    let params = new HttpParams();
    if (version) {
      params = params.set('version', version.toString());
    }

    return this.http
      .get<TemplateResponse>(`${this.baseUrl}/${templateId}`, { params })
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new template
   */
  createTemplate(template: TemplateCreate): Observable<TemplateResponse> {
    return this.http
      .post<TemplateResponse>(this.baseUrl, template)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update an existing template
   */
  updateTemplate(
    templateId: string,
    updates: TemplateUpdate
  ): Observable<TemplateResponse> {
    return this.http
      .put<TemplateResponse>(`${this.baseUrl}/${templateId}`, updates)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a template (all versions)
   */
  deleteTemplate(
    templateId: string
  ): Observable<{ message: string; versions_deleted: number }> {
    return this.http
      .delete<{
        message: string;
        versions_deleted: number;
      }>(`${this.baseUrl}/${templateId}`)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Version Control Operations
  // ============================================================================

  /**
   * Get all versions of a template
   */
  getTemplateVersions(
    templateId: string
  ): Observable<TemplateVersionListResponse> {
    return this.http
      .get<TemplateVersionListResponse>(
        `${this.baseUrl}/${templateId}/versions`
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new version of a template
   */
  createTemplateVersion(
    templateId: string,
    versionData: TemplateVersionCreate
  ): Observable<TemplateResponse> {
    return this.http
      .post<TemplateResponse>(
        `${this.baseUrl}/${templateId}/versions`,
        versionData
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Activate a specific version of a template
   */
  activateTemplateVersion(
    templateId: string,
    versionNumber: number
  ): Observable<TemplateResponse> {
    const request: TemplateActivationRequest = {
      version_number: versionNumber,
    };
    return this.http
      .post<TemplateResponse>(`${this.baseUrl}/${templateId}/activate`, request)
      .pipe(catchError(this.handleError));
  }

  /**
   * Compare two versions of a template
   */
  compareTemplateVersions(
    templateId: string,
    version1: number,
    version2: number
  ): Observable<TemplateDiffResponse> {
    const request: TemplateDiffRequest = {
      version_1: version1,
      version_2: version2,
    };
    return this.http
      .post<TemplateDiffResponse>(`${this.baseUrl}/${templateId}/diff`, request)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Approval Workflow Operations
  // ============================================================================

  /**
   * Approve a template for deployment
   */
  approveTemplate(
    templateId: string,
    approvalNotes?: string
  ): Observable<TemplateResponse> {
    const request: TemplateApprovalRequest = { approval_notes: approvalNotes };
    return this.http
      .post<TemplateResponse>(`${this.baseUrl}/${templateId}/approve`, request)
      .pipe(catchError(this.handleError));
  }

  /**
   * Reject a template
   */
  rejectTemplate(
    templateId: string,
    rejectionReason: string
  ): Observable<TemplateResponse> {
    const request: TemplateRejectionRequest = {
      rejection_reason: rejectionReason,
    };
    return this.http
      .post<TemplateResponse>(`${this.baseUrl}/${templateId}/reject`, request)
      .pipe(catchError(this.handleError));
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Handle HTTP errors
   */
  private handleError(error: any): Observable<never> {
    console.error('Template service error:', error);
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
   * Get deployment status badge class for UI styling
   */
  getDeploymentStatusClass(status: string): string {
    const statusMap: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      pending: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      deployed: 'bg-blue-100 text-blue-800',
    };
    return statusMap[status] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Get deployment status display name
   */
  getDeploymentStatusName(status: string): string {
    const statusMap: Record<string, string> = {
      draft: 'Draft',
      pending: 'Pending Review',
      approved: 'Approved',
      deployed: 'Deployed',
    };
    return statusMap[status] || status;
  }
}
