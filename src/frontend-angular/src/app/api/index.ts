/**
 * API module exports
 * This file exports all API-related services, models, and utilities
 */

// Models
export * from './models/auth.models';
export * from './models/common.models';
export * from './models/orchestrator.models';

// Services
export * from './services/api.service';
export * from './services/websocket.service';

// Core services (re-exported from core)
export { ApiCacheService } from '../core/services/api-cache.service';
export type {
  CacheConfig,
  CacheEntry,
} from '../core/services/api-cache.service';
export { ErrorHandlingService } from '../core/services/error-handling.service';
export type {
  ErrorLogEntry,
  ErrorNotification,
} from '../core/services/error-handling.service';
export { OfflineService } from '../core/services/offline.service';
export type {
  OfflineConfig,
  OfflineQueueEntry,
} from '../core/services/offline.service';

// Interceptors
export { errorInterceptor } from '../core/interceptors/error.interceptor';
export { loggingInterceptor } from '../core/interceptors/logging.interceptor';
