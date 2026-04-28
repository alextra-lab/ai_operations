/**
 * Metrics Models
 *
 * Models for metrics dashboard including aggregates, recommendations,
 * repeatability testing, and performance analytics.
 *
 * Related: P4-TOOLS-07, ADR-045
 */

import {
  ExecutionMetrics,
  QueryConfig,
} from '../api/models/query-config.models';

// ============================================================================
// Aggregate Metrics
// ============================================================================

export interface AggregateMetrics {
  execution_count: number;

  // Latency metrics
  average_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;

  // Token metrics
  average_tokens: number;
  total_tokens: number;
  average_input_tokens: number;
  average_output_tokens: number;

  // Cost metrics
  total_cost: number;
  average_cost_per_query: number;
  projected_monthly_cost: number;
  currency: string;

  // Consistency metrics
  consistency_score: number; // 0-1, higher = more consistent
  latency_std_dev: number;
  token_std_dev: number;

  // Success metrics
  success_rate: number;
  error_count: number;
}

// ============================================================================
// Parameter Recommendations
// ============================================================================

export type RecommendationType =
  | 'performance'
  | 'consistency'
  | 'cost'
  | 'quality';

export interface ParameterRecommendation {
  type: RecommendationType;
  parameter: string;
  current_value: any;
  recommended_value: any;
  reason: string;
  impact_description: string;
  confidence: number; // 0-1, confidence in recommendation
}

// ============================================================================
// Repeatability Testing
// ============================================================================

export interface RepeatabilityTestConfig {
  query: string;
  iterations: number;
  config: QueryConfig;
}

export interface RepeatabilityMetrics {
  min: number;
  max: number;
  avg: number;
  median: number;
  std_dev: number;
  coefficient_of_variation: number; // std_dev / avg
}

export interface RepeatabilityTestResult {
  test_id: string;
  query: string;
  iterations: number;
  timestamp: string;

  // Latency analysis
  latency: RepeatabilityMetrics;

  // Token analysis
  tokens: RepeatabilityMetrics;

  // Cost analysis
  cost: RepeatabilityMetrics;

  // Overall consistency score (0-1, higher = more consistent)
  consistency_score: number;

  // Individual execution results
  executions: ExecutionMetrics[];

  // Configuration used
  config: QueryConfig;
}

// ============================================================================
// Performance Time Series
// ============================================================================

export interface PerformanceDataPoint {
  timestamp: string;
  latency_ms: number;
  tokens_used: number;
  cost: number;
  success: boolean;
}

export interface PerformanceTimeSeries {
  data_points: PerformanceDataPoint[];
  time_window_minutes: number;
  aggregation_interval_seconds: number;
}

// ============================================================================
// Metrics Export
// ============================================================================

export interface MetricsExport {
  export_timestamp: string;
  time_range: {
    start: string;
    end: string;
  };
  aggregate_metrics: AggregateMetrics;
  recommendations: ParameterRecommendation[];
  performance_data: PerformanceDataPoint[];
  config: QueryConfig;
}

// ============================================================================
// Statistical Helpers
// ============================================================================

/**
 * Calculate mean of an array of numbers
 */
export function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/**
 * Calculate median of an array of numbers
 */
export function median(values: number[]): number {
  if (values.length === 0) return 0;

  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

/**
 * Calculate standard deviation
 */
export function standardDeviation(values: number[]): number {
  if (values.length < 2) return 0;

  const avg = mean(values);
  const squaredDiffs = values.map((v) => Math.pow(v - avg, 2));
  const variance = mean(squaredDiffs);

  return Math.sqrt(variance);
}

/**
 * Calculate percentile
 */
export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;

  const sorted = [...values].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (lower === upper) {
    return sorted[lower];
  }

  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

/**
 * Calculate min value
 */
export function min(values: number[]): number {
  if (values.length === 0) return 0;
  return Math.min(...values);
}

/**
 * Calculate max value
 */
export function max(values: number[]): number {
  if (values.length === 0) return 0;
  return Math.max(...values);
}
