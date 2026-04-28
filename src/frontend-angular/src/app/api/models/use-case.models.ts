/**
 * Use Case Execution Interface - Data Models
 * Comprehensive TypeScript interfaces for the Use-Case-Driven AI Assistant
 */

// ============================================================================
// Core Use Case Models
// ============================================================================

export interface UseCase {
  id: string;
  use_case_id: string;
  name: string;
  description: string;
  category: string;
  intent_type: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
  created_by: string;
  is_active: boolean;
  visibility_config?: VisibilityConfig;
}

export interface UseCaseListResponse {
  use_cases: UseCase[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface VisibilityConfig {
  roles: string[];
  tags: string[];
  is_public: boolean;
}

// ============================================================================
// Use Case Execution Models
// ============================================================================

export interface UseCaseExecution {
  use_case_id: string;
  inputs: Record<string, any>;
  overrides?: ExecutionOverrides;
}

export interface ExecutionOverrides {
  temperature?: number;
  top_k?: number;
  streaming?: boolean;
  similarity_threshold?: number;
  max_tokens?: number;
  model_id?: string;
  embedding_model?: string;
}

export interface ExecutionResponse {
  response: string;
  sources: SourceMetadata[];
  metrics: ConsolidatedMetrics;
  suggested_actions?: SuggestedAction[];
  request_id: string;
  execution_time_ms: number;
  timestamp: string;
  /** Parsed structured output when output_contract.format is json/yaml/structured */
  structured_data?: Record<string, unknown>;
  /** Portable Vega-Lite visualization spec (ADR-068) */
  visualization_spec?: {
    version: string;
    layout: 'single' | 'grid' | 'tabs';
    sections: Array<{
      section_id: string;
      title: string;
      type: 'vega-lite' | 'table';
      vega_lite_spec?: Record<string, unknown>;
      table_spec?: Record<string, unknown>;
      width?: string;
    }>;
  };
}

export interface ExecutionError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  request_id?: string;
}

// ============================================================================
// Source Citation Models
// ============================================================================

export interface SourceMetadata {
  document_id: string;
  title: string;
  source: string;
  author?: string;
  similarity_score: number;
  page_number?: number;
  chunk_text?: string; // Optional for backward compatibility
  content?: string; // New field from /process endpoint
  chunk_index: number;
  document_type: string;
  classification?: string;
  created_at: string;
  url?: string;
}

export interface SourceCitation {
  source: SourceMetadata;
  relevance_score: number;
  confidence_level: 'high' | 'medium' | 'low';
  highlighted_text?: string;
}

// ============================================================================
// Metrics Models
// ============================================================================

export interface ConsolidatedMetrics {
  retrieval: RetrievalMetrics;
  guard: GuardMetrics;
  model: ModelMetrics;
  confidence_score: number;
  calculation_method?: string;
}

export interface RetrievalMetrics {
  top_k: number;
  hits: number;
  avg_similarity: number;
  min_similarity: number;
  max_similarity: number;
  source_count: number;
}

export interface GuardMetrics {
  risk_score: number;
  modified: boolean;
  details: Record<string, any>;
}

export interface GuardDetails {
  // Primary security flags (aligned with LLM Guard scanners)
  pii_detected: boolean; // anonymize scanner
  jailbreak_attempt: boolean; // prompt_injection scanner
  secrets_detected: boolean; // secrets + regex scanners
  gibberish_detected: boolean; // gibberish scanner
  invalid_language: boolean; // language scanner
  content_filtered: boolean; // aggregate of all failed scanners

  // Legacy flag (not currently implemented in LLM Guard)
  toxicity_detected: boolean;

  // Scanner details
  blocked_categories?: string[];
  scanners?: Record<string, any>;
}

export interface ModelMetrics {
  model_id: string;
  tokens_in: number;
  tokens_out: number;
  total_tokens: number;
  processing_time: number;
  metadata: ModelMetadata;
}

export interface ModelMetadata {
  cost_estimate?: number;
  cost_breakdown?: CostBreakdown;
  parameters?: ModelParameters;
  timing_breakdown?: TimingBreakdown;
  [key: string]: any;
}

export interface CostBreakdown {
  input_cost: number;
  output_cost: number;
  total_cost: number;
  currency: string;
  pricing_source: string;
  pricing_per_million?: {
    input: number;
    output: number;
  };
}

export interface ModelParameters {
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
}

export interface TimingBreakdown {
  retrieval_time?: number;
  guard_time?: number;
  model_time?: number;
  total_time?: number;
  breakdown?: {
    retrieval_pct?: number;
    guard_pct?: number;
    model_pct?: number;
  };
}

// ============================================================================
// Suggested Actions Models
// ============================================================================

export interface SuggestedAction {
  id: string;
  type: 'query' | 'document' | 'analysis' | 'export';
  title: string;
  description: string;
  parameters: Record<string, any>;
  confidence: number;
  icon?: string;
}

// ============================================================================
// Use Case Configuration Models
// ============================================================================

/** User prompt template with {{variable}} placeholders (Phase 2 authoring). */
export interface UserPromptTemplateConfig {
  template: string;
  variables: string[];
  fallback_mode: 'concatenate' | 'error';
}

/** Output contract (format, validation, optional visualization template). */
export interface OutputContractConfig {
  format: string;
  validation_mode: string;
  output_schema?: Record<string, unknown> | null;
  template_id?: string | null;
}

export interface UseCaseConfig {
  use_case_id: string;
  name: string;
  description: string;
  category: string;
  intent_type: string;
  template_config: TemplateConfig;
  visibility_config: VisibilityConfig;
  execution_config: ExecutionConfig;
  ui_config: UIConfig;
  /** Output contract when returned by config API (e.g. from config_json). */
  output_contract?: OutputContractConfig;
}

export interface TemplateConfig {
  input_fields: InputField[];
  output_format: 'text' | 'json' | 'structured';
  validation_rules?: ValidationRule[];
  examples?: UseCaseExample[];
}

/** Supported input field types (align with backend InputFieldType). */
export type InputFieldType =
  | 'text'
  | 'textarea'
  | 'select'
  | 'number'
  | 'checkbox'
  | 'date';

export interface InputField {
  name: string;
  type: InputFieldType | 'multiselect' | 'boolean' | 'file'; // legacy kept
  label: string;
  description?: string;
  required: boolean;
  default_value?: string | number | boolean;
  options?: SelectOption[];
  validation?: FieldValidation;
  placeholder?: string;
}

export interface SelectOption {
  value: string | number;
  label: string;
  description?: string;
}

export interface FieldValidation {
  min_length?: number;
  max_length?: number;
  min_value?: number;
  max_value?: number;
  pattern?: string;
  pattern_message?: string;
  custom_validator?: string;
}

export interface ValidationRule {
  field_name: string;
  rule_type: 'required' | 'min_length' | 'max_length' | 'pattern' | 'custom';
  value?: any;
  error_message: string;
}

export interface UseCaseExample {
  title: string;
  description: string;
  inputs: Record<string, any>;
  expected_output?: string;
}

export interface ExecutionConfig {
  default_model: string;
  default_temperature: number;
  default_top_k: number;
  default_similarity_threshold: number;
  supports_streaming: boolean;
  max_execution_time_ms: number;
  retry_config?: RetryConfig;
}

export interface RetryConfig {
  max_attempts: number;
  backoff_ms: number;
  retryable_errors: string[];
}

export interface UIConfig {
  icon: string;
  color: string;
  layout: 'single' | 'multi-column' | 'wizard';
  show_metrics: boolean;
  show_sources: boolean;
  show_suggestions: boolean;
  enable_history: boolean;
  custom_css?: string;
}

// ============================================================================
// Query History Integration Models
// ============================================================================

export interface UseCaseHistory {
  id: string;
  use_case_id: string;
  user_id: string;
  inputs: Record<string, any>;
  overrides?: ExecutionOverrides;
  response: string;
  metrics: ConsolidatedMetrics;
  sources: SourceMetadata[];
  execution_time_ms: number;
  created_at: string;
  status: 'completed' | 'failed' | 'partial';
  error?: ExecutionError;
  tags?: string[];
  is_favorite: boolean;
}

export interface UseCaseHistoryResponse {
  history: UseCaseHistory[];
  total: number;
  page: number;
  size: number;
}

export interface UseCaseHistoryRequest {
  use_case_id?: string;
  user_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  date_range?: DateRange;
  tags?: string[];
  is_favorite?: boolean;
}

export interface DateRange {
  start_date: string;
  end_date: string;
}

// ============================================================================
// Real-time Execution Models
// ============================================================================

export interface ExecutionProgress {
  request_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  current_step: string;
  estimated_completion_ms?: number;
  error?: ExecutionError;
}

export interface StreamingResponse {
  type: 'chunk' | 'metrics' | 'sources' | 'complete' | 'error';
  data: any;
  request_id: string;
  timestamp?: string;
  full_response?: string; // Accumulated response so far
  sources?: any[]; // Sources from backend
  metrics?: any; // Metrics from backend
}

// ============================================================================
// Utility Types
// ============================================================================

export type UseCaseStatus = 'active' | 'inactive' | 'draft' | 'archived';
export type ExecutionStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';
export type ConfidenceLevel = 'high' | 'medium' | 'low';
export type MetricStatus = 'success' | 'warning' | 'error';

// ============================================================================
// API Request/Response Wrappers
// ============================================================================

export interface UseCaseExecutionRequest {
  execution: UseCaseExecution;
  user_id: string;
  session_id?: string;
  client_info?: ClientInfo;
}

export interface ClientInfo {
  user_agent: string;
  ip_address?: string;
  session_id?: string;
  client_version: string;
}

export interface UseCaseExecutionResult {
  success: boolean;
  data?: ExecutionResponse;
  error?: ExecutionError;
  request_id: string;
  execution_time_ms: number;
}
