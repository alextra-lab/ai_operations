/**
 * Orchestrator-related models generated from FastAPI OpenAPI spec
 */

export type RequestType =
  | 'QUERY'
  | 'RULE_GENERATION'
  | 'SUMMARIZATION'
  | 'ENRICHMENT';

export interface ProcessRequest {
  query: string;
  request_type?: RequestType | null;
  context?: Record<string, any> | null;
  stream?: boolean;
}

export interface SourceMetadata {
  document_id: string;
  title: string;
  source_type: string;
  relevance_score: number;
  content_snippet: string;
  metadata?: Record<string, any>;
}

export interface FormattedResponse {
  response: string;
  sources: SourceMetadata[];
  confidence: number;
  suggested_actions?: Record<string, any> | null;
  request_id: string;
}

export interface DocumentUploadRequest {
  file: File;
  title?: string | null;
  source?: string | null;
  author?: string | null;
  classification?: string | null;
  tags?: string | null;
  metadata?: string | null;
  process_async?: boolean;
}

export interface DocumentListParams {
  limit?: number;
  offset?: number;
  document_type?: string | null;
  tag?: string | null;
  query?: string | null;
}

export interface DocumentGetParams {
  document_id: string;
  include_preview?: boolean;
  preview_length?: number;
}

export type DocumentUpdateRequest = Record<string, any>;

export interface DocumentDeleteParams {
  document_id: string;
  force?: boolean;
}

export type QueryRequest = Record<string, any>;

export interface AnalyticsParams {
  limit?: number;
  hours?: number;
}
