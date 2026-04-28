/**
 * Corpus service for document preflight analysis (ADR-034).
 *
 * Handles preflight analysis for intelligent chunking strategy selection.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ChunkingStrategy,
  PreflightReport,
} from '../api/models/preflight.models';

export interface PreflightRequest {
  file?: File;
  document_id?: string;
  collection_id: string;
  test_suite_id?: string;
  run_retrieval_metrics?: boolean;
}

export interface ChunkingConfigRequest {
  strategy: ChunkingStrategy;
  chunk_size?: number;
  overlap?: number;
  heading_levels?: number[];
  min_chunk_size?: number;
  max_chunk_size?: number;
  metadata?: Record<string, any>;
}

@Injectable({
  providedIn: 'root',
})
export class CorpusService {
  private readonly apiUrl = `${environment.apiBaseUrl}/corpus`;

  constructor(private http: HttpClient) {}

  /**
   * Run preflight analysis on a document.
   */
  runPreflight(request: PreflightRequest): Observable<PreflightReport> {
    const formData = new FormData();

    if (request.file) {
      formData.append('file', request.file);
    }

    if (request.document_id) {
      formData.append('document_id', request.document_id);
    }

    formData.append('collection_id', request.collection_id);

    if (request.test_suite_id) {
      formData.append('test_suite_id', request.test_suite_id);
    }

    if (request.run_retrieval_metrics !== undefined) {
      formData.append(
        'run_retrieval_metrics',
        request.run_retrieval_metrics.toString()
      );
    }

    return this.http.post<PreflightReport>(
      `${this.apiUrl}/preflight`,
      formData
    );
  }

  /**
   * Get preflight report by ID.
   */
  getPreflightReport(reportId: string): Observable<PreflightReport> {
    return this.http.get<PreflightReport>(
      `${this.apiUrl}/preflight/${reportId}`
    );
  }

  /**
   * Apply chunking configuration to a document.
   */
  applyChunkingConfig(
    documentId: string,
    collectionId: string,
    config: ChunkingConfigRequest
  ): Observable<{
    document_id: string;
    chunks_created: number;
    strategy: ChunkingStrategy;
  }> {
    return this.http.post<{
      document_id: string;
      chunks_created: number;
      strategy: ChunkingStrategy;
    }>(`${this.apiUrl}/documents/${documentId}/chunk`, {
      collection_id: collectionId,
      ...config,
    });
  }

  /**
   * Get available chunking strategies.
   */
  getAvailableStrategies(): ChunkingStrategy[] {
    return [
      ChunkingStrategy.FIXED_TOKEN,
      ChunkingStrategy.SLIDING_TOKEN,
      ChunkingStrategy.HEADING_AWARE,
      ChunkingStrategy.SENTENCE_PARAGRAPH,
      ChunkingStrategy.TABLE_AWARE,
      ChunkingStrategy.SEMANTIC_ADAPTIVE,
      ChunkingStrategy.PAGE_BLOCK,
      ChunkingStrategy.RECURSIVE,
    ];
  }
}
