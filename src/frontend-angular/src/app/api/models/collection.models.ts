/**
 * TypeScript models for Collection Management
 *
 * These interfaces mirror the backend Pydantic schemas for collection
 * management, ensuring type safety in the Angular frontend.
 *
 * See:
 * - Backend: src/retrieval/app/schemas/collections.py
 * - ADR: docs/development/adrs/ADR-021-Collection-Based-Document-Management.md
 */

/**
 * Collection entity representing a logical grouping of documents
 * with a specific embedding model binding.
 */
export interface Collection {
  /** Unique identifier (UUID) */
  id: string;

  /** Collection name (lowercase, alphanumeric, underscores, hyphens) */
  name: string;

  /** Optional description */
  description?: string;

  /** Embedding model identifier (immutable after creation) */
  embedding_model: string;

  /** Embedding provider: 'openai' or 'local' (immutable after creation) */
  embedding_provider: string;

  /** Vector dimensions for this embedding model (immutable after creation) */
  embedding_dimensions: number;

  /** Qdrant collection name mapping (format: fc_{name}_{hash8}) */
  qdrant_collection_name: string;

  /** True if this is the system default collection */
  is_default: boolean;

  /** True if collection is active and available for use */
  is_active: boolean;

  /** True if collection is system-managed (cannot be deleted) */
  is_system_managed: boolean;

  /** Username of creator */
  created_by: string;

  /** Creation timestamp (ISO 8601) */
  created_at: string;

  /** Last update timestamp (ISO 8601) */
  updated_at: string;

  /** Number of documents in this collection (cached, auto-updated) */
  document_count: number;

  /** Sample size in tokens for preflight analysis during auto-detection */
  preflight_sample_tokens: number;

  /** List of chunking strategies to test during auto-detection */
  preflight_strategies: string[];

  /** Whether auto-chunking is enabled for this collection */
  auto_chunk_enabled: boolean;
}

/**
 * Request payload for creating a new collection
 */
export interface CollectionCreate {
  /** Collection name (3-255 chars, lowercase, alphanumeric, underscores, hyphens) */
  name: string;

  /** Optional description (max 1000 chars) */
  description?: string;

  /** Embedding model identifier (e.g., 'text-embedding-3-small') */
  embedding_model: string;

  /** Embedding provider: 'openai' or 'local' */
  embedding_provider: 'openai' | 'local';

  /** Vector dimensions (must be > 0) */
  embedding_dimensions: number;

  /** Sample size in tokens for preflight analysis (default: 10000) */
  preflight_sample_tokens?: number;

  /** List of chunking strategies to test (default: all available) */
  preflight_strategies?: string[];

  /** Whether auto-chunking is enabled (default: true) */
  auto_chunk_enabled?: boolean;
}

/**
 * Request payload for updating an existing collection.
 * Only description, is_active, and preflight settings can be modified.
 * Embedding model is immutable after creation.
 */
export interface CollectionUpdate {
  /** Updated description */
  description?: string;

  /** Active status */
  is_active?: boolean;

  /** Sample size in tokens for preflight analysis */
  preflight_sample_tokens?: number;

  /** List of chunking strategies to test */
  preflight_strategies?: string[];

  /** Whether auto-chunking is enabled */
  auto_chunk_enabled?: boolean;
}

/**
 * Response containing a list of collections with pagination metadata
 */
export interface CollectionListResponse {
  /** Array of collections */
  collections: Collection[];

  /** Total number of collections matching the query */
  total: number;

  /** Number of items skipped (for pagination) */
  skip?: number;

  /** Maximum items per page */
  limit?: number;
}

/**
 * Collection statistics response
 */
export interface CollectionStats {
  /** Collection ID */
  collection_id: string;

  /** Collection name */
  name: string;

  /** Number of documents */
  document_count: number;

  /** Embedding model */
  embedding_model: string;

  /** Whether collection is active */
  is_active: boolean;
}

/**
 * Available embedding models for collection creation
 */
export const EMBEDDING_MODELS = {
  OPENAI_SMALL: {
    id: 'text-embedding-3-small',
    name: 'OpenAI Text Embedding 3 Small',
    provider: 'openai' as const,
    dimensions: 1536,
    description: 'Cost-effective, good for most use cases',
  },
  OPENAI_LARGE: {
    id: 'text-embedding-3-large',
    name: 'OpenAI Text Embedding 3 Large',
    provider: 'openai' as const,
    dimensions: 3072,
    description: 'Higher accuracy, more expensive',
  },
  LOCAL_MINILM: {
    id: 'all-MiniLM-L6-v2',
    name: 'MiniLM L6 v2',
    provider: 'local' as const,
    dimensions: 384,
    description: 'Fast local model, no API costs',
  },
} as const;

/**
 * Type guard to check if a string is a valid embedding provider
 */
export function isValidProvider(value: string): value is 'openai' | 'local' {
  return value === 'openai' || value === 'local';
}
