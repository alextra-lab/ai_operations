/**
 * Query-related models for semantic search, RAG Q&A, and query history
 */

export type QueryType =
  | 'SEMANTIC_SEARCH'
  | 'RAG_QA'
  | 'DOCUMENT_SEARCH'
  | 'ANALYTICS_QUERY';

export type QueryStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type SearchResultType = 'DOCUMENT' | 'CHUNK' | 'METADATA' | 'SUMMARY';

export type SortOrder =
  | 'RELEVANCE'
  | 'DATE_DESC'
  | 'DATE_ASC'
  | 'TITLE_ASC'
  | 'TITLE_DESC';

export interface SearchFilter {
  document_type?: string[];
  date_range?: {
    start_date: string;
    end_date: string;
  };
  tags?: string[];
  classification?: string[];
  author?: string[];
  source?: string[];
  confidence_threshold?: number;
}

export interface SearchSort {
  field: string;
  order: SortOrder;
}

export interface SemanticSearchRequest {
  query: string;
  filters?: SearchFilter;
  sort?: SearchSort;
  limit?: number;
  offset?: number;
  include_snippets?: boolean;
  highlight_matches?: boolean;
  search_type?: QueryType;
  context?: Record<string, any>;
  threshold?: number;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  snippet: string;
  source_type: SearchResultType;
  document_id?: string;
  chunk_index?: number;
  relevance_score: number;
  confidence: number;
  metadata: {
    author?: string;
    source?: string;
    classification?: string;
    tags?: string[];
    created_date?: string;
    modified_date?: string;
    file_type?: string;
    file_size?: number;
    [key: string]: any;
  };
  highlighted_content?: string;
  suggested_actions?: string[];
}

export interface SemanticSearchResponse {
  results: SearchResult[];
  total_count: number;
  query_id: string;
  processing_time_ms: number;
  search_metadata: {
    search_type: QueryType;
    filters_applied: SearchFilter;
    sort_applied: SearchSort;
    suggestions?: string[];
    related_queries?: string[];
  };
  pagination: {
    current_page: number;
    total_pages: number;
    page_size: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface RAGQuestionRequest {
  question: string;
  context_documents?: string[];
  include_sources?: boolean;
  max_context_length?: number;
  temperature?: number;
  model_preference?: string;
  conversation_id?: string;
}

export interface RAGAnswer {
  answer: string;
  confidence: number;
  sources: RAGSource[];
  reasoning?: string;
  follow_up_questions?: string[];
  conversation_id: string;
  message_id: string;
}

export interface RAGSource {
  document_id: string;
  title: string;
  content_snippet: string;
  relevance_score: number;
  page_number?: number;
  chunk_index?: number;
  metadata: {
    author?: string;
    source?: string;
    classification?: string;
    created_date?: string;
    [key: string]: any;
  };
}

export interface RAGQAResponse {
  answer: RAGAnswer;
  processing_time_ms: number;
  model_used: string;
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  context_retrieved: {
    documents_count: number;
    total_chunks: number;
    context_length_tokens: number;
  };
}

export interface QueryHistory {
  id: string;
  query_text: string; // Backend field name
  intent_type?: string; // Backend field name (nullable)
  response_status: string; // Backend field name
  created_at: string;
  updated_at: string;
  user_id: string;
  run_id: string; // Backend includes this
  use_case_id?: string; // Backend includes this
  use_case_name?: string; // Backend includes this
  center_id?: string; // Backend includes this
  query_params?: Record<string, any>; // Backend includes this
  response_text?: string; // Backend includes this
  metrics?: Record<string, any>; // Backend includes this
  processing_time_ms?: number; // Correct field name
  sources?: Record<string, any>; // Backend includes this
  citations?: Record<string, any>; // Backend includes this
  parent_query_id?: string; // For forked queries
  thread_id?: string; // Backend includes this
  fork_count?: number; // Backend includes this
  archived_at?: string; // Backend includes this
  metadata_json?: Record<string, any>; // Backend field name (not metadata)
  // Legacy/UI-specific fields (not from backend)
  tags?: string[];
  is_favorite?: boolean;
  is_shared?: boolean;
  shared_with?: string[];
}

export interface QueryHistoryRequest {
  limit?: number;
  offset?: number;
  use_case_id?: string;
  intent_type?: string;
  response_status?: string;
  search_query?: string;
}

export interface QueryHistoryResponse {
  items: QueryHistory[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface QueryForkRequest {
  parent_query_id: string;
  modifications: {
    query_text?: string;
    filters?: SearchFilter;
    sort?: SearchSort;
    context?: Record<string, any>;
  };
  fork_reason?: string;
}

export interface QueryForkResponse {
  forked_query: QueryHistory;
  parent_query: QueryHistory;
  modifications_applied: QueryForkRequest['modifications'];
}

export interface QueryAnalytics {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  average_response_time_ms: number;
  most_common_queries: {
    query: string;
    count: number;
    success_rate: number;
  }[];
  query_types_distribution: {
    query_type: QueryType;
    count: number;
    percentage: number;
  }[];
  time_series_data: {
    timestamp: string;
    query_count: number;
    avg_response_time_ms: number;
  }[];
  user_activity: {
    user_id: string;
    query_count: number;
    last_query_date: string;
  }[];
}

export interface QueryPerformanceMetrics {
  query_id: string;
  start_time: string;
  end_time: string;
  processing_time_ms: number;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  api_calls_count: number;
  cache_hits: number;
  cache_misses: number;
  documents_processed: number;
  tokens_processed: number;
  error_details?: {
    error_type: string;
    error_message: string;
    stack_trace?: string;
  };
}

// Form models for UI components
export interface QueryFormData {
  query_text: string;
  search_type: QueryType;
  filters: SearchFilter;
  sort: SearchSort;
  limit: number;
  include_snippets: boolean;
  highlight_matches: boolean;
}

export interface RAGFormData {
  question: string;
  include_sources: boolean;
  max_context_length: number;
  temperature: number;
  model_preference: string;
}

export interface QueryHistoryFilters {
  query_type?: QueryType;
  status?: QueryStatus;
  date_range?: {
    start_date: string;
    end_date: string;
  };
  tags?: string[];
  is_favorite?: boolean;
  user_id?: string;
}

// Error models
export interface QueryError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  query_id?: string;
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

// WebSocket models for real-time updates
export interface QueryProgressUpdate {
  query_id: string;
  status: QueryStatus;
  progress_percentage: number;
  current_step: string;
  estimated_completion_time?: string;
  results_count?: number;
  error?: QueryError;
}

export interface RealTimeSearchResult {
  query_id: string;
  result: SearchResult;
  result_index: number;
  is_final: boolean;
}

// Configuration models
export interface QueryConfiguration {
  default_search_type: QueryType;
  default_limit: number;
  max_limit: number;
  default_filters: SearchFilter;
  available_sort_options: SearchSort[];
  supported_file_types: string[];
  max_query_length: number;
  cache_settings: {
    enabled: boolean;
    ttl_seconds: number;
    max_entries: number;
  };
  real_time_settings: {
    enabled: boolean;
    update_interval_ms: number;
    max_concurrent_queries: number;
  };
}
