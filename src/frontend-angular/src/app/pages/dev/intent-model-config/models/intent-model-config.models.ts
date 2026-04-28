/**
 * Intent Model Configuration Models
 *
 * TypeScript models for intent-to-model configuration management (ADR-069).
 */

/**
 * Available model from registry
 */
export interface AvailableModel {
  model_id: string;
  provider: string;
  context_window: number | null;
  capabilities: string[];
  is_active: boolean;
}

/**
 * Intent model default configuration
 */
export interface IntentModelDefault {
  id: string;
  intent_code: string;
  model_id: string;
  priority: number;
  is_active: boolean;
  effective_date: string;
  notes: string | null;
  created_at: string;
  created_by: string | null;
  updated_at: string;
  updated_by: string | null;
}

/**
 * Intent model default with model details
 */
export interface IntentModelDefaultWithModel extends IntentModelDefault {
  model_provider: string | null;
  model_context_window: number | null;
  model_capabilities: string[];
}

/**
 * Summary of intent with current model configuration
 */
export interface IntentModelSummary {
  intent_code: string;
  display_name: string;
  description: string;
  current_model_id: string | null;
  current_temperature: number | null;
  has_default: boolean;
  icon: string | null;
  color: string | null;
}

/**
 * Request to update intent model default
 */
export interface UpdateIntentModelRequest {
  model_id: string;
  temperature?: number | null;
  notes?: string | null;
  effective_date?: string | null;
}

/**
 * Historical intent model configuration entry
 */
export interface IntentModelHistoryEntry {
  id: string;
  intent_code: string;
  model_id: string;
  is_active: boolean;
  effective_date: string;
  notes: string | null;
  created_at: string;
  created_by_username: string | null;
}

/**
 * UI state for intent configuration row
 */
export interface IntentConfigRow extends IntentModelSummary {
  isEditing: boolean;
  selectedModel: string | null;
  selectedTemperature: number | null;
  notes: string | null;
}
