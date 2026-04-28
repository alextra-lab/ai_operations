/**
 * Query Configuration Models
 *
 * Models for query developer tools configuration including
 * sampling presets, RAG parameters, and advanced vector DB settings.
 *
 * Related ADRs:
 * - ADR-023: Sampling Presets and Guardrails
 * - ADR-045: Query Developer Tools Architecture
 */

// ============================================================================
// Sampling Presets (ADR-023)
// ============================================================================

export enum SamplingPreset {
  STRICT = 'STRICT',
  BALANCED = 'BALANCED',
  CREATIVE = 'CREATIVE',
  CUSTOM = 'CUSTOM',
}

export interface SamplingConfig {
  preset: SamplingPreset;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  presence_penalty?: number;
  frequency_penalty?: number;
}

// ============================================================================
// RAG Configuration
// ============================================================================

export interface RAGConfig {
  enabled: boolean;
  vector_collections: string[];
  top_k: number;
  similarity_threshold: number;
  hybrid_bm25?: boolean;
  reranking_enabled?: boolean;
}

// ============================================================================
// Vector DB Configuration
// ============================================================================

export interface VectorDBConfig {
  ef_search?: number;
  score_normalization?: boolean;
  filter_strategy?: 'pre' | 'post';
}

// ============================================================================
// Query Configuration
// ============================================================================

export interface QueryConfig {
  // Model configuration (LLM only - embedding model is system-determined)
  llm_model: string;

  // Sampling configuration
  sampling: SamplingConfig;

  // RAG configuration (retrieval parameters)
  rag: RAGConfig;

  // Advanced vector DB settings
  vector_db?: VectorDBConfig;

  // Query metadata
  query_type?: 'semantic' | 'rag' | 'usecase';
  timeout_ms?: number;
}

// ============================================================================
// Execution Metrics
// ============================================================================

export interface ExecutionTiming {
  retrieval_time_ms?: number;
  guard_time_ms?: number;
  generation_time_ms?: number;
  total_time_ms: number;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface CostEstimate {
  input_cost: number;
  output_cost: number;
  total_cost: number;
  currency: string;
}

export interface ExecutionMetrics {
  timing: ExecutionTiming;
  tokens: TokenUsage;
  cost?: CostEstimate;
  confidence_score?: number;

  // Optional detailed metrics
  retrieval?: {
    chunks_retrieved: number;
    avg_similarity: number;
    collections_searched: string[];
  };

  guard?: {
    risk_score: number;
    checks_performed: string[];
    warnings: string[];
  };

  model?: {
    model_id: string;
    provider: string;
    latency_ms: number;
  };
}

// ============================================================================
// Message Models
// ============================================================================

export interface Message {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  token_count?: number;
  metadata?: Record<string, any>;
}

export interface MessageAction {
  action: 'copy' | 'regenerate' | 'edit' | 'delete';
  message: Message;
}

// ============================================================================
// Source Metadata (for results panel)
// ============================================================================

export interface SourceMetadata {
  document_id: string;
  title: string;
  content_snippet: string;
  relevance_score: number;
  page_number?: number;
  chunk_index?: number;
  metadata?: {
    author?: string;
    source?: string;
    classification?: string;
    created_date?: string;
    [key: string]: any;
  };
}

// ============================================================================
// Configuration Validation
// ============================================================================

export interface ConfigValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  high_entropy_detected?: boolean;
}

// ============================================================================
// Query Configuration Helpers
// ============================================================================

/**
 * Get default sampling values for a preset
 */
export function getPresetValues(
  preset: SamplingPreset
): Partial<SamplingConfig> {
  const presets: Record<SamplingPreset, Partial<SamplingConfig>> = {
    [SamplingPreset.STRICT]: {
      temperature: 0.15,
      top_p: 0.9,
      max_tokens: 1024,
    },
    [SamplingPreset.BALANCED]: {
      temperature: 0.65,
      top_p: 0.95,
      max_tokens: 2048,
    },
    [SamplingPreset.CREATIVE]: {
      temperature: 0.85,
      top_p: 0.97,
      max_tokens: 4096,
    },
    [SamplingPreset.CUSTOM]: {},
  };

  return presets[preset] || presets[SamplingPreset.BALANCED];
}

/**
 * Detect high-entropy configuration (ADR-023)
 */
export function isHighEntropyConfig(config: SamplingConfig): boolean {
  const temp = config.temperature ?? 0.65;
  const topP = config.top_p ?? 0.95;

  // High-entropy detection: temp > 0.9 AND top_p > 0.97
  return temp > 0.9 && topP > 0.97;
}

/**
 * Get default QueryConfig
 */
export function getDefaultQueryConfig(): QueryConfig {
  return {
    llm_model: 'gpt-4o-mini',
    // embedding_model removed - determined by collection metadata
    sampling: {
      preset: SamplingPreset.BALANCED,
      temperature: 0.65,
      top_p: 0.95,
      max_tokens: 2048,
    },
    rag: {
      enabled: true,
      vector_collections: ['documents'],
      top_k: 10,
      similarity_threshold: 0.6,
      hybrid_bm25: false,
    },
    vector_db: {
      ef_search: 128,
      score_normalization: false,
    },
    query_type: 'rag',
    timeout_ms: 30000,
  };
}
