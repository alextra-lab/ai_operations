import {
  HttpClient,
  HttpErrorResponse,
  HttpHeaders,
  HttpParams,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

import {
  LoginRequest,
  RefreshTokenRequest,
  TokenResponse,
  UserCreate,
  UserResponse,
  UserUpdate,
} from '../models/auth.models';
import { ApiConfig, RequestConfig } from '../models/common.models';
import {
  AnalyticsParams,
  DocumentDeleteParams,
  DocumentGetParams,
  DocumentListParams,
  DocumentUpdateRequest,
  DocumentUploadRequest,
  FormattedResponse,
  ProcessRequest,
  QueryRequest,
} from '../models/orchestrator.models';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly config: ApiConfig = {
    baseUrl: environment.apiBaseUrl,
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000,
  };

  constructor(private http: HttpClient) {}

  // Authentication endpoints
  login(loginData: LoginRequest): Observable<TokenResponse> {
    const body = new URLSearchParams();
    body.set('username', loginData.username);
    body.set('password', loginData.password);
    if (loginData.grant_type) body.set('grant_type', loginData.grant_type);
    if (loginData.scope) body.set('scope', loginData.scope);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http
      .post<TokenResponse>(
        `${this.config.baseUrl}/auth/token`,
        body.toString(),
        { headers }
      )
      .pipe(retry(this.config.retryAttempts), catchError(this.handleError));
  }

  refreshToken(refreshToken: string): Observable<TokenResponse> {
    const body: RefreshTokenRequest = { refresh_token: refreshToken };
    return this.http
      .post<TokenResponse>(`${this.config.baseUrl}/auth/refresh`, body)
      .pipe(retry(this.config.retryAttempts), catchError(this.handleError));
  }

  revokeToken(refreshToken: string): Observable<any> {
    const body: RefreshTokenRequest = { refresh_token: refreshToken };
    return this.http
      .post(`${this.config.baseUrl}/auth/revoke`, body, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  validateToken(): Observable<any> {
    return this.http
      .get(`${this.config.baseUrl}/auth/validate`, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  // User management endpoints
  getCurrentUser(): Observable<UserResponse> {
    return this.http
      .get<UserResponse>(
        `${this.config.baseUrl}/auth/me`,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  getUsers(): Observable<UserResponse[]> {
    return this.http
      .get<
        UserResponse[]
      >(`${this.config.baseUrl}/auth/users`, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  getUser(userId: string): Observable<UserResponse> {
    return this.http
      .get<UserResponse>(
        `${this.config.baseUrl}/auth/users/${userId}`,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  createUser(userData: UserCreate): Observable<UserResponse> {
    return this.http
      .post<UserResponse>(
        `${this.config.baseUrl}/auth/users`,
        userData,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  updateUser(userId: string, userData: UserUpdate): Observable<UserResponse> {
    return this.http
      .put<UserResponse>(
        `${this.config.baseUrl}/auth/users/${userId}`,
        userData,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  // Core orchestrator endpoints
  processRequest(request: ProcessRequest): Observable<FormattedResponse> {
    return this.http
      .post<FormattedResponse>(
        `${this.config.baseUrl}/process`,
        request,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  // Document management endpoints
  uploadDocument(uploadData: DocumentUploadRequest): Observable<any> {
    const formData = new FormData();
    formData.append('file', uploadData.file);
    if (uploadData.title) formData.append('title', uploadData.title);
    if (uploadData.source) formData.append('source', uploadData.source);
    if (uploadData.author) formData.append('author', uploadData.author);
    if (uploadData.classification)
      formData.append('classification', uploadData.classification);
    if (uploadData.tags) formData.append('tags', uploadData.tags);
    if (uploadData.metadata) formData.append('metadata', uploadData.metadata);
    formData.append(
      'process_async',
      uploadData.process_async?.toString() ?? 'true'
    );

    const headers = this.getAuthHeaders().headers;
    if (headers) {
      delete headers['Content-Type']; // Let browser set multipart/form-data boundary
    }

    return this.http
      .post(`${this.config.baseUrl}/documents/`, formData, { headers })
      .pipe(catchError(this.handleError));
  }

  getDocuments(params: DocumentListParams = {}): Observable<any[]> {
    let httpParams = new HttpParams();
    if (params.limit)
      httpParams = httpParams.set('limit', params.limit.toString());
    if (params.offset)
      httpParams = httpParams.set('offset', params.offset.toString());
    if (params.document_type)
      httpParams = httpParams.set('document_type', params.document_type);
    if (params.tag) httpParams = httpParams.set('tag', params.tag);
    if (params.query) httpParams = httpParams.set('query', params.query);

    return this.http
      .get<any[]>(`${this.config.baseUrl}/documents/`, {
        ...this.getAuthHeaders(),
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  getDocument(params: DocumentGetParams): Observable<any> {
    let httpParams = new HttpParams();
    if (params.include_preview !== undefined) {
      httpParams = httpParams.set(
        'include_preview',
        params.include_preview.toString()
      );
    }
    if (params.preview_length) {
      httpParams = httpParams.set(
        'preview_length',
        params.preview_length.toString()
      );
    }

    return this.http
      .get(`${this.config.baseUrl}/documents/${params.document_id}`, {
        ...this.getAuthHeaders(),
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  updateDocument(
    documentId: string,
    updateData: DocumentUpdateRequest
  ): Observable<any> {
    return this.http
      .patch(
        `${this.config.baseUrl}/documents/${documentId}`,
        updateData,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  deleteDocument(params: DocumentDeleteParams): Observable<any> {
    let httpParams = new HttpParams();
    if (params.force !== undefined) {
      httpParams = httpParams.set('force', params.force.toString());
    }

    return this.http
      .delete(`${this.config.baseUrl}/documents/${params.document_id}`, {
        ...this.getAuthHeaders(),
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  getDocumentStatus(documentId: string): Observable<any> {
    return this.http
      .get(
        `${this.config.baseUrl}/documents/${documentId}/status`,
        this.getAuthHeaders()
      )
      .pipe(catchError(this.handleError));
  }

  getDocumentStats(): Observable<any> {
    return this.http
      .get(`${this.config.baseUrl}/documents/stats`, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  // Query endpoints
  searchDocuments(query: QueryRequest): Observable<any> {
    return this.http
      .post(`${this.config.baseUrl}/query/search`, query, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  askQuestion(query: QueryRequest): Observable<any> {
    return this.http
      .post(`${this.config.baseUrl}/query/ask`, query, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  // Analytics endpoints
  getHotDocuments(params: AnalyticsParams = {}): Observable<any[]> {
    let httpParams = new HttpParams();
    if (params.limit)
      httpParams = httpParams.set('limit', params.limit.toString());
    if (params.hours)
      httpParams = httpParams.set('hours', params.hours.toString());

    return this.http
      .get<any[]>(`${this.config.baseUrl}/analytics/documents/hot`, {
        ...this.getAuthHeaders(),
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  getUsageStats(params: AnalyticsParams = {}): Observable<any> {
    let httpParams = new HttpParams();
    if (params.hours)
      httpParams = httpParams.set('hours', params.hours.toString());

    return this.http
      .get(`${this.config.baseUrl}/analytics/usage/stats`, {
        ...this.getAuthHeaders(),
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  // Health check
  healthCheck(): Observable<any> {
    return this.http
      .get(`${this.config.baseUrl}/health`)
      .pipe(catchError(this.handleError));
  }

  // Protected route test
  testProtectedRoute(): Observable<any> {
    return this.http
      .get(`${this.config.baseUrl}/protected`, this.getAuthHeaders())
      .pipe(catchError(this.handleError));
  }

  // Utility methods
  private getAuthHeaders(): RequestConfig {
    const token = localStorage.getItem('access_token');
    return {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    };
  }

  private handleError = (error: HttpErrorResponse): Observable<never> => {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      // Server-side error
      if (error.error?.detail) {
        if (typeof error.error.detail === 'string') {
          errorMessage = error.error.detail;
        } else if (Array.isArray(error.error.detail)) {
          errorMessage = error.error.detail
            .map((err: any) => err.msg || err.message)
            .join(', ');
        }
      } else {
        errorMessage = `Server Error: ${error.status} - ${error.statusText}`;
      }
    }

    console.error('API Error:', error);
    return throwError(() => new Error(errorMessage));
  };
}
