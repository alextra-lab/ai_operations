/**
 * Dashboard models and interfaces for P2-F1: Real-time Dashboard System
 */

export interface DashboardWidget {
  id: string;
  type: WidgetType;
  title: string;
  position: WidgetPosition;
  size: WidgetSize;
  data: any;
  config: WidgetConfig;
  isVisible: boolean;
  isCollapsed: boolean;
  lastUpdated: Date;
}

export enum WidgetType {
  THREAT_FEED = 'threat_feed',
  SYSTEM_HEALTH = 'system_health',
  QUERY_STATS = 'query_stats',
  USER_ACTIVITY = 'user_activity',
  SECURITY_ALERTS = 'security_alerts',
  PERFORMANCE_METRICS = 'performance_metrics',
  DOCUMENT_PROCESSING = 'document_processing',
  CUSTOM_CHART = 'custom_chart',
}

export interface WidgetPosition {
  x: number;
  y: number;
  z: number;
}

export interface WidgetSize {
  width: number;
  height: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
}

export interface WidgetConfig {
  refreshInterval?: number;
  autoRefresh: boolean;
  showHeader: boolean;
  showControls: boolean;
  theme?: 'light' | 'dark' | 'auto';
  customSettings?: Record<string, any>;
}

export interface DashboardLayout {
  id: string;
  name: string;
  description?: string;
  widgets: DashboardWidget[];
  gridConfig: GridConfig;
  isDefault: boolean;
  isPublic: boolean;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface GridConfig {
  columns: number;
  rows: number;
  cellSize: number;
  gap: number;
  autoFit: boolean;
}

export interface RealTimeData {
  threat_events: ThreatEvent[];
  system_health: SystemHealth;
  query_stats: QueryStats;
  user_activity: UserActivity[];
  security_alerts: SecurityAlert[];
  performance_metrics: PerformanceMetrics;
  document_processing: DocumentProcessingStats;
  timestamp: Date;
}

export interface ThreatEvent {
  id: string;
  title: string;
  description: string;
  severity: ThreatSeverity;
  source: string;
  timestamp: Date;
  category: string;
  tags: string[];
  status: ThreatStatus;
  assignedTo?: string;
  resolution?: string;
}

export enum ThreatSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum ThreatStatus {
  NEW = 'new',
  INVESTIGATING = 'investigating',
  RESOLVED = 'resolved',
  FALSE_POSITIVE = 'false_positive',
  ESCALATED = 'escalated',
}

export interface SystemHealth {
  status: SystemStatus;
  uptime: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_status: NetworkStatus;
  services: ServiceStatus[];
  last_check: Date;
}

export enum SystemStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  CRITICAL = 'critical',
  OFFLINE = 'offline',
}

export interface NetworkStatus {
  latency: number;
  bandwidth: number;
  packet_loss: number;
  status: 'up' | 'down' | 'degraded';
}

export interface ServiceStatus {
  name: string;
  status: SystemStatus;
  uptime: number;
  last_check: Date;
  error_message?: string;
}

export interface QueryStats {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  average_response_time: number;
  queries_per_hour: number;
  top_queries: TopQuery[];
  recent_queries: RecentQuery[];
}

export interface TopQuery {
  query: string;
  count: number;
  avg_response_time: number;
  success_rate: number;
}

export interface RecentQuery {
  id: string;
  query: string;
  user: string;
  timestamp: Date;
  status: 'success' | 'failed' | 'processing';
  response_time?: number;
}

export interface UserActivity {
  user_id: string;
  username: string;
  action: string;
  resource: string;
  timestamp: Date;
  ip_address: string;
  user_agent: string;
  success: boolean;
}

export interface SecurityAlert {
  id: string;
  type: SecurityAlertType;
  title: string;
  description: string;
  severity: ThreatSeverity;
  source: string;
  timestamp: Date;
  status: AlertStatus;
  acknowledged_by?: string;
  acknowledged_at?: Date;
  resolved_at?: Date;
}

export enum SecurityAlertType {
  AUTHENTICATION_FAILURE = 'authentication_failure',
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  DATA_BREACH = 'data_breach',
  MALWARE_DETECTED = 'malware_detected',
  UNAUTHORIZED_ACCESS = 'unauthorized_access',
  SYSTEM_COMPROMISE = 'system_compromise',
}

export enum AlertStatus {
  ACTIVE = 'active',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
  SUPPRESSED = 'suppressed',
}

export interface PerformanceMetrics {
  response_time: number;
  throughput: number;
  error_rate: number;
  cpu_usage: number;
  memory_usage: number;
  disk_io: number;
  network_io: number;
  active_connections: number;
  queue_length: number;
}

export interface DocumentProcessingStats {
  total_documents: number;
  processing: number;
  completed: number;
  failed: number;
  average_processing_time: number;
  queue_size: number;
  recent_documents: RecentDocument[];
}

export interface RecentDocument {
  id: string;
  filename: string;
  status: DocumentStatus;
  uploaded_by: string;
  uploaded_at: Date;
  processed_at?: Date;
  processing_time?: number;
  error_message?: string;
}

export enum DocumentStatus {
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  QUEUED = 'queued',
}

export interface DashboardConfig {
  defaultLayout: string;
  autoRefresh: boolean;
  refreshInterval: number;
  theme: 'light' | 'dark' | 'auto';
  notifications: NotificationConfig;
  widgets: WidgetConfig[];
}

export interface NotificationConfig {
  enabled: boolean;
  sound: boolean;
  desktop: boolean;
  email: boolean;
  severity_threshold: ThreatSeverity;
}

export interface DashboardState {
  currentLayout: string;
  widgets: DashboardWidget[];
  isFullscreen: boolean;
  isEditing: boolean;
  selectedWidget?: string;
  realTimeData: RealTimeData;
  lastUpdate: Date;
}

export interface WidgetUpdateEvent {
  widgetId: string;
  type: 'data' | 'config' | 'position' | 'size' | 'visibility';
  data: any;
  timestamp: Date;
}

export interface DashboardError {
  widgetId?: string;
  message: string;
  type: 'data' | 'connection' | 'permission' | 'validation';
  timestamp: Date;
  details?: any;
}
