export enum ToolCategory {
  DATABASE = 'database',
  VECTOR_DB = 'vector_db',
  WEB_SCRAPING = 'web_scraping',
  REASONING = 'reasoning',
  DOCUMENTATION = 'documentation',
  CODE_ANALYSIS = 'code_analysis',
  THREAT_INTEL = 'threat_intel',
  CUSTOM = 'custom',
}

export enum ToolStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  DEGRADED = 'degraded',
  UNKNOWN = 'unknown',
}

// =============================================================================
// Security Classification (ADR-057)
// =============================================================================

/**
 * Trust level of data sources the tool accesses.
 */
export enum DataSourceType {
  INTERNAL = 'internal',
  EXTERNAL = 'external',
  NONE = 'none',
  MIXED = 'mixed',
}

/**
 * Direction of data flow relative to the platform.
 */
export enum DataFlowDirection {
  INGRESS = 'ingress',
  EGRESS = 'egress',
  BIDIRECTIONAL = 'bidirectional',
  NONE = 'none',
}

/**
 * Network access requirements for the tool.
 */
export enum NetworkAccessLevel {
  ISOLATED = 'isolated',
  INTERNAL = 'internal',
  EXTERNAL = 'external',
}

/**
 * Maximum data classification the tool can process.
 */
export enum MaxDataSensitivity {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted',
}

export interface ToolListItem {
  id: string;
  tool_id: string;
  name: string;
  description?: string;
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

export interface Tool {
  id: string;
  tool_id: string;
  name: string;
  description?: string;
  category: ToolCategory;
  provider?: string;

  // Configuration (deprecated)
  tool_purpose: string;
  service_location: string;
  mcp_server_type: string;

  // Security Classification (ADR-057)
  data_source_type: DataSourceType;
  data_flow_direction: DataFlowDirection;
  network_access_level: NetworkAccessLevel;
  max_data_sensitivity: MaxDataSensitivity;

  // Capabilities
  capabilities?: Record<string, any>;
  parameters_schema?: Record<string, any>;

  // Limits
  timeout_seconds: number;
  rate_limit_per_minute?: number;

  // Lifecycle
  is_enabled: boolean;
  is_healthy: boolean;
  last_health_check?: string;

  // Metadata
  version?: string;
  documentation_url?: string;
  tags: string[];

  created_at: string;
  updated_at: string;
}
