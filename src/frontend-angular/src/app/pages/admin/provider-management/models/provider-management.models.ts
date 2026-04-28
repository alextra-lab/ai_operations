/**
 * Provider Management Models
 *
 * TypeScript models for Inference Gateway provider management.
 */

/**
 * Provider type enum
 */
export type ProviderType =
  | 'openai'
  | 'mistral'
  | 'anthropic'
  | 'local'
  | 'custom';

/**
 * Provider status enum
 */
export type ProviderStatus = 'active' | 'disabled' | 'error' | 'testing';

/**
 * Circuit breaker state
 */
export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

/**
 * Provider configuration interface
 */
export interface ProviderConfig {
  id?: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  api_key?: string;
  is_enabled: boolean;
  status: ProviderStatus;
  priority: number;
  config_json?: Record<string, any>;
  health_check_url?: string;
  last_health_check?: string;
  last_health_status?: boolean;
  error_count?: number;
  success_count?: number;
  circuit_state?: CircuitState;
  created_at?: string;
  updated_at?: string;
}

/**
 * Provider list response with pagination
 */
export interface ProviderListResponse {
  items: ProviderConfig[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Provider filters for list queries
 */
export interface ProviderFilters {
  limit?: number;
  offset?: number;
  enabled_only?: boolean;
}

/**
 * Provider test result
 */
export interface ProviderTestResult {
  success: boolean;
  status_code?: number;
  latency_ms?: number;
  message: string;
}

/**
 * Create provider request (subset of ProviderConfig)
 */
export interface CreateProviderRequest {
  name: string;
  provider_type: ProviderType;
  base_url: string;
  api_key?: string;
  is_enabled?: boolean;
  status?: ProviderStatus;
  priority?: number;
  config_json?: Record<string, any>;
  health_check_url?: string;
}

/**
 * Update provider request (partial)
 */
export interface UpdateProviderRequest {
  name?: string;
  provider_type?: ProviderType;
  base_url?: string;
  api_key?: string;
  is_enabled?: boolean;
  status?: ProviderStatus;
  priority?: number;
  config_json?: Record<string, any>;
  health_check_url?: string;
}
