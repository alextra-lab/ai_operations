/**
 * Gateway Metrics Models
 *
 * TypeScript models for Inference Gateway metrics data.
 */

export interface GatewayMetrics {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_eur: number;
  avg_latency_ms: number;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  p99_latency_ms: number | null;
  unique_models: number;
  unique_users: number;
  streaming_requests: number;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
  label?: string | null;
}

export interface TimeSeriesData {
  latency: TimeSeriesPoint[];
  tokens: TimeSeriesPoint[];
  cost: TimeSeriesPoint[];
  requests: TimeSeriesPoint[];
}

export interface ProviderMetrics {
  provider_name: string;
  request_count: number;
  success_rate: number;
  avg_latency_ms: number;
  total_cost_eur: number;
  total_tokens: number;
}

export interface ModelMetrics {
  model_name: string;
  request_count: number;
  total_tokens: number;
  total_cost_eur: number;
  avg_latency_ms: number;
}

export interface MetricsFilters {
  hours: number;
  provider?: string;
}

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';

export const TIME_RANGE_OPTIONS = [
  { value: '1h', label: 'Last Hour', hours: 1 },
  { value: '6h', label: 'Last 6 Hours', hours: 6 },
  { value: '24h', label: 'Last 24 Hours', hours: 24 },
  { value: '7d', label: 'Last 7 Days', hours: 168 },
  { value: '30d', label: 'Last 30 Days', hours: 720 },
];
