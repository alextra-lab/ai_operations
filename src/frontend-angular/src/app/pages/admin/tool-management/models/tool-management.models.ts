/**
 * Tool Management Models
 *
 * TypeScript models for Tools Track admin management.
 */

/**
 * Tool category enum
 */
export type ToolCategory =
  | 'database'
  | 'vector_db'
  | 'web_scraping'
  | 'reasoning'
  | 'documentation'
  | 'code_analysis'
  | 'threat_intel'
  | 'custom';

/**
 * Tool status enum
 */
export type ToolStatus = 'online' | 'offline' | 'degraded' | 'unknown';

/**
 * MCP server type enum
 */
export type MCPServerType = 'stdio' | 'sse' | 'http';

// =============================================================================
// Security Classification (ADR-057)
// =============================================================================

/**
 * Trust level of data sources the tool accesses.
 */
export type DataSourceType = 'internal' | 'external' | 'none' | 'mixed';

/**
 * Direction of data flow relative to the platform.
 */
export type DataFlowDirection = 'ingress' | 'egress' | 'bidirectional' | 'none';

/**
 * Network access requirements for the tool.
 */
export type NetworkAccessLevel = 'isolated' | 'internal' | 'external';

/**
 * Maximum data classification the tool can process.
 */
export type MaxDataSensitivity =
  | 'public'
  | 'internal'
  | 'confidential'
  | 'restricted';

/**
 * Tool list item interface (minimal for table display)
 */
export interface ToolListItem {
  id: string;
  tool_id: string;
  name: string;
  description: string | null;
  category: ToolCategory;
  is_enabled: boolean;
  is_healthy: boolean;
  requires_authentication: boolean;
  // Security Classification (ADR-057)
  data_source_type?: DataSourceType;
  data_flow_direction?: DataFlowDirection;
  network_access_level?: NetworkAccessLevel;
  max_data_sensitivity?: MaxDataSensitivity;
}

/**
 * Complete tool interface (for details/edit)
 */
export interface Tool {
  id: string;
  tool_id: string;
  name: string;
  description: string | null;
  category: ToolCategory;
  provider: string | null;
  // Deprecated: Legacy classification (ADR-001)
  tool_purpose: 'retrieval' | 'orchestrator';
  service_location: 'retrieval_service' | 'orchestrator';
  // Security Classification (ADR-057)
  data_source_type: DataSourceType;
  data_flow_direction: DataFlowDirection;
  network_access_level: NetworkAccessLevel;
  max_data_sensitivity: MaxDataSensitivity;
  // MCP Configuration
  mcp_server_type: MCPServerType;
  mcp_command: string[] | null;
  mcp_endpoint: string | null;
  mcp_protocol_version: string;
  capabilities: Record<string, any> | null;
  parameters_schema: Record<string, any> | null;
  requires_authentication: boolean;
  authentication_type: string | null;
  secret_name: string | null;
  config_options: Record<string, any> | null;
  timeout_seconds: number;
  rate_limit_per_minute: number | null;
  max_concurrent_calls: number;
  is_enabled: boolean;
  health_check_interval_seconds: number;
  version: string | null;
  documentation_url: string | null;
  tags: string[];
  is_healthy: boolean;
  last_health_check: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

/**
 * Tool filters for list queries
 */
export interface ToolFilters {
  category?: ToolCategory;
  enabled_only?: boolean;
  healthy_only?: boolean;
  search?: string;
}

/**
 * Tool update request (partial)
 */
export interface ToolUpdateRequest {
  name?: string;
  description?: string | null;
  is_enabled?: boolean;
  timeout_seconds?: number;
  rate_limit_per_minute?: number | null;
  config_options?: Record<string, any> | null;
  tags?: string[];
}

/**
 * Health check result
 */
export interface ToolHealthCheckResult {
  tool_id: string;
  status: ToolStatus;
  response_time_ms: number | null;
  error_message: string | null;
  checked_at: string;
}
