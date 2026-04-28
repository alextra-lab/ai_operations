import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, EMPTY, Observable, Subject, timer } from 'rxjs';
import { filter, map, takeUntil } from 'rxjs/operators';

import { WebSocketConfig, WebSocketMessage } from '../models/common.models';

export enum WebSocketConnectionState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
  RECONNECTING = 'reconnecting',
}

@Injectable({
  providedIn: 'root',
})
export class WebSocketService implements OnDestroy {
  private ws: WebSocket | null = null;
  private connectionState$ = new BehaviorSubject<WebSocketConnectionState>(
    WebSocketConnectionState.DISCONNECTED
  );
  private messageSubject$ = new Subject<WebSocketMessage>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000;
  private destroy$ = new Subject<void>();

  constructor() { }

  /**
   * Connect to WebSocket server
   */
  connect<T = any>(config: WebSocketConfig): Observable<WebSocketMessage<T>> {
    const wsUrl = this.buildWebSocketUrl(config.url);

    try {
      // Close existing connection if any
      if (this.ws) {
        this.ws.close();
      }

      // Create a new Subject for this connection to avoid completion issues
      this.messageSubject$ = new Subject<WebSocketMessage>();

      this.ws = new WebSocket(wsUrl, config.protocols);
      this.connectionState$.next(WebSocketConnectionState.CONNECTING);

      this.ws.onopen = () => {
        this.connectionState$.next(WebSocketConnectionState.CONNECTED);
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage<T> = JSON.parse(event.data);
          this.messageSubject$.next(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        this.connectionState$.next(WebSocketConnectionState.DISCONNECTED);

        // Attempt to reconnect if not manually closed
        if (
          event.code !== 1000 &&
          this.reconnectAttempts < this.maxReconnectAttempts
        ) {
          this.scheduleReconnect(config);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionState$.next(WebSocketConnectionState.ERROR);
      };

      return this.messageSubject$.asObservable();
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.connectionState$.next(WebSocketConnectionState.ERROR);
      return EMPTY;
    }
  }

  /**
   * Send message through WebSocket
   */
  send<T = any>(message: WebSocketMessage<T>): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(
          JSON.stringify({
            ...message,
            timestamp: new Date().toISOString(),
          })
        );
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    }
    console.warn('WebSocket is not connected');
    return false;
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.destroy$.next();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.connectionState$.next(WebSocketConnectionState.DISCONNECTED);
  }

  /**
   * Get current connection state
   */
  getConnectionState(): Observable<WebSocketConnectionState> {
    return this.connectionState$.asObservable();
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Subscribe to specific message types
   */
  subscribeToMessageType<T = any>(
    messageType: string
  ): Observable<WebSocketMessage<T>> {
    return this.messageSubject$.pipe(
      filter((message) => message.type === messageType),
      map((message) => message as WebSocketMessage<T>)
    );
  }

  /**
   * Subscribe to real-time document processing updates
   */
  subscribeToDocumentUpdates(): Observable<WebSocketMessage> {
    return this.subscribeToMessageType('document_processing_update');
  }

  /**
   * Subscribe to real-time query processing updates
   */
  subscribeToQueryUpdates(): Observable<WebSocketMessage> {
    return this.subscribeToMessageType('query_processing_update');
  }

  /**
   * Subscribe to system health updates
   */
  subscribeToHealthUpdates(): Observable<WebSocketMessage> {
    return this.subscribeToMessageType('health_update');
  }

  /**
   * Subscribe to user notifications
   */
  subscribeToNotifications(): Observable<WebSocketMessage> {
    return this.subscribeToMessageType('notification');
  }

  /**
   * Request real-time document processing status
   */
  requestDocumentStatus(documentId: string): boolean {
    return this.send({
      type: 'request_document_status',
      data: { document_id: documentId },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Request real-time query processing status
   */
  requestQueryStatus(queryId: string): boolean {
    return this.send({
      type: 'request_query_status',
      data: { query_id: queryId },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Join a specific room/channel for targeted updates
   */
  joinRoom(roomId: string): boolean {
    return this.send({
      type: 'join_room',
      data: { room_id: roomId },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Leave a specific room/channel
   */
  leaveRoom(roomId: string): boolean {
    return this.send({
      type: 'leave_room',
      data: { room_id: roomId },
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Ping the WebSocket server to keep connection alive
   */
  ping(): boolean {
    return this.send({
      type: 'ping',
      data: {},
      timestamp: new Date().toISOString(),
    });
  }

  private buildWebSocketUrl(url: string): string {
    // Convert HTTP URL to WebSocket URL
    if (url.startsWith('http://')) {
      return url.replace('http://', 'ws://');
    } else if (url.startsWith('https://')) {
      return url.replace('https://', 'wss://');
    }
    return url;
  }

  private scheduleReconnect(config: WebSocketConfig): void {
    this.reconnectAttempts++;
    this.connectionState$.next(WebSocketConnectionState.RECONNECTING);

    timer(this.reconnectInterval)
      .pipe(
        takeUntil(this.destroy$),
        takeUntil(
          this.connectionState$.pipe(
            filter((state) => state === WebSocketConnectionState.CONNECTED)
          )
        )
      )
      .subscribe(() => {
        if (this.reconnectAttempts <= this.maxReconnectAttempts) {
          this.connect(config);
        } else {
          console.error('Max reconnection attempts reached');
          this.connectionState$.next(WebSocketConnectionState.ERROR);
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.disconnect();
  }
}
