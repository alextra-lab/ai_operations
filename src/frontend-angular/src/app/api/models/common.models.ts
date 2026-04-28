/**
 * Common models and types used across the API
 */

export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  success: boolean;
  timestamp?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
  timestamp: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version?: string;
  uptime?: number;
}

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

export interface RequestConfig {
  headers?: Record<string, string>;
  timeout?: number;
  retryAttempts?: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface WebSocketMessage<T = any> {
  type: string;
  data: T;
  timestamp: string;
  id?: string;
}

export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}
