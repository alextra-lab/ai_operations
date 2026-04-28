/**
 * Document management models for AI Operations Platform
 * Comprehensive TypeScript interfaces for document operations
 */

/**
 * Document interface matching backend DocumentResponse schema
 * from retrieval service /api/v1/documents/
 */
export interface Document {
  id: string;
  title: string;
  source?: string | null;
  author?: string | null;
  created_at?: string | null;
  file_type: DocumentType;
  tags: string[];
  classification: DocumentClassification;
  metadata: Record<string, any>;
  original_file_name: string;
  file_size: number;
  file_checksum: string;
  content_compressed: boolean;
  status: DocumentState;
  num_chunks?: number | null;
  error_message?: string | null;
  ingested_at: string;
  ingested_by?: string | null;
  uploaded_by?: string | null;
  uploaded_at: string;
  processed_at?: string | null;
  embedding_model?: string | null;
  embedding_provider?: string | null;
  embedding_dimensions?: number | null;
  avg_chunk_size_tokens?: number | null;
  updated_at: string;
}

export interface DocumentMetadata {
  [key: string]: any;
  pages?: number;
  word_count?: number;
  language?: string;
  created_date?: Date;
  modified_date?: Date;
  author?: string;
  subject?: string;
  keywords?: string[];
  security_classification?: string;
  retention_period?: number;
  custom_fields?: Record<string, any>;
}

/**
 * Document processing states (matches backend DocumentState enum)
 */
export enum DocumentState {
  PENDING = 'pending',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  FAILED = 'failed',
  DELETED = 'deleted',
}

/**
 * Document classification levels (matches backend DocumentClassification enum)
 */
export enum DocumentClassification {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted',
  UNCLASSIFIED = 'unclassified',
}

/**
 * Document file types (matches backend DocumentType enum)
 */
export enum DocumentType {
  PDF = 'pdf',
  DOCX = 'docx',
  TXT = 'txt',
  HTML = 'html',
  MD = 'md',
  JSON = 'json',
  CSV = 'csv',
  XLSX = 'xlsx',
  RTF = 'rtf',
  XML = 'xml',
  PPTX = 'pptx',
  UNKNOWN = 'unknown',
}

// Backward compatibility alias
export const DocumentStatus = DocumentState;

/**
 * Backend upload response (from POST /api/v1/documents/)
 */
export interface DocumentUploadResponse {
  document_id: string;
  status: string;
  message: string;
}

/**
 * Upload progress tracking for UI
 * P4-DOC-07: Enhanced with auto-detection progress details
 */
export interface DocumentUploadProgress {
  documentId: string;
  filename: string;
  progress: number;
  status:
    | 'uploading'
    | 'analyzing'
    | 'chunking'
    | 'embedding'
    | 'processing'
    | 'completed'
    | 'error';
  message?: string;
  error?: string;
  // Auto-detection progress details (P4-DOC-07)
  current_strategy?: string; // "testing: heading_aware"
  strategies_tested?: string; // "3/5"
  selected_strategy?: string; // "heading_aware"
  confidence?: number; // 0.94
  auto_detection_time_ms?: number; // 2450
}

export interface DocumentUploadRequest {
  file: File;
  collection_name?: string;
  title?: string;
  source?: string;
  author?: string;
  classification?: string;
  tags?: string[];
  metadata?: DocumentMetadata;
  process_async?: boolean;
  chunking_config?: {
    strategy?: string;
    chunk_size?: number;
    chunk_overlap?: number;
    preserve_whitespace?: boolean;
    respect_sentence_boundaries?: boolean;
  };
}

/**
 * Parameters for listing documents (matches backend API query parameters)
 */
export interface DocumentListParams {
  limit?: number;
  offset?: number;
  document_type?: string;
  tag?: string;
  query?: string;
  include_deleted?: boolean;
}

/**
 * Response from document list API
 */
export interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Filters for document search UI
 */
export interface DocumentSearchFilters {
  searchTerm: string;
  category: string;
  status: DocumentState | '';
  classification: string;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  tags: string[];
  uploadedBy: string;
}

export interface DocumentUpdateRequest {
  title?: string;
  source?: string;
  author?: string;
  classification?: string;
  tags?: string[];
  metadata?: DocumentMetadata;
}

export interface DocumentDeleteRequest {
  document_id: string;
  force?: boolean;
  reason?: string;
}

/**
 * Backend document status response (from GET /api/v1/documents/{id}/status)
 */
export interface DocumentStatusResponse {
  document_id: string;
  state: string;
  status: string;
  error_message: string | null;
  chunks_count: number | null;
  embedding_model: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Document processing status (enriched with document metadata for UI)
 */
export interface DocumentProcessingStatus {
  document_id: string;
  status: DocumentState;
  progress: number;
  current_step: string;
  total_steps: number;
  estimated_completion?: Date;
  error_message?: string | null;
  processing_logs: ProcessingLog[];
  // Merged document metadata for better UX
  title?: string;
  filename?: string;
  original_filename?: string;
  uploaded_at?: string;
  processed_at?: string | null;
  updated_at?: string;
  chunks_count?: number | null;
  embedding_model?: string | null;
}

export interface ProcessingLog {
  timestamp: Date;
  level: 'info' | 'warning' | 'error';
  message: string;
  step: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  filename: string;
  file_size: number;
  uploaded_at: Date;
  uploaded_by: string;
  change_description?: string;
  is_current: boolean;
}

/**
 * Document statistics (matches backend /api/v1/documents/stats response)
 */
export interface DocumentStats {
  total_documents: number;
  total_size_bytes: number;
  documents_by_type: Record<string, number>;
  documents_by_state: Record<string, number>;
  documents_by_classification: Record<string, number>;
  recent_uploads: number;
  processing_success_rate: number;
  avg_chunks_per_document: number;
  avg_processing_time_ms: number | null;
}

export interface DocumentBatchOperation {
  operation: 'delete' | 'update' | 'reprocess' | 'archive';
  document_ids: string[];
  parameters?: Record<string, any>;
}

export interface DocumentBatchResult {
  operation: string;
  total_processed: number;
  successful: number;
  failed: number;
  errors: { document_id: string; error: string }[];
}

// File upload related interfaces
export interface FileUploadConfig {
  maxFileSize: number; // in bytes
  allowedTypes: string[];
  maxFiles: number;
  chunkSize: number; // for large file uploads
  retryAttempts: number;
  retryDelay: number;
}

export interface UploadedFile {
  file: File;
  id: string;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
  document?: Document;
}

// Document library display interfaces
export interface DocumentLibraryView {
  view_type: 'grid' | 'list' | 'table';
  sort_by: string;
  sort_order: 'asc' | 'desc';
  filters: DocumentSearchFilters;
  page_size: number;
  current_page: number;
}

export interface DocumentLibraryConfig {
  default_view: DocumentLibraryView;
  available_views: DocumentLibraryView[];
  batch_operations: string[];
  export_formats: string[];
  preview_enabled: boolean;
  metadata_editing_enabled: boolean;
}

// Document preview interfaces
export interface DocumentPreview {
  document_id: string;
  content_type: string;
  preview_content: string;
  page_count?: number;
  current_page?: number;
  thumbnail_url?: string;
  full_text?: string;
  extracted_metadata?: DocumentMetadata;
}

// Document sharing and collaboration
export interface DocumentShare {
  document_id: string;
  shared_with: string[];
  permissions: DocumentPermission[];
  expires_at?: Date;
  created_by: string;
  created_at: Date;
}

export interface DocumentPermission {
  user_id: string;
  permission: 'read' | 'write' | 'admin';
  granted_by: string;
  granted_at: Date;
}

// Document analytics and insights
export interface DocumentAnalytics {
  document_id: string;
  view_count: number;
  download_count: number;
  last_accessed: Date;
  access_patterns: DocumentAccessPattern[];
  related_documents: string[];
  search_queries: string[];
}

export interface DocumentAccessPattern {
  user_id: string;
  action: 'view' | 'download' | 'edit' | 'share';
  timestamp: Date;
  duration?: number; // in seconds
  ip_address?: string;
  user_agent?: string;
}
