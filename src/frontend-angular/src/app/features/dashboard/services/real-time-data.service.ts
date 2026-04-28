import { Injectable, OnDestroy } from '@angular/core';
import {
  BehaviorSubject,
  Observable,
  Subject,
  interval,
  of,
  throwError,
} from 'rxjs';
import {
  catchError,
  distinctUntilChanged,
  map,
  switchMap,
  takeUntil,
  tap,
} from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import { WebSocketConfig } from '../../../api/models/common.models';
import {
  WebSocketConnectionState,
  WebSocketService,
} from '../../../api/services/websocket.service';
import {
  DocumentProcessingStats,
  PerformanceMetrics,
  QueryStats,
  RealTimeData,
  SecurityAlert,
  SystemHealth,
  ThreatEvent,
  UserActivity,
} from '../models/dashboard.models';

@Injectable({
  providedIn: 'root',
})
export class RealTimeDataService implements OnDestroy {
  private readonly destroy$ = new Subject<void>();
  private readonly realTimeData$ = new BehaviorSubject<RealTimeData | null>(
    null
  );
  private readonly connectionState$ =
    new BehaviorSubject<WebSocketConnectionState>(
      WebSocketConnectionState.DISCONNECTED
    );

  private wsConfig: WebSocketConfig;

  constructor(private webSocketService: WebSocketService) {
    // Construct WebSocket URL dynamically
    let url = environment.wsBaseUrl;
    if (url.startsWith('/')) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      url = `${protocol}//${window.location.host}${url}`;
    }
    // Ensure URL ends with /dashboard, handling potential trailing slash in wsBaseUrl
    url = url.endsWith('/') ? `${url}dashboard` : `${url}/dashboard`;

    this.wsConfig = {
      url: url,
      protocols: undefined, // Don't specify protocols - backend doesn't require them
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
    };

    this.initializeWebSocketConnection();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.webSocketService.disconnect();
  }

  /**
   * Get real-time data stream
   */
  getRealTimeData(): Observable<RealTimeData | null> {
    return this.realTimeData$.asObservable();
  }

  /**
   * Get threat feed events
   */
  getThreatFeed(): Observable<ThreatEvent[]> {
    return this.realTimeData$.pipe(
      map((data) => data?.threat_events || []),
      distinctUntilChanged(
        (prev, curr) =>
          prev.length === curr.length &&
          prev.every((event, index) => event.id === curr[index]?.id)
      )
    );
  }

  /**
   * Get system health status
   */
  getSystemHealth(): Observable<SystemHealth | null> {
    return this.realTimeData$.pipe(
      map((data) => data?.system_health || null),
      distinctUntilChanged(
        (prev, curr) =>
          prev?.status === curr?.status && prev?.uptime === curr?.uptime
      )
    );
  }

  /**
   * Get query stats
   */
  getQueryStats(): Observable<QueryStats | null> {
    return this.realTimeData$.pipe(
      map((data) => data?.query_stats || null),
      distinctUntilChanged(
        (prev, curr) =>
          prev?.total_queries === curr?.total_queries &&
          prev?.successful_queries === curr?.successful_queries
      )
    );
  }

  /**
   * Get user activity
   */
  getUserActivity(): Observable<UserActivity[]> {
    return this.realTimeData$.pipe(
      map((data) => data?.user_activity || []),
      distinctUntilChanged(
        (prev, curr) =>
          prev.length === curr.length &&
          prev.every(
            (activity, index) => activity.user_id === curr[index]?.user_id
          )
      )
    );
  }

  /**
   * Get security alerts
   */
  getSecurityAlerts(): Observable<SecurityAlert[]> {
    return this.realTimeData$.pipe(
      map((data) => data?.security_alerts || []),
      distinctUntilChanged(
        (prev, curr) =>
          prev.length === curr.length &&
          prev.every((alert, index) => alert.id === curr[index]?.id)
      )
    );
  }

  /**
   * Get performance metrics
   */
  getPerformanceMetrics(): Observable<PerformanceMetrics | null> {
    return this.realTimeData$.pipe(
      map((data) => data?.performance_metrics || null),
      distinctUntilChanged(
        (prev, curr) =>
          prev?.response_time === curr?.response_time &&
          prev?.throughput === curr?.throughput
      )
    );
  }

  /**
   * Get document processing stats
   */
  getDocumentProcessingStats(): Observable<DocumentProcessingStats | null> {
    return this.realTimeData$.pipe(
      map((data) => data?.document_processing || null),
      distinctUntilChanged(
        (prev, curr) =>
          prev?.total_documents === curr?.total_documents &&
          prev?.processing === curr?.processing
      )
    );
  }

  /**
   * Get connection state
   */
  getConnectionState(): Observable<WebSocketConnectionState> {
    return this.connectionState$.asObservable();
  }

  /**
   * Check if connected to real-time data
   */
  isConnected(): boolean {
    return this.webSocketService.isConnected();
  }

  /**
   * Request specific data update
   */
  requestDataUpdate(dataType: string): void {
    this.webSocketService.send({
      type: 'request_data_update',
      data: { data_type: dataType },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Subscribe to specific threat events
   */
  subscribeToThreatEvents(severity?: string): Observable<ThreatEvent[]> {
    return this.getThreatFeed().pipe(
      map((events) =>
        severity
          ? events.filter((event) => event.severity === severity)
          : events
      )
    );
  }

  /**
   * Subscribe to security alerts by type
   */
  subscribeToSecurityAlerts(alertType?: string): Observable<SecurityAlert[]> {
    return this.getSecurityAlerts().pipe(
      map((alerts) =>
        alertType ? alerts.filter((alert) => alert.type === alertType) : alerts
      )
    );
  }

  /**
   * Get real-time data for specific time range
   */
  getDataForTimeRange(
    startTime: Date,
    endTime: Date
  ): Observable<RealTimeData | null> {
    // Request historical data for the specified time range
    this.webSocketService.send({
      type: 'request_historical_data',
      data: {
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
      },
      timestamp: new Date().toISOString(),
    });

    // Return current data (in a real implementation, this would fetch historical data)
    return this.realTimeData$.asObservable();
  }

  /**
   * Acknowledge security alert
   */
  acknowledgeAlert(alertId: string, userId: string): Observable<boolean> {
    return new Observable((observer) => {
      const success = this.webSocketService.send({
        type: 'acknowledge_alert',
        data: {
          alert_id: alertId,
          user_id: userId,
        },
        timestamp: new Date().toISOString(),
      });

      observer.next(success);
      observer.complete();
    });
  }

  /**
   * Resolve security alert
   */
  resolveAlert(
    alertId: string,
    resolution: string,
    userId: string
  ): Observable<boolean> {
    return new Observable((observer) => {
      const success = this.webSocketService.send({
        type: 'resolve_alert',
        data: {
          alert_id: alertId,
          resolution: resolution,
          user_id: userId,
        },
        timestamp: new Date().toISOString(),
      });

      observer.next(success);
      observer.complete();
    });
  }

  /**
   * Initialize WebSocket connection
   */
  private initializeWebSocketConnection(): void {
    // Monitor connection state
    this.webSocketService
      .getConnectionState()
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => {
        this.connectionState$.next(state);
      });

    // Connect to WebSocket and subscribe to real-time data
    this.webSocketService
      .connect(this.wsConfig)
      .pipe(
        takeUntil(this.destroy$),
        tap((message) => {
          if (message.type === 'dashboard_data') {
            this.handleDashboardData(message.data);
          } else {
            console.warn('Unknown message type:', message.type);
          }
        }),
        catchError((error) => {
          console.error('WebSocket connection error:', error);
          this.connectionState$.next(WebSocketConnectionState.ERROR);
          return throwError(error);
        })
      )
      .subscribe();

    // Set up periodic data requests if not connected
    interval(30000) // Request data every 30 seconds
      .pipe(
        takeUntil(this.destroy$),
        switchMap(() =>
          this.connectionState$.pipe(
            map((state) => state === WebSocketConnectionState.CONNECTED)
          )
        ),
        switchMap((isConnected) =>
          isConnected ? of(null) : this.requestFallbackData()
        )
      )
      .subscribe();
  }

  /**
   * Handle incoming dashboard data
   */
  private handleDashboardData(data: any): void {
    try {
      const realTimeData: RealTimeData = {
        threat_events: data.threat_events || [],
        system_health: data.system_health || this.getDefaultSystemHealth(),
        query_stats: data.query_stats || this.getDefaultQueryStats(),
        user_activity: data.user_activity || [],
        security_alerts: data.security_alerts || [],
        performance_metrics:
          data.performance_metrics || this.getDefaultPerformanceMetrics(),
        document_processing:
          data.document_processing || this.getDefaultDocumentProcessingStats(),
        timestamp: new Date(data.timestamp || Date.now()),
      };

      this.realTimeData$.next(realTimeData);
    } catch (error) {
      console.error('Error processing dashboard data:', error);
    }
  }

  /**
   * Request fallback data when WebSocket is not available
   */
  private requestFallbackData(): Observable<RealTimeData> {
    // In a real implementation, this would make HTTP requests to get data
    const fallbackData: RealTimeData = {
      threat_events: [],
      system_health: this.getDefaultSystemHealth(),
      query_stats: this.getDefaultQueryStats(),
      user_activity: [],
      security_alerts: [],
      performance_metrics: this.getDefaultPerformanceMetrics(),
      document_processing: this.getDefaultDocumentProcessingStats(),
      timestamp: new Date(),
    };

    this.realTimeData$.next(fallbackData);
    return of(fallbackData);
  }

  /**
   * Get default system health data
   */
  private getDefaultSystemHealth(): SystemHealth {
    return {
      status: 'healthy' as any,
      uptime: 0,
      cpu_usage: 0,
      memory_usage: 0,
      disk_usage: 0,
      network_status: {
        latency: 0,
        bandwidth: 0,
        packet_loss: 0,
        status: 'up',
      },
      services: [],
      last_check: new Date(),
    };
  }

  /**
   * Get default query stats
   */
  private getDefaultQueryStats(): QueryStats {
    return {
      total_queries: 0,
      successful_queries: 0,
      failed_queries: 0,
      average_response_time: 0,
      queries_per_hour: 0,
      top_queries: [],
      recent_queries: [],
    };
  }

  /**
   * Get default performance metrics
   */
  private getDefaultPerformanceMetrics(): PerformanceMetrics {
    return {
      response_time: 0,
      throughput: 0,
      error_rate: 0,
      cpu_usage: 0,
      memory_usage: 0,
      disk_io: 0,
      network_io: 0,
      active_connections: 0,
      queue_length: 0,
    };
  }

  /**
   * Get default document processing stats
   */
  private getDefaultDocumentProcessingStats(): DocumentProcessingStats {
    return {
      total_documents: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      average_processing_time: 0,
      queue_size: 0,
      recent_documents: [],
    };
  }
}
