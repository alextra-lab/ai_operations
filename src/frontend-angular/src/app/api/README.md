# API Integration Module

This module provides comprehensive API integration for the AI Operations Platform Angular frontend, replacing the Streamlit-based UI with a modern Angular application.

## Overview

The API integration module includes:

- **TypeScript Models**: Auto-generated from FastAPI OpenAPI spec
- **HTTP Services**: Complete API service layer with error handling
- **WebSocket Services**: Real-time data capabilities
- **Error Handling**: Centralized error management with user notifications
- **Caching**: API response caching with configurable TTL
- **Offline Support**: Request queuing for offline scenarios
- **Interceptors**: HTTP request/response interceptors for logging and error handling

## Architecture

```
src/app/api/
├── models/                 # TypeScript models from OpenAPI spec
│   ├── auth.models.ts      # Authentication models
│   ├── orchestrator.models.ts # Core API models
│   └── common.models.ts    # Shared models and types
├── services/               # API services
│   ├── api.service.ts      # Main HTTP API service
│   ├── websocket.service.ts # WebSocket service
│   └── api.service.spec.ts # Unit tests
├── index.ts               # Module exports
└── README.md              # This file

src/app/core/
├── services/
│   ├── error-handling.service.ts # Error management
│   ├── api-cache.service.ts      # Response caching
│   └── offline.service.ts        # Offline capabilities
└── interceptors/
    ├── error.interceptor.ts      # Error handling interceptor
    └── logging.interceptor.ts    # Request metadata logging
```

## Features

### 1. Type-Safe API Models

All API models are generated from the FastAPI OpenAPI specification, ensuring type safety and consistency between frontend and backend.

```typescript
import {
  LoginRequest,
  TokenResponse,
  UserResponse,
} from '../api/models/auth.models';

const loginData: LoginRequest = {
  username: 'user@example.com',
  password: 'securepassword',
};

apiService.login(loginData).subscribe((response: TokenResponse) => {
  // Store tokens securely; avoid logging sensitive values.
});
```

### 2. Comprehensive HTTP Service

The `ApiService` provides methods for all backend endpoints:

- **Authentication**: Login, logout, token refresh, user management
- **Core Operations**: Process requests, health checks
- **Document Management**: Upload, list, update, delete documents
- **Query Operations**: Semantic search, RAG Q&A
- **Analytics**: Usage statistics, hot documents

```typescript
// Example: Process a query request
const processRequest = {
  query: 'What are the latest security threats?',
  request_type: 'QUERY' as const,
  stream: false,
};

apiService.processRequest(processRequest).subscribe((response) => {
  // Handle response data in the UI; avoid logging user content.
});
```

### 3. Real-Time WebSocket Support

WebSocket service provides real-time updates for:

- Document processing status
- Query execution progress
- System health updates
- User notifications

```typescript
// Connect to WebSocket
const wsConfig = {
  url: 'ws://localhost:8000/ws',
  protocols: [],
  reconnectInterval: 5000,
  maxReconnectAttempts: 3,
};

webSocketService.connect(wsConfig).subscribe((message) => {
  // Handle real-time updates in the UI.
});

// Subscribe to specific message types
webSocketService.subscribeToDocumentUpdates().subscribe((update) => {
  // Update UI state from document processing updates.
});
```

### 4. Advanced Error Handling

Centralized error handling with user-friendly notifications:

```typescript
// Automatic error handling with user notifications
apiService.getDocuments().subscribe({
  next: (documents) => (this.documents = documents),
  error: (error) => {
    // Error is automatically handled by ErrorHandlingService
    // User sees appropriate notification
  },
});

// Manual error notifications
errorHandlingService.showErrorNotification(
  'Upload Failed',
  'File size exceeds maximum limit',
  'error'
);
```

### 5. API Response Caching

Intelligent caching system with configurable TTL:

```typescript
// Cache with default TTL (5 minutes)
apiCacheService.set('documents', documents);

// Cache with custom TTL (10 minutes)
apiCacheService.set('user-profile', profile, 10 * 60 * 1000);

// Get from cache
const cachedData = apiCacheService.get('documents');
if (cachedData) {
  cachedData.subscribe((data) => (this.documents = data));
}
```

### 6. Offline Support

Automatic request queuing when offline:

```typescript
// Check online status
offlineService.isOnline().subscribe((isOnline) => {
  if (isOnline) {
    this.isOnline = true;
  } else {
    this.isOnline = false;
  }
});

// Queue status
const queueStatus = offlineService.getQueueStatus();
this.queueSize = queueStatus.size;
```

## Usage Examples

### Basic API Integration

```typescript
import { Component, OnInit } from '@angular/core';
import { ApiService } from '../api/services/api.service';

@Component({
  selector: 'app-example',
  template: `
    <div>
      <button (click)="loadDocuments()">Load Documents</button>
      <div *ngFor="let doc of documents">
        {{ doc.title }}
      </div>
    </div>
  `,
})
export class ExampleComponent implements OnInit {
  documents: any[] = [];

  constructor(private apiService: ApiService) {}

  loadDocuments(): void {
    this.apiService.getDocuments({ limit: 10 }).subscribe({
      next: (documents) => (this.documents = documents),
      error: (error) => console.error('Failed to load documents:', error),
    });
  }
}
```

### Real-Time Updates

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { WebSocketService } from '../api/services/websocket.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-realtime',
  template: `
    <div>
      <div *ngFor="let update of updates">
        {{ update.timestamp }}: {{ update.message }}
      </div>
    </div>
  `,
})
export class RealtimeComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  updates: any[] = [];

  constructor(private webSocketService: WebSocketService) {}

  ngOnInit(): void {
    // Subscribe to real-time updates
    this.webSocketService
      .subscribeToDocumentUpdates()
      .pipe(takeUntil(this.destroy$))
      .subscribe((update) => {
        this.updates.push(update);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

## Configuration

### Environment Configuration

Update `src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiBaseUrl: '/api/v1',
  wsBaseUrl: '/ws',
  verboseLogging: false, // Read from assets/env.js in runtime builds
};
```

### HTTP Interceptors

Interceptors are automatically configured in `app.config.ts`:

```typescript
provideHttpClient(
  withInterceptors([
    authInterceptor, // JWT token management
    securityInterceptor, // Security headers
    errorInterceptor, // Error handling
    loggingInterceptor, // Request/response logging
  ])
);
```

## Testing

### Unit Tests

Run the API service tests:

```bash
npm test -- --testNamePattern="ApiService"
```

### Integration Testing

Use the API test component at `/api-test` to manually test API integration:

1. Navigate to `http://localhost:4200/api-test`
2. Test health check, authentication, WebSocket connection, and error handling
3. Verify all API endpoints work correctly

### API Validation

The API integration validates:

- ✅ All API endpoints accessible with proper types
- ✅ Error handling works for all error scenarios
- ✅ WebSocket connections work for real-time data
- ✅ API responses are properly typed and validated
- ✅ Offline capabilities work when network is unavailable

## Migration from Streamlit

This Angular frontend replaces the Streamlit-based `ui-webapp` with:

- **Better Performance**: Client-side rendering, caching, offline support
- **Modern UI/UX**: Angular Material, responsive design, accessibility
- **Type Safety**: Full TypeScript integration with backend APIs
- **Real-Time Updates**: WebSocket support for live data
- **Enterprise Features**: Error handling, logging, security headers

## Future Enhancements

Planned improvements include:

- **GraphQL Support**: Alternative to REST for complex queries
- **Service Workers**: Enhanced offline capabilities
- **Progressive Web App**: Installable app with offline functionality
- **Advanced Caching**: Redis integration for shared cache
- **API Versioning**: Support for multiple API versions
- **Rate Limiting**: Client-side rate limiting and retry logic

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure backend CORS is configured for Angular dev server
2. **Authentication Failures**: Check JWT token expiration and refresh logic
3. **WebSocket Connection Issues**: Verify WebSocket endpoint is available
4. **Type Errors**: Regenerate types if backend API changes

### Performance Monitoring

Monitor API performance:

```typescript
// Check cache statistics
const cacheStats = apiCacheService.getStats();
this.cacheHitRate = cacheStats;

// Monitor offline queue
const queueStatus = offlineService.getQueueStatus();
this.queueSize = queueStatus.size;
```
