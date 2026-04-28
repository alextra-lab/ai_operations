/**
 * Preflight Analysis Models
 *
 * Models for document chunking strategy analysis and recommendations.
 * Matches backend schemas for preflight workflow.
 */

/**
 * Chunking strategies available
 */
export enum ChunkingStrategy {
  FIXED_TOKEN = 'fixed_token',
  SLIDING_TOKEN = 'sliding_token',
  HEADING_AWARE = 'heading_aware',
  SENTENCE_PARAGRAPH = 'sentence_paragraph',
  TABLE_AWARE = 'table_aware',
  SEMANTIC_ADAPTIVE = 'semantic_adaptive',
  PAGE_BLOCK = 'page_block',
  RECURSIVE = 'recursive',
}

/**
 * Document structure analysis signals
 */
export interface StructureSignals {
  heading_density: number;
  table_ratio: number;
  list_ratio: number;
  avg_paragraph_length: number;
  sentence_count: number;
  token_count: number;
  has_code_blocks: boolean;
  has_equations: boolean;
  ocr_confidence?: number;
}

/**
 * Strategy benchmark result
 */
export interface StrategyBenchmarkResult {
  strategy: ChunkingStrategy;
  chunk_count: number;
  avg_chunk_size: number;
  std_chunk_size: number;
  processing_time_ms: number;
  hit_at_k?: number;
  mrr?: number;
  ndcg?: number;
  zero_result_rate?: number;
  score: number;
  rank?: number;
}

/**
 * Preflight recommendation
 */
export interface PreflightRecommendation {
  strategy: ChunkingStrategy;
  confidence: number;
  reasoning: string[];
  alternative_strategies: ChunkingStrategy[];
}

/**
 * Complete preflight analysis report
 */
export interface PreflightReport {
  document_id?: string;
  document_name: string;
  document_type: string;
  document_size_bytes: number;
  sample_size_tokens: number;
  structure_signals: StructureSignals;
  strategy_results: StrategyBenchmarkResult[];
  recommendation: PreflightRecommendation;
  test_suite_id?: string;
  analysis_time_ms: number;
  created_at: string;
  metadata?: Record<string, any>;
}

/**
 * Chunking configuration override
 */
export interface ChunkingConfigOverride {
  strategy: ChunkingStrategy;
  chunk_size?: number;
  chunk_overlap?: number;
  overlap?: number; // Alias for chunk_overlap for backward compatibility
  heading_levels?: number[];
  min_chunk_size?: number;
  max_chunk_size?: number;
  preserve_whitespace?: boolean;
  respect_sentence_boundaries?: boolean;
  metadata?: Record<string, any>;
}

/**
 * Preflight analysis request
 */
export interface PreflightAnalysisRequest {
  document_id?: string;
  collection_name: string;
  strategies?: ChunkingStrategy[];
  test_suite_id?: string;
  sample_size?: number;
}

/**
 * Chunking config apply result
 */
export interface ChunkingConfigApplyResult {
  success: boolean;
  document_id: string;
  strategy: ChunkingStrategy;
  chunk_count: number;
  message: string;
  metadata?: Record<string, any>;
}

/**
 * Chunking preset (saved configuration)
 */
export interface ChunkingPreset {
  id: string;
  name: string;
  description?: string;
  config: ChunkingConfigOverride;
  created_at: string;
  updated_at: string;
  usage_count: number;
}

/**
 * Strategy comparison request
 */
export interface StrategyComparisonRequest {
  document_id: string;
  strategies: ChunkingStrategy[];
  test_suite_id?: string;
  include_retrieval_metrics: boolean;
}
