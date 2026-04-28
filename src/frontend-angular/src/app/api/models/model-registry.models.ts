/**
 * Model Registry Interface - Data Models
 *
 * TypeScript interfaces for the Model Registry API responses and requests.
 */

export interface Model {
  id: string;
  model_id: string;
  name: string;
  provider_type: string;
  provider: string | null;
  model_type: string;
  description?: string;
  context_window?: number;
  max_input_tokens?: number;
  max_output_tokens?: number;
  embedding_dimensions?: number;
  supports_tools: boolean;
  supports_vision: boolean;
  supports_audio: boolean;
  is_reasoning_model: boolean;
  reasoning_config: Record<string, any>;
  typical_latency_ms?: number;
  tokens_per_second?: number;
  input_price_per_million?: number;
  output_price_per_million?: number;
  specialization?: string;
  version?: string;
  release_date?: string;
  deprecated: boolean;
  deprecation_date?: string;
  default_temperature: number;
  temperature_range: TemperatureRange;
  recommended_use_cases?: string[];
  is_available: boolean;
  is_hidden: boolean;
  health_status: string;
  created_at: string;
  updated_at: string;
  metadata_json: Record<string, any>;
}

export interface ModelCapabilities {
  supports_tools: boolean;
  supports_vision: boolean;
  supports_audio: boolean;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  supports_json_mode: boolean;
}

export interface ModelPricing {
  input_price_per_million?: number;
  output_price_per_million?: number;
  currency: string;
}

export interface ModelPerformance {
  typical_latency_ms?: number;
  tokens_per_second?: number;
  context_window?: number;
  max_input_tokens?: number;
  max_output_tokens?: number;
}

export interface TemperatureRange {
  min: number;
  max: number;
}

export interface ModelDetailedResponse extends Model {
  capabilities: ModelCapabilities;
  pricing?: ModelPricing;
  performance: ModelPerformance;
  estimated_cost_per_1k_tokens?: number;
}

export interface ModelListResponse {
  models: Model[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ModelRecommendation {
  model_id: string;
  name: string;
  confidence: number;
  reasoning: string;
  estimated_cost?: number;
  estimated_latency_ms?: number;
  capabilities_match: number;
}

export interface ModelSelectionRequest {
  use_case_type: string;
  requirements?: Record<string, any>;
  constraints?: Record<string, any>;
  prefer_capabilities?: string[];
}
