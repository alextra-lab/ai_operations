/**
 * Preflight Analysis Service
 *
 * Service for document chunking strategy analysis and optimization.
 * Provides AI-powered recommendations for optimal chunking configuration.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, catchError, map, of, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ChunkingConfigApplyResult,
  ChunkingConfigOverride,
  ChunkingPreset,
  ChunkingStrategy,
  PreflightReport,
  StrategyBenchmarkResult,
  StrategyComparisonRequest,
} from '../models/preflight.models';

@Injectable({
  providedIn: 'root',
})
export class PreflightService {
  private baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) { }

  /**
   * Analyze document and get chunking strategy recommendations
   *
   * Uploads file to backend which extracts text, analyzes structure,
   * benchmarks strategies, and returns AI-powered recommendations.
   *
   * Backend handles PDF/DOCX/TXT extraction automatically.
   */
  analyzeDocument(
    file: File,
    collectionName: string,
    strategies?: ChunkingStrategy[],
    testSuiteId?: string
  ): Observable<PreflightReport> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', collectionName);

    if (strategies && strategies.length > 0) {
      formData.append('strategies', JSON.stringify(strategies));
    }

    if (testSuiteId) {
      formData.append('test_suite_id', testSuiteId);
    }

    return this.http
      .post<PreflightReport>(
        `${this.baseUrl}/chunking/preflight/analyze`,
        formData
      )
      .pipe(
        catchError((error) => {
          console.error('Preflight analysis failed:', error);
          const errorMsg =
            error.error?.detail ||
            error.message ||
            'Failed to analyze document. Please try again.';
          return throwError(() => new Error(errorMsg));
        })
      );
  }

  /**
   * Run detailed strategy comparison with retrieval metrics
   *
   * Requires a test suite for retrieval quality metrics.
   */
  compareStrategies(
    request: StrategyComparisonRequest
  ): Observable<StrategyBenchmarkResult[]> {
    return this.http
      .post<{
        results: StrategyBenchmarkResult[];
      }>(`${this.baseUrl}/chunking/compare`, request)
      .pipe(
        map((response) => response.results),
        catchError((error) => {
          console.error('Strategy comparison failed:', error);
          return throwError(
            () =>
              new Error(error.error?.detail || 'Failed to compare strategies.')
          );
        })
      );
  }

  /**
   * Apply chunking configuration to document
   *
   * Applies the specified chunking config and re-processes the document.
   */
  applyChunkingConfig(
    documentId: string,
    config: ChunkingConfigOverride
  ): Observable<ChunkingConfigApplyResult> {
    return this.http
      .post<ChunkingConfigApplyResult>(`${this.baseUrl}/chunking/apply`, {
        document_id: documentId,
        config: config,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to apply chunking config:', error);
          return throwError(
            () =>
              new Error(error.error?.detail || 'Failed to apply configuration.')
          );
        })
      );
  }

  /**
   * Get available chunking strategies
   */
  getAvailableStrategies(): Observable<ChunkingStrategy[]> {
    return this.http.get<string[]>(`${this.baseUrl}/chunking/strategies`).pipe(
      map((strategies) => strategies as ChunkingStrategy[]),
      catchError(() => {
        // Fallback to default strategies
        return of(Object.values(ChunkingStrategy));
      })
    );
  }

  /**
   * Get default configuration for a strategy
   */
  getStrategyDefaultConfig(
    strategy: ChunkingStrategy
  ): Observable<ChunkingConfigOverride> {
    return this.http
      .get<ChunkingConfigOverride>(
        `${this.baseUrl}/chunking/strategies/${strategy}/config`
      )
      .pipe(
        catchError((error) => {
          console.error('Failed to get strategy config:', error);
          // Return sensible defaults
          return of(this.getDefaultConfig(strategy));
        })
      );
  }

  /**
   * Save chunking configuration as preset
   */
  savePreset(
    name: string,
    description: string,
    config: ChunkingConfigOverride
  ): Observable<ChunkingPreset> {
    return this.http
      .post<ChunkingPreset>(`${this.baseUrl}/chunking/presets`, {
        name,
        description,
        config,
      })
      .pipe(
        catchError((error) => {
          console.error('Failed to save preset:', error);
          return throwError(
            () => new Error(error.error?.detail || 'Failed to save preset.')
          );
        })
      );
  }

  /**
   * Get saved presets
   */
  getPresets(): Observable<ChunkingPreset[]> {
    return this.http
      .get<{ presets: ChunkingPreset[] }>(`${this.baseUrl}/chunking/presets`)
      .pipe(
        map((response) => response.presets || []),
        catchError(() => of([]))
      );
  }

  /**
   * Delete preset
   */
  deletePreset(presetId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.baseUrl}/chunking/presets/${presetId}`
    );
  }

  /**
   * Get default configuration for a strategy (client-side fallback)
   */
  private getDefaultConfig(strategy: ChunkingStrategy): ChunkingConfigOverride {
    const defaults: Record<ChunkingStrategy, ChunkingConfigOverride> = {
      [ChunkingStrategy.FIXED_TOKEN]: {
        strategy: ChunkingStrategy.FIXED_TOKEN,
        chunk_size: 512,
        chunk_overlap: 50,
        min_chunk_size: 64,
        max_chunk_size: 2048,
        preserve_whitespace: true,
        respect_sentence_boundaries: true,
      },
      [ChunkingStrategy.SLIDING_TOKEN]: {
        strategy: ChunkingStrategy.SLIDING_TOKEN,
        chunk_size: 512,
        chunk_overlap: 100,
        min_chunk_size: 64,
        max_chunk_size: 2048,
        preserve_whitespace: true,
        respect_sentence_boundaries: true,
      },
      [ChunkingStrategy.HEADING_AWARE]: {
        strategy: ChunkingStrategy.HEADING_AWARE,
        chunk_size: 1024,
        chunk_overlap: 50,
        min_chunk_size: 128,
        max_chunk_size: 4096,
        heading_levels: [1, 2, 3],
        preserve_whitespace: true,
        respect_sentence_boundaries: false,
      },
      [ChunkingStrategy.SENTENCE_PARAGRAPH]: {
        strategy: ChunkingStrategy.SENTENCE_PARAGRAPH,
        chunk_size: 768,
        chunk_overlap: 50,
        min_chunk_size: 128,
        max_chunk_size: 2048,
        preserve_whitespace: true,
        respect_sentence_boundaries: true,
      },
      [ChunkingStrategy.TABLE_AWARE]: {
        strategy: ChunkingStrategy.TABLE_AWARE,
        chunk_size: 1024,
        chunk_overlap: 0,
        min_chunk_size: 256,
        max_chunk_size: 4096,
        preserve_whitespace: true,
        respect_sentence_boundaries: false,
      },
      [ChunkingStrategy.SEMANTIC_ADAPTIVE]: {
        strategy: ChunkingStrategy.SEMANTIC_ADAPTIVE,
        chunk_size: 768,
        chunk_overlap: 50,
        min_chunk_size: 128,
        max_chunk_size: 2048,
        preserve_whitespace: true,
        respect_sentence_boundaries: true,
      },
      [ChunkingStrategy.PAGE_BLOCK]: {
        strategy: ChunkingStrategy.PAGE_BLOCK,
        chunk_size: 2048,
        chunk_overlap: 0,
        min_chunk_size: 512,
        max_chunk_size: 8192,
        preserve_whitespace: true,
        respect_sentence_boundaries: false,
      },
      [ChunkingStrategy.RECURSIVE]: {
        strategy: ChunkingStrategy.RECURSIVE,
        chunk_size: 512,
        chunk_overlap: 50,
        min_chunk_size: 64,
        max_chunk_size: 2048,
        preserve_whitespace: true,
        respect_sentence_boundaries: true,
      },
    };

    return defaults[strategy];
  }

  /**
   * Format strategy enum to human-readable name
   */
  formatStrategyName(strategy: ChunkingStrategy): string {
    const names: Record<ChunkingStrategy, string> = {
      [ChunkingStrategy.FIXED_TOKEN]: 'Fixed Token',
      [ChunkingStrategy.SLIDING_TOKEN]: 'Sliding Window',
      [ChunkingStrategy.HEADING_AWARE]: 'Heading Aware',
      [ChunkingStrategy.SENTENCE_PARAGRAPH]: 'Sentence/Paragraph',
      [ChunkingStrategy.TABLE_AWARE]: 'Table Aware',
      [ChunkingStrategy.SEMANTIC_ADAPTIVE]: 'Semantic Adaptive',
      [ChunkingStrategy.PAGE_BLOCK]: 'Page Block',
      [ChunkingStrategy.RECURSIVE]: 'Recursive',
    };
    return names[strategy] || strategy;
  }
}
