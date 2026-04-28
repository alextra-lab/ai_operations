/**
 * Platform Configuration Models
 *
 * TypeScript interfaces for dynamic categories and intent types
 * loaded from /api/v1/config endpoints.
 *
 * ADR-067: Dynamic Categories, Intent Capability Profiles,
 * and Auto-Presets.
 */

// ============================================================
// Category Configuration
// ============================================================

/** A category loaded from the backend. */
export interface CategoryConfig {
  category_code: string;
  display_name: string;
  description: string;
  icon: string;
  color: string;
  sort_order: number;
}

/** API response wrapper for categories list. */
export interface CategoriesListResponse {
  categories: CategoryConfig[];
  total: number;
}

// ============================================================
// Intent Type Configuration (with Capability Profile)
// ============================================================

/** Sampling preset values. */
export type SamplingPreset =
  | 'strict'
  | 'balanced'
  | 'creative';

/** Output format values. */
export type OutputFormat =
  | 'text'
  | 'json'
  | 'yaml'
  | 'structured';

/**
 * An intent type with its capability profile,
 * loaded from the backend.
 *
 * The capability profile drives auto-presets in
 * the wizard (ADR-067): when the user selects an
 * intent type, the wizard auto-sets
 * `sampling_preset` and `output_format` to these
 * defaults (overridable).
 */
export interface IntentTypeConfig {
  intent_code: string;
  display_name: string;
  description: string;
  category_code: string;
  icon: string;
  color: string;
  is_system: boolean;
  default_sampling_preset: SamplingPreset;
  default_output_format: OutputFormat;
  recommended_capabilities: string[];
  sort_order: number;
}

/** API response wrapper for intent types list. */
export interface IntentTypesListResponse {
  intent_types: IntentTypeConfig[];
  total: number;
}
