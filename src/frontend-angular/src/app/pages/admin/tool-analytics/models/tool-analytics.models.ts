/**
 * Tool Analytics Models
 *
 * Type definitions for T6-F3 Tool Analytics Dashboard.
 * Maps to backend API responses from tools_analytics.py endpoints.
 */

/**
 * Usage summary for a single tool
 * Response from GET /api/v1/tools/analytics/usage/summary
 */
export interface ToolUsageSummary {
  tool_id: string;
  tool_name?: string;
  total_calls: number;
  successful_calls: number;
  success_rate: number;
  avg_duration_ms: number;
  total_cost: number;
}

/**
 * Usage aggregated by center
 * Response from GET /api/v1/tools/analytics/usage/by-center
 */
export interface CenterUsage {
  center_id: string;
  total_calls: number;
  total_cost: number;
}

/**
 * Aggregated analytics for all tools
 */
export interface AggregateAnalytics {
  total_invocations: number;
  total_successful: number;
  average_success_rate: number;
  total_cost: number;
  average_duration_ms: number;
  most_used_tool: string | null;
  most_used_tool_calls: number;
}

/**
 * Date range preset options
 */
export enum DateRangePreset {
  TODAY = 'today',
  WEEK = 'week',
  MONTH = 'month',
  QUARTER = 'quarter',
  CUSTOM = 'custom',
}

/**
 * Date range for filtering analytics
 */
export interface DateRange {
  start: Date;
  end: Date;
  preset: DateRangePreset;
}

/**
 * Time range option for dropdown
 */
export interface TimeRangeOption {
  value: DateRangePreset;
  label: string;
  days: number;
}

/**
 * Predefined time range options
 */
export const TIME_RANGE_OPTIONS: TimeRangeOption[] = [
  { value: DateRangePreset.TODAY, label: 'Last 24 hours', days: 1 },
  { value: DateRangePreset.WEEK, label: 'Last 7 days', days: 7 },
  { value: DateRangePreset.MONTH, label: 'Last 30 days', days: 30 },
  { value: DateRangePreset.QUARTER, label: 'Last 90 days', days: 90 },
];

/**
 * Analytics filters for API requests
 */
export interface AnalyticsFilters {
  startDate?: Date;
  endDate?: Date;
  days?: number;
  toolId?: string;
}

/**
 * Export format options
 */
export type ExportFormat = 'csv' | 'json';

/**
 * Chart data point for center usage
 */
export interface CenterChartData {
  label: string;
  calls: number;
  cost: number;
}

/**
 * Calculate aggregate analytics from usage summary
 */
export function calculateAggregates(
  summaries: ToolUsageSummary[]
): AggregateAnalytics {
  if (summaries.length === 0) {
    return {
      total_invocations: 0,
      total_successful: 0,
      average_success_rate: 0,
      total_cost: 0,
      average_duration_ms: 0,
      most_used_tool: null,
      most_used_tool_calls: 0,
    };
  }

  const totalInvocations = summaries.reduce((sum, s) => sum + s.total_calls, 0);
  const totalSuccessful = summaries.reduce(
    (sum, s) => sum + s.successful_calls,
    0
  );
  const totalCost = summaries.reduce((sum, s) => sum + s.total_cost, 0);

  // Weighted average for duration
  const totalDuration = summaries.reduce(
    (sum, s) => sum + s.avg_duration_ms * s.total_calls,
    0
  );
  const avgDuration =
    totalInvocations > 0 ? totalDuration / totalInvocations : 0;

  // Weighted average for success rate
  const avgSuccessRate =
    totalInvocations > 0 ? (totalSuccessful / totalInvocations) * 100 : 0;

  // Find most used tool
  let mostUsedTool: string | null = null;
  let mostUsedCalls = 0;
  summaries.forEach((s) => {
    if (s.total_calls > mostUsedCalls) {
      mostUsedCalls = s.total_calls;
      mostUsedTool = s.tool_name || s.tool_id;
    }
  });

  return {
    total_invocations: totalInvocations,
    total_successful: totalSuccessful,
    average_success_rate: avgSuccessRate,
    total_cost: totalCost,
    average_duration_ms: avgDuration,
    most_used_tool: mostUsedTool,
    most_used_tool_calls: mostUsedCalls,
  };
}

/**
 * Get success rate color class
 */
export function getSuccessRateClass(rate: number): string {
  if (rate >= 95) {
    return 'success-high';
  }
  if (rate >= 90) {
    return 'success-medium';
  }
  return 'success-low';
}

/**
 * Format cost value for display
 */
export function formatCost(cost: number): string {
  return `€${cost.toFixed(4)}`;
}

/**
 * Format duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}
