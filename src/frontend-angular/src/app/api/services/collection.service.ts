/**
 * Collection Management HTTP Service
 *
 * Provides HTTP methods for interacting with the Collection Management API.
 * Handles CRUD operations for collections and integration with the RAG pipeline.
 *
 * Admin endpoints require 'admin' or 'corpus_admin' role.
 * Public endpoints available to all authenticated users.
 *
 * See:
 * - Backend: src/retrieval/app/routers/collections.py
 * - Models: src/app/api/models/collection.models.ts
 * - ADR: docs/development/adrs/ADR-021-Collection-Based-Document-Management.md
 */

import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import {
  Collection,
  CollectionCreate,
  CollectionListResponse,
  CollectionStats,
  CollectionUpdate,
} from '../models/collection.models';

@Injectable({ providedIn: 'root' })
export class CollectionService {
  private readonly baseUrl = `${environment.apiBaseUrl}/admin/collections/`;
  private readonly publicUrl = `${environment.apiBaseUrl}/admin/collections`;

  constructor(private http: HttpClient) {}

  /**
   * List all collections with optional filters (Admin endpoint)
   *
   * @param activeOnly - Only return active collections
   * @param embeddingModel - Filter by embedding model
   * @param skip - Number of items to skip (pagination)
   * @param limit - Maximum number of items to return
   * @returns Observable of collection list response
   *
   * **Permissions:** admin, corpus_admin
   */
  listCollections(
    activeOnly = true,
    embeddingModel?: string,
    skip = 0,
    limit = 100
  ): Observable<CollectionListResponse> {
    // For now, use the public endpoint that's working
    // TODO: Fix admin endpoint authentication issue
    return this.listAvailableCollections();
  }

  /**
   * Get collection by ID (Admin endpoint)
   *
   * @param id - Collection UUID
   * @returns Observable of collection
   *
   * **Permissions:** admin, corpus_admin
   */
  getCollection(id: string): Observable<Collection> {
    // baseUrl already has trailing slash, so don't add another
    return this.http
      .get<Collection>(`${this.baseUrl}${id}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Create a new collection (Admin endpoint)
   *
   * @param data - Collection creation payload
   * @returns Observable of created collection
   *
   * **Permissions:** admin, corpus_admin
   *
   * **Note:** Embedding model, provider, and dimensions are immutable after creation
   */
  createCollection(data: CollectionCreate): Observable<Collection> {
    return this.http
      .post<Collection>(this.baseUrl, data)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update collection (Admin endpoint)
   *
   * Only description and is_active can be updated.
   * Embedding model is immutable after creation.
   *
   * @param id - Collection UUID
   * @param data - Update payload
   * @returns Observable of updated collection
   *
   * **Permissions:** admin, corpus_admin
   */
  updateCollection(id: string, data: CollectionUpdate): Observable<Collection> {
    return this.http
      .put<Collection>(`${this.baseUrl}${id}`, data)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete collection (Admin endpoint)
   *
   * Collection must have no documents to be deleted.
   * System-managed collections cannot be deleted.
   *
   * @param id - Collection UUID
   * @returns Observable of void
   *
   * **Permissions:** admin, corpus_admin
   */
  deleteCollection(id: string): Observable<void> {
    return this.http
      .delete<void>(`${this.baseUrl}${id}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get collection statistics (Admin endpoint)
   *
   * @param id - Collection UUID
   * @returns Observable of collection stats
   *
   * **Permissions:** admin, corpus_admin
   */
  getCollectionStats(id: string): Observable<CollectionStats> {
    return this.http
      .get<CollectionStats>(`${this.baseUrl}${id}/stats`)
      .pipe(catchError(this.handleError));
  }

  /**
   * List available collections for Use Case configuration (Public endpoint)
   *
   * Returns only active collections that can be selected for RAG queries.
   *
   * @returns Observable of collection list response
   *
   * **Permissions:** All authenticated users
   */
  listAvailableCollections(): Observable<CollectionListResponse> {
    return this.http
      .get<CollectionListResponse>(`${this.publicUrl}/available`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get collection by ID (Public read-only endpoint)
   *
   * @param id - Collection UUID
   * @returns Observable of collection
   *
   * **Permissions:** All authenticated users
   */
  getCollectionPublic(id: string): Observable<Collection> {
    return this.http
      .get<Collection>(`${this.publicUrl}/${id}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Validate collection name format
   *
   * Name must be:
   * - 3-255 characters
   * - Lowercase alphanumeric with underscores and hyphens
   * - Not reserved (system, default, test, admin, etc.)
   *
   * @param name - Collection name to validate
   * @returns Validation result with error message if invalid
   */
  validateCollectionName(name: string): { valid: boolean; error?: string } {
    if (!name || name.length < 3) {
      return { valid: false, error: 'Name must be at least 3 characters' };
    }

    if (name.length > 255) {
      return { valid: false, error: 'Name must be at most 255 characters' };
    }

    const validPattern = /^[a-z0-9_-]+$/;
    if (!validPattern.test(name)) {
      return {
        valid: false,
        error:
          'Name must contain only lowercase letters, numbers, underscores, and hyphens',
      };
    }

    const reservedNames = [
      'system',
      'default',
      'test',
      'admin',
      'public',
      'private',
    ];
    if (reservedNames.includes(name)) {
      return { valid: false, error: 'This name is reserved' };
    }

    return { valid: true };
  }

  /**
   * Handle HTTP errors
   *
   * @param error - HTTP error response
   * @returns Observable that errors with user-friendly message
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side or network error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Backend returned an unsuccessful response code
      if (error.error?.detail) {
        errorMessage = error.error.detail;
      } else if (error.status === 403) {
        errorMessage = 'You do not have permission to perform this action';
      } else if (error.status === 404) {
        errorMessage = 'Collection not found';
      } else if (error.status === 409) {
        errorMessage = 'A collection with this name already exists';
      } else if (error.status === 422) {
        errorMessage = 'Invalid data provided';
      } else {
        errorMessage = `Server error: ${error.status}`;
      }
    }

    console.error('CollectionService error:', error);
    return throwError(() => new Error(errorMessage));
  }
}
