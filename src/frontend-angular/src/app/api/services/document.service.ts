import {
  HttpClient,
  HttpErrorResponse,
  HttpEvent,
  HttpEventType,
  HttpParams,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable, of, throwError } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import {
  Document,
  DocumentAnalytics,
  DocumentBatchOperation,
  DocumentBatchResult,
  DocumentDeleteRequest,
  DocumentListParams,
  DocumentListResponse,
  DocumentProcessingStatus,
  DocumentSearchFilters,
  DocumentState,
  DocumentStats,
  DocumentStatusResponse,
  DocumentUpdateRequest,
  DocumentUploadProgress,
  DocumentUploadRequest,
  DocumentUploadResponse,
  DocumentVersion,
} from '../models/document.models';

@Injectable({
  providedIn: 'root',
})
export class DocumentService {
  private readonly baseUrl = '/api/v1/documents';
  private readonly uploadProgressSubject = new BehaviorSubject<
    DocumentUploadProgress[]
  >([]);
  private readonly processingStatusSubject = new BehaviorSubject<
    DocumentProcessingStatus[]
  >([]);

  public uploadProgress$ = this.uploadProgressSubject.asObservable();
  public processingStatus$ = this.processingStatusSubject.asObservable();

  constructor(private http: HttpClient) { }

  /**
   * Upload a single document with progress tracking
   * Backend returns DocumentUploadResponse, then we fetch the full Document
   */
  uploadDocument(uploadRequest: DocumentUploadRequest): Observable<Document> {
    const formData = new FormData();
    formData.append('file', uploadRequest.file);

    // Collection name (required)
    if (uploadRequest.collection_name) {
      formData.append('collection_name', uploadRequest.collection_name);
    } else {
      console.warn(
        'DocumentService: No collection_name provided in uploadRequest!'
      );
    }

    if (uploadRequest.title) formData.append('title', uploadRequest.title);
    if (uploadRequest.source) formData.append('source', uploadRequest.source);
    if (uploadRequest.author) formData.append('author', uploadRequest.author);
    if (uploadRequest.classification)
      formData.append('classification', uploadRequest.classification);
    if (uploadRequest.tags)
      formData.append('tags', JSON.stringify(uploadRequest.tags));
    if (uploadRequest.metadata)
      formData.append('metadata', JSON.stringify(uploadRequest.metadata));
    if (uploadRequest.process_async !== undefined)
      formData.append('process_async', uploadRequest.process_async.toString());

    // Chunking configuration
    if (uploadRequest.chunking_config) {
      formData.append(
        'chunking_config',
        JSON.stringify(uploadRequest.chunking_config)
      );
    }

    const progress: DocumentUploadProgress = {
      documentId: '',
      filename: uploadRequest.file.name,
      progress: 0,
      status: 'uploading',
    };

    this.updateUploadProgress(progress);

    return this.http
      .post<DocumentUploadResponse>(`${this.baseUrl}/`, formData, {
        reportProgress: true,
        observe: 'events',
      })
      .pipe(
        map((event: HttpEvent<any>) => {
          switch (event.type) {
            case HttpEventType.UploadProgress:
              if (event.total) {
                progress.progress = Math.round(
                  (100 * event.loaded) / event.total
                );
              }
              this.updateUploadProgress(progress);
              return null;
            case HttpEventType.Response:
              progress.status = 'completed';
              progress.documentId = event.body.document_id;
              progress.message = event.body.message;
              this.updateUploadProgress(progress);
              return event.body;
            default:
              return null;
          }
        }),
        // Filter out null events and get the upload response
        map((response) => response as DocumentUploadResponse | null),
        switchMap((uploadResponse: DocumentUploadResponse | null) => {
          if (!uploadResponse) {
            return of(null as any);
          }
          // Fetch the full document details after upload
          return this.getDocument(uploadResponse.document_id);
        }),
        map((document) => document as Document),
        catchError(this.handleError)
      );
  }

  /**
   * Upload multiple documents with batch progress tracking
   */
  uploadDocuments(
    uploadRequests: DocumentUploadRequest[]
  ): Observable<Document[]> {
    const uploads = uploadRequests.map((request) =>
      this.uploadDocument(request)
    );
    return new Observable((observer) => {
      const results: Document[] = [];
      let completed = 0;

      uploads.forEach((upload, index) => {
        upload.subscribe({
          next: (document) => {
            if (document) {
              results[index] = document;
              completed++;
              if (completed === uploads.length) {
                observer.next(results);
                observer.complete();
              }
            }
          },
          error: (error) => {
            observer.error(error);
          },
        });
      });
    });
  }

  /**
   * Get list of documents with filtering and pagination
   * Only uses parameters supported by backend API
   */
  getDocuments(
    params: DocumentListParams = {}
  ): Observable<DocumentListResponse> {
    let httpParams = new HttpParams();

    if (params.limit)
      httpParams = httpParams.set('limit', params.limit.toString());
    if (params.offset)
      httpParams = httpParams.set('offset', params.offset.toString());
    if (params.document_type)
      httpParams = httpParams.set('document_type', params.document_type);
    if (params.tag) httpParams = httpParams.set('tag', params.tag);
    if (params.query) httpParams = httpParams.set('query', params.query);
    if (params.include_deleted !== undefined)
      httpParams = httpParams.set(
        'include_deleted',
        params.include_deleted.toString()
      );

    return this.http
      .get<DocumentListResponse>(`${this.baseUrl}/`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Search documents with advanced filters
   * Note: Some filters are not supported by the current backend API
   */
  searchDocuments(
    filters: DocumentSearchFilters
  ): Observable<DocumentListResponse> {
    const params: DocumentListParams = {
      query: filters.searchTerm || undefined,
    };

    if (filters.tags.length > 0) {
      params.tag = filters.tags.join(',');
    }

    return this.getDocuments(params);
  }

  /**
   * Get a single document by ID
   */
  getDocument(
    documentId: string,
    includePreview = false
  ): Observable<Document> {
    let httpParams = new HttpParams();
    if (includePreview) httpParams = httpParams.set('include_preview', 'true');

    return this.http
      .get<Document>(`${this.baseUrl}/${documentId}`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Update document metadata
   */
  updateDocument(
    documentId: string,
    updateRequest: DocumentUpdateRequest
  ): Observable<Document> {
    return this.http
      .patch<Document>(`${this.baseUrl}/${documentId}`, updateRequest)
      .pipe(catchError(this.handleError));
  }

  /**
   * Delete a document
   */
  deleteDocument(deleteRequest: DocumentDeleteRequest): Observable<void> {
    let httpParams = new HttpParams();
    if (deleteRequest.force) httpParams = httpParams.set('force', 'true');
    if (deleteRequest.reason)
      httpParams = httpParams.set('reason', deleteRequest.reason);

    return this.http
      .delete<void>(`${this.baseUrl}/${deleteRequest.document_id}`, {
        params: httpParams,
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get document processing status
   * Converts backend DocumentStatusResponse to UI-friendly DocumentProcessingStatus
   */
  getProcessingStatus(
    documentId: string
  ): Observable<DocumentProcessingStatus> {
    return this.http
      .get<DocumentStatusResponse>(`${this.baseUrl}/${documentId}/status`)
      .pipe(
        map((statusResponse: DocumentStatusResponse) => {
          // Convert backend status response to UI processing status
          const processingStatus: DocumentProcessingStatus = {
            document_id: statusResponse.document_id,
            status: statusResponse.state as DocumentState,
            progress: this.calculateProgress(statusResponse.state),
            current_step: this.getCurrentStep(statusResponse.state),
            total_steps: 3, // Upload, Process, Complete
            error_message: statusResponse.error_message,
            processing_logs: [],
            chunks_count: statusResponse.chunks_count,
            embedding_model: statusResponse.embedding_model,
            uploaded_at: statusResponse.created_at,
            updated_at: statusResponse.updated_at,
          };
          return processingStatus;
        }),
        catchError(this.handleError)
      );
  }

  /**
   * Calculate progress percentage based on document state
   */
  private calculateProgress(state: string): number {
    const progressMap: Record<string, number> = {
      pending: 0,
      processing: 50,
      processed: 100,
      failed: 0,
      deleted: 0,
    };
    return progressMap[state] || 0;
  }

  /**
   * Get current step description based on document state
   */
  private getCurrentStep(state: string): string {
    const stepMap: Record<string, string> = {
      pending: 'Queued for processing',
      processing: 'Processing document',
      processed: 'Processing complete',
      failed: 'Processing failed',
      deleted: 'Document deleted',
    };
    return stepMap[state] || 'Unknown status';
  }

  /**
   * Get all processing statuses by first getting all documents, then their statuses
   * Merges document metadata (title, timestamps) with status information
   */
  getAllProcessingStatuses(): Observable<DocumentProcessingStatus[]> {
    // First get all documents, then get status for each
    return this.getDocuments({ limit: 100, offset: 0 }).pipe(
      switchMap((response: DocumentListResponse) => {
        const documents = response.documents || [];
        if (!documents || documents.length === 0) {
          return of([]);
        }

        // Get status for each document and merge with document metadata
        const statusRequests = documents.map((doc: Document) =>
          this.getProcessingStatus(doc.id).pipe(
            map((status: DocumentProcessingStatus) => ({
              ...status,
              title: doc.title || doc.original_file_name,
              filename: doc.original_file_name,
              original_filename: doc.original_file_name,
              uploaded_at: doc.uploaded_at,
              processed_at: doc.processed_at,
            })),
            catchError(() => of(null)) // Return null for failed requests
          )
        );

        return forkJoin(statusRequests).pipe(
          map((statuses: (DocumentProcessingStatus | null)[]) =>
            statuses.filter(
              (status): status is DocumentProcessingStatus => status !== null
            )
          )
        );
      }),
      tap((statuses: DocumentProcessingStatus[]) =>
        this.processingStatusSubject.next(statuses)
      ),
      catchError(this.handleError)
    );
  }

  /**
   * Reprocess a document
   */
  reprocessDocument(documentId: string): Observable<DocumentProcessingStatus> {
    return this.http
      .post<DocumentProcessingStatus>(
        `${this.baseUrl}/${documentId}/reprocess`,
        {}
      )
      .pipe(catchError(this.handleError));
  }

  /**
   * Get document statistics
   */
  getDocumentStats(): Observable<DocumentStats> {
    return this.http
      .get<DocumentStats>(`${this.baseUrl}/stats`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get document analytics
   */
  getDocumentAnalytics(documentId: string): Observable<DocumentAnalytics> {
    return this.http
      .get<DocumentAnalytics>(`${this.baseUrl}/${documentId}/analytics`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get document versions
   */
  getDocumentVersions(documentId: string): Observable<DocumentVersion[]> {
    return this.http
      .get<DocumentVersion[]>(`${this.baseUrl}/${documentId}/versions`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Download document
   */
  downloadDocument(documentId: string): Observable<Blob> {
    return this.http
      .get(`${this.baseUrl}/${documentId}/download`, {
        responseType: 'blob',
      })
      .pipe(catchError(this.handleError));
  }

  /**
   * Get document preview
   */
  getDocumentPreview(documentId: string, page?: number): Observable<any> {
    let httpParams = new HttpParams();
    if (page) httpParams = httpParams.set('page', page.toString());

    return this.http
      .get(`${this.baseUrl}/${documentId}/preview`, { params: httpParams })
      .pipe(catchError(this.handleError));
  }

  /**
   * Perform batch operations on documents
   */
  performBatchOperation(
    operation: DocumentBatchOperation
  ): Observable<DocumentBatchResult> {
    return this.http
      .post<DocumentBatchResult>(`${this.baseUrl}/batch`, operation)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get available document classifications
   */
  getDocumentClassifications(): Observable<string[]> {
    return this.http
      .get<string[]>(`${this.baseUrl}/classifications`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get available document tags
   */
  getDocumentTags(): Observable<string[]> {
    return this.http
      .get<string[]>(`${this.baseUrl}/tags`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Update upload progress
   */
  private updateUploadProgress(progress: DocumentUploadProgress): void {
    const currentProgress = this.uploadProgressSubject.value;
    const existingIndex = currentProgress.findIndex(
      (p) => p.filename === progress.filename
    );

    if (existingIndex >= 0) {
      currentProgress[existingIndex] = progress;
    } else {
      currentProgress.push(progress);
    }

    this.uploadProgressSubject.next([...currentProgress]);
  }

  /**
   * Clear upload progress
   */
  clearUploadProgress(): void {
    this.uploadProgressSubject.next([]);
  }

  /**
   * Clear processing status
   */
  clearProcessingStatus(): void {
    this.processingStatusSubject.next([]);
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
      if (error.error?.detail) {
        errorMessage = error.error.detail;
      }
    }

    console.error('DocumentService Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
