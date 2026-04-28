/**
 * TypeScript models for token usage analytics
 * Based on backend schemas in src/backend/app/schemas/token_usage.py
 */

export interface TokenUsageSummary {
  center_id?: string;
  user_id?: string;
  total_requests: number;
  unique_users?: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_tokens: number;
  total_cost?: number;
  avg_tokens_per_request?: number;
  top_models?: Record<string, number>;
}

export interface DailyUsagePoint {
  date: string;
  total_tokens: number;
  total_requests: number;
  total_cost?: number;
}

export interface CenterUsageSummaryResponse {
  center_id: string;
  start_date: string;
  end_date: string;
  summary: TokenUsageSummary;
}

export interface AllCentersUsageSummaryResponse {
  start_date: string;
  end_date: string;
  centers: TokenUsageSummary[];
  grand_total: TokenUsageSummary;
}

export interface UserUsageResponse {
  user_id: string;
  center_id?: string;
  summary: TokenUsageSummary;
  daily_usage: DailyUsagePoint[];
}

export interface ModelUsageResponse {
  model_id: string;
  model_provider?: string;
  summary: TokenUsageSummary;
}

// Chart data interfaces for visualization
export interface TokenUsageChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string;
    borderColor?: string;
    fill?: boolean;
  }[];
}

export interface CostChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string;
    borderColor?: string;
  }[];
}

// Filter options for the dashboard
export interface TokenUsageFilters {
  startDate?: string;
  endDate?: string;
  centerId?: string;
  userId?: string;
  modelId?: string;
}
