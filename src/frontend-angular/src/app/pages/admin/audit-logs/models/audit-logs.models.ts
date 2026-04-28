/**
 * TypeScript models for audit log operations.
 *
 * These models match the backend Pydantic schemas for audit log queries.
 */

export interface AuditLogEntry {
  id: string;
  event_time: string;
  actor_user_id: string | null;
  actor_username: string | null;
  actor_roles: string[];
  action: string;
  resource_type: string;
  resource_id: string | null;
  use_case_id: string | null;
  use_case_name: string | null;
  request_id: string | null;
  client_ip: string | null;
  user_agent: string | null;
  success: boolean;
  details: Record<string, any>;
  created_at: string;
}

export interface AuditLogListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  logs: AuditLogEntry[];
}

export interface AuditLogStatsResponse {
  total_events: number;
  success_count: number;
  failure_count: number;
  unique_users: number;
  unique_resource_types: number;
  date_range_start: string | null;
  date_range_end: string | null;
  top_actions: { action: string; count: number }[];
  top_resource_types: { resource_type: string; count: number }[];
}

export interface AuditLogFilters {
  page?: number;
  page_size?: number;
  start_date?: string;
  end_date?: string;
  actor_user_id?: string;
  action?: string;
  resource_type?: string;
  use_case_id?: string;
  success?: boolean;
  search?: string;
}

export interface AuditLogDateRange {
  start: Date;
  end: Date;
}
