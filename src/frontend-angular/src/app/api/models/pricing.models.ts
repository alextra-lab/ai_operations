/**
 * Admin Pricing Models - Per-Model Pricing with History (ADR-046)
 */

export interface ModelPriceCurrentResponse {
  model_id: string;
  currency: string; // "EUR"
  input_price_per_million: number;
  output_price_per_million: number;
  effective_from?: string | null; // ISO timestamp
  effective_to?: string | null; // ISO timestamp
}

export interface ModelPriceChangeRequest {
  input_price_per_million: number;
  output_price_per_million: number;
  effective_from?: string | null; // ISO timestamp or omitted for now
  change_reason?: string | null;
}

export interface ModelPriceHistoryEntry {
  id: string; // UUID
  model_uuid?: string | null;
  model_id?: string | null;
  input_price_per_million: number;
  output_price_per_million: number;
  effective_from: string; // ISO timestamp
  effective_to?: string | null; // ISO timestamp
  changed_by_user_id?: string | null;
  change_reason?: string | null;
  created_at: string; // ISO timestamp
}
