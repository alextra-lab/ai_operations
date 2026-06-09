/**
 * System Configuration Models
 *
 * TypeScript models for system configuration management.
 * Mirrors backend Pydantic schemas.
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export type ConfigSection = 'corpus' | 'auth' | 'features' | 'system';

export interface PasswordPolicy {
  min_length: number;
  require_uppercase: boolean;
  require_lowercase: boolean;
  require_numbers: boolean;
  require_special: boolean;
}

export interface CorpusConfig {
  chunk_size: number;
  chunk_overlap: number;
  default_embedding_model: string;
  max_document_size_mb: number;
  allowed_file_types: string[];
}

export interface AuthConfig {
  session_timeout_minutes: number;
  refresh_token_ttl_days: number;
  password_policy: PasswordPolicy;
}

export interface FeatureFlags {
  multi_collection_search: boolean;
  export_functionality: boolean;
  conversation_cache: boolean;
  telemetry_enabled: boolean;
}

export interface SystemConfig {
  log_level: LogLevel;
  max_workers: number;
  request_timeout_seconds: number;
  enable_debug_endpoints: boolean;
}

export interface SystemConfigFull {
  corpus: CorpusConfig;
  auth: AuthConfig;
  features: FeatureFlags;
  system: SystemConfig;
}

export interface ConfigSectionResponse {
  section: ConfigSection;
  config: Record<string, unknown>;
  updated_at: string;
  updated_by?: string;
  restart_required: boolean;
}

export interface ConfigExportResponse {
  config_yaml: string;
  exported_at: string;
}

export interface ConfigImportRequest {
  config_yaml: string;
  validate_only: boolean;
}

export interface ConfigImportResponse {
  success: boolean;
  sections_updated: string[];
  restart_required: boolean;
  validation_errors?: string[];
}

export interface ConfigSchema {
  type: string;
  properties: Record<string, SchemaProperty>;
  required?: string[];
  $defs?: Record<string, SchemaProperty>;
}

export interface SchemaProperty {
  type: string;
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  enum?: unknown[];
  items?: SchemaProperty;
  properties?: Record<string, SchemaProperty>;
  $ref?: string;
}

export interface ConfigSectionMetadata {
  section: ConfigSection;
  title: string;
  description: string;
  icon: string;
  restart_required: boolean;
}

export const CONFIG_SECTIONS: ConfigSectionMetadata[] = [
  {
    section: 'corpus',
    title: 'Corpus Settings',
    description: 'Document chunking and embedding configuration',
    icon: 'database',
    restart_required: true,
  },
  {
    section: 'auth',
    title: 'Authentication Settings',
    description: 'Session timeout and password policy',
    icon: 'shield',
    restart_required: false,
  },
  {
    section: 'features',
    title: 'Feature Flags',
    description: 'Enable or disable system features',
    icon: 'toggle-right',
    restart_required: false,
  },
  {
    section: 'system',
    title: 'System Settings',
    description: 'Log level, workers, and performance settings',
    icon: 'settings',
    restart_required: true,
  },
];
