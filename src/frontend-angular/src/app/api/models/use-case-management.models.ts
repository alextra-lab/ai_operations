/**
 * Use Case Management Models for AI Operations Platform
 *
 * TypeScript interfaces matching the backend Pydantic schemas for
 * Use Case CRUD operations, lifecycle management, and version control.
 *
 * Reference: USE_CASE_MANAGEMENT_PLAN.md
 * Architecture: ADR-018 Use Case Owned Architecture
 */

// ============================================================================
// Use Case Base Models
// ============================================================================

export interface UseCaseBase {
  use_case_id: string;
  name: string;
  description?: string | null;
  category?: string | null;
  intent_type: string;
}

export interface UseCaseCreate extends UseCaseBase {
  version?: number;
  lifecycle_state?: string;
  is_active?: boolean;
  config_json?: Record<string, any>;
  metadata_json?: Record<string, any>;
  prompts?: UseCasePromptSet;
  team_id?: string | null;
}

export interface UseCaseUpdate {
  name?: string;
  description?: string | null;
  category?: string | null;
  config_json?: Record<string, any>;
  metadata_json?: Record<string, any>;
  prompts?: UseCasePromptSet;
}

export interface UseCaseResponse extends UseCaseBase {
  id: string;
  version: number;
  lifecycle_state: string;
  is_active: boolean;
  config_json: Record<string, any>;
  metadata_json: Record<string, any>;
  prompts?: UseCasePromptSet | null;
  created_at: string;
  updated_at: string;
  team_id?: string | null;
  created_by_user_id?: string | null;
  approved_by_user_id?: string | null;
  published_by_user_id?: string | null;
  approved_at?: string | null;
  published_at?: string | null;
}

export interface UseCaseListResponse {
  use_cases: UseCaseResponse[];
  total_count?: number;
  total?: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

// ============================================================================
// Prompt Models (Multi-role)
// ============================================================================

export interface FewshotPair {
  user: string;
  assistant: string;
}

export interface UseCasePromptSet {
  system_prompt?: string | null;
  developer_prompt?: string | null;
  fewshots?: FewshotPair[];
  variables?: string[];
}

// ============================================================================
// Lifecycle & Version Control Models
// ============================================================================

export interface StateTransitionRequest {
  to_state: string;
  approval_notes?: string;
}

export interface VersionHistoryEntry {
  version: number;
  config_snapshot: Record<string, any>;
  prompts_snapshot?: UseCasePromptSet;
  updated_at: string;
  updated_by: string;
  change_notes?: string;
}

export interface VersionHistoryResponse {
  use_case_id: string;
  versions: VersionHistoryEntry[];
  total_versions: number;
}

export interface RollbackRequest {
  to_version: number;
}

export interface CloneRequest {
  new_use_case_id: string;
  new_name?: string;
}

// ============================================================================
// Filter & Search Models
// ============================================================================

export interface UseCaseListFilters {
  category?: string;
  lifecycle_state?: string;
  is_active?: boolean;
  intent_type?: string;
  search_query?: string;
  use_case_id_filter?: string;
  active_only?: boolean;
  page?: number;
  page_size?: number;
}

// ============================================================================
// Configuration Models (UseCaseConfig)
// ============================================================================

export interface UseCaseConfig {
  models: ModelConfig;
  rag?: RAGConfig;
  generation_params: GenerationParams;
  output_contract: OutputContract;
  policy: PolicyConfig;
  tools_allowlist?: string[];
  tool_restrictions?: ToolRestrictions | null; // ADR-057
  visibility?: VisibilityConfig;
  telemetry?: TelemetryConfig;
}

// =============================================================================
// Tool Restrictions (ADR-057)
// =============================================================================

export type DataSourceType = 'internal' | 'external' | 'none' | 'mixed';
export type DataFlowDirection = 'ingress' | 'egress' | 'bidirectional' | 'none';
export type NetworkAccessLevel = 'isolated' | 'internal' | 'external';
export type MaxDataSensitivity =
  | 'public'
  | 'internal'
  | 'confidential'
  | 'restricted';

export interface ToolRestrictions {
  allowed_data_sources: DataSourceType[];
  allowed_data_flows: DataFlowDirection[];
  allowed_network_levels: NetworkAccessLevel[];
  required_data_sensitivity: MaxDataSensitivity;
  explicit_tool_allowlist?: string[];
  explicit_tool_blocklist?: string[];
}

export type ToolRestrictionPreset =
  | 'high_security'
  | 'internal_only'
  | 'research_open'
  | 'no_egress'
  | 'custom';

export const TOOL_RESTRICTION_PRESETS: Record<
  Exclude<ToolRestrictionPreset, 'custom'>,
  { label: string; description: string; restrictions: ToolRestrictions }
> = {
  high_security: {
    label: 'High Security (PII)',
    description: 'Only internal sources, no internet, restricted data allowed',
    restrictions: {
      allowed_data_sources: ['internal', 'none'],
      allowed_data_flows: ['ingress', 'none'],
      allowed_network_levels: ['isolated', 'internal'],
      required_data_sensitivity: 'restricted',
    },
  },
  internal_only: {
    label: 'Internal Only',
    description: 'Internal sources only, internal network access',
    restrictions: {
      allowed_data_sources: ['internal', 'none'],
      allowed_data_flows: ['ingress', 'none'],
      allowed_network_levels: ['isolated', 'internal'],
      required_data_sensitivity: 'internal',
    },
  },
  research_open: {
    label: 'Research (Open)',
    description: 'All sources allowed, external access, public data only',
    restrictions: {
      allowed_data_sources: ['internal', 'external', 'none', 'mixed'],
      allowed_data_flows: ['ingress', 'bidirectional', 'none'],
      allowed_network_levels: ['isolated', 'internal', 'external'],
      required_data_sensitivity: 'public',
    },
  },
  no_egress: {
    label: 'No Data Egress',
    description: 'All sources allowed, but no data can leave the system',
    restrictions: {
      allowed_data_sources: ['internal', 'external', 'none', 'mixed'],
      allowed_data_flows: ['ingress', 'none'],
      allowed_network_levels: ['isolated', 'internal', 'external'],
      required_data_sensitivity: 'internal',
    },
  },
};

export interface ModelConfig {
  llm: string;
  // NOTE: Embedding model removed - system-wide configuration
}

export interface RAGConfig {
  enabled: boolean;
  top_k: number;
  similarity_threshold: number;
  vector_collections: string[];
  metadata_filters?: Record<string, any>;
  tags?: string[];
  hybrid_bm25?: boolean;
}

export interface GenerationParams {
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface OutputContract {
  format: string; // 'text', 'json', 'markdown'
  output_schema?: Record<string, any> | null;
  validation_mode: string; // 'strict', 'best_effort'
}

export interface PolicyConfig {
  streaming_enabled: boolean;
  streaming_default: boolean;
  history_persistence: boolean;
  pii_redaction?: string; // 'none', 'anonymize', 'remove'
}

export interface VisibilityConfig {
  roles?: string[];
  tags?: string[];
}

export interface TelemetryConfig {
  required_metrics?: string[];
}

// ============================================================================
// Enums & Constants
// ============================================================================

export enum LifecycleState {
  DRAFT = 'draft',
  REVIEW = 'review',
  PUBLISHED = 'published',
  ARCHIVED = 'archived',
}

/**
 * @deprecated ADR-067 — Intent types are now loaded
 * dynamically from the backend via PlatformConfigService.
 * Kept for backward compatibility only.
 * Use `PlatformConfigService.intentTypes$` instead.
 */
export enum IntentType {
  QUERY = 'QUERY',
  RULE_GENERATION = 'RULE_GENERATION',
  SUMMARIZATION = 'SUMMARIZATION',
  ENRICHMENT = 'ENRICHMENT',
}

/**
 * @deprecated ADR-067 — Categories are now loaded
 * dynamically from the backend via PlatformConfigService.
 * Kept for backward compatibility only.
 * Use `PlatformConfigService.categories$` instead.
 */
export const UseCaseCategories = [
  'security',
  'compliance',
  'threat-intel',
  'incident-response',
  'siem-analysis',
  'risk-assessment',
  'test',
] as const;

/** @deprecated Use CategoryConfig from platform-config.models. */
export type UseCaseCategory = (typeof UseCaseCategories)[number];

// ============================================================================
// UI Helper Types
// ============================================================================

export interface UseCaseWithActions extends UseCaseResponse {
  canEdit: boolean;
  canDelete: boolean;
  canClone: boolean;
  canTransition: boolean;
  canExecute: boolean;
}
