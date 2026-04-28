/**
 * Analytics Data Models
 *
 * TypeScript interfaces for analytics data returned from the backend.
 */

/**
 * Hot Document Analytics Response
 */
export interface HotDocument {
  id: string;
  title: string;
  classification: string;
  ingested_at: string;
  access_count: number;
  last_accessed: string;
  unique_users: number;
}

export interface HotDocumentsResponse {
  documents: HotDocument[];
  total: number;
  limit: number;
  hours: number;
}

/**
 * Usage Statistics Response
 */
export interface DailyTrend {
  date: string;
  queries: number;
  avg_relevancy: number;
}

export interface TopRelevancyDocument {
  document_id: string;
  title: string;
  avg_relevancy_score: number;
  access_count: number;
}

export interface UsageStatsResponse {
  total_retrievals: number;
  unique_documents_accessed: number;
  unique_users: number;
  avg_chunks_per_retrieval: number;
  avg_relevancy_score: number;
  daily_trends: DailyTrend[];
  top_relevancy_documents: TopRelevancyDocument[];
}

/**
 * Security Metrics Response
 */
export interface SecurityMetricsResponse {
  csp_violations_24h: number;
  security_events_24h: number;
  xss_attempts_24h: number;
  security_score: number;
  header_compliance: number;
  last_updated: string;
}

/**
 * Analytics Request Parameters
 */
export interface AnalyticsParams {
  hours?: number;
  limit?: number;
}
