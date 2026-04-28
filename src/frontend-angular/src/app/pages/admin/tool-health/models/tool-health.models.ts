/**
 * Tool Health Dashboard Models
 *
 * TypeScript models for T6-F2 Tool Health Monitoring Dashboard.
 */

/**
 * Overall health summary from /api/v1/tools/health/status
 */
export interface HealthSummary {
  total_tools: number;
  online: number;
  offline: number;
  health_percentage: number;
  last_check: string | null;
}

/**
 * Individual health check record from history API
 */
export interface ToolHealthCheckRecord {
  id: string;
  tool_id: string;
  status: 'online' | 'offline' | 'degraded' | 'unknown';
  response_time_ms: number | null;
  error_message: string | null;
  checked_at: string;
  mcp_server_info?: Record<string, unknown> | null;
}

/**
 * Tool item for health table display
 * Extended from ToolListItem with health-specific fields
 */
export interface ToolHealthListItem {
  id: string;
  tool_id: string;
  name: string;
  description: string | null;
  is_enabled: boolean;
  is_healthy: boolean;
  last_health_check: string | null;
  response_time_ms?: number | null;
}

/**
 * Time range options for health history
 */
export interface TimeRangeOption {
  value: number;
  label: string;
}

/**
 * Health status for display (computed)
 */
export type HealthDisplayStatus = 'online' | 'offline' | 'disabled' | 'unknown';

/**
 * Get display status from tool data
 */
export function getHealthDisplayStatus(
  isEnabled: boolean,
  isHealthy: boolean,
  lastCheck: string | null
): HealthDisplayStatus {
  if (!isEnabled) {
    return 'disabled';
  }
  if (lastCheck === null) {
    return 'unknown';
  }
  return isHealthy ? 'online' : 'offline';
}
