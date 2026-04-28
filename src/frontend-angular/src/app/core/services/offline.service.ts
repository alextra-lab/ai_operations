import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, fromEvent, merge } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

export interface OfflineQueueEntry {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;
  body?: any;
  headers?: Record<string, string>;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
}

export interface OfflineConfig {
  enableOfflineMode: boolean;
  queueSize: number;
  retryDelay: number; // milliseconds
  maxRetries: number;
  syncOnReconnect: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class OfflineService {
  private isOnline$ = new BehaviorSubject<boolean>(navigator.onLine);
  private offlineQueue: OfflineQueueEntry[] = [];
  private syncInProgress = false;

  private readonly config: OfflineConfig = {
    enableOfflineMode: true,
    queueSize: 50,
    retryDelay: 5000,
    maxRetries: 3,
    syncOnReconnect: true,
  };

  constructor() {
    this.setupNetworkListeners();
    this.loadOfflineQueue();
  }

  /**
   * Check if device is online
   */
  isOnline(): Observable<boolean> {
    return this.isOnline$.asObservable();
  }

  /**
   * Check if device is currently online
   */
  getIsOnline(): boolean {
    return this.isOnline$.value;
  }

  /**
   * Add request to offline queue
   */
  addToQueue(
    entry: Omit<OfflineQueueEntry, 'id' | 'timestamp' | 'retryCount'>
  ): void {
    if (!this.config.enforceOfflineMode) {
      return;
    }

    const queueEntry: OfflineQueueEntry = {
      ...entry,
      id: this.generateId(),
      timestamp: Date.now(),
      retryCount: 0,
    };

    this.offlineQueue.push(queueEntry);
    this.enforceQueueSize();
    this.saveOfflineQueue();
  }

  /**
   * Process offline queue when connection is restored
   */
  async processQueue(): Promise<void> {
    if (
      this.syncInProgress ||
      !this.getIsOnline() ||
      this.offlineQueue.length === 0
    ) {
      return;
    }

    this.syncInProgress = true;

    const queue = [...this.offlineQueue];
    this.offlineQueue = [];

    for (const entry of queue) {
      try {
        await this.processQueueEntry(entry);
      } catch (error) {
        console.error(`Failed to process queued request ${entry.id}:`, error);

        // Re-queue if retries available
        if (entry.retryCount < entry.maxRetries) {
          entry.retryCount++;
          this.offlineQueue.push(entry);
        }
      }
    }

    this.saveOfflineQueue();
    this.syncInProgress = false;
  }

  /**
   * Get offline queue status
   */
  getQueueStatus(): { size: number; entries: OfflineQueueEntry[] } {
    return {
      size: this.offlineQueue.length,
      entries: [...this.offlineQueue],
    };
  }

  /**
   * Clear offline queue
   */
  clearQueue(): void {
    this.offlineQueue = [];
    this.saveOfflineQueue();
  }

  /**
   * Check if request should be queued for offline processing
   */
  shouldQueueRequest(method: string, url: string): boolean {
    if (!this.config.enforceOfflineMode || this.getIsOnline()) {
      return false;
    }

    // Only queue certain types of requests
    const queueableMethods = ['POST', 'PUT', 'PATCH', 'DELETE'];
    return queueableMethods.includes(method);
  }

  /**
   * Get offline status message
   */
  getOfflineMessage(): string {
    if (!this.getIsOnline()) {
      return 'You are currently offline. Some features may be limited.';
    }

    if (this.offlineQueue.length > 0) {
      return `${this.offlineQueue.length} requests are queued for sync when online.`;
    }

    return '';
  }

  private setupNetworkListeners(): void {
    // Listen for online/offline events
    const online$ = fromEvent(window, 'online').pipe(map(() => true));
    const offline$ = fromEvent(window, 'offline').pipe(map(() => false));

    merge(online$, offline$)
      .pipe(startWith(navigator.onLine))
      .subscribe((isOnline) => {
        this.isOnline$.next(isOnline);

        if (isOnline && this.config.syncOnReconnect) {
          // Small delay to ensure connection is stable
          setTimeout(() => this.processQueue(), 1000);
        }
      });
  }

  private async processQueueEntry(entry: OfflineQueueEntry): Promise<void> {
    // This would typically use your HTTP client to make the request
    // For now, we'll simulate the request

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 100));

    // In a real implementation, you would make the actual HTTP request here
    // using your HTTP client (like HttpClient)
  }

  private enforceQueueSize(): void {
    if (this.offlineQueue.length > this.config.queueSize) {
      // Remove oldest entries
      this.offlineQueue = this.offlineQueue
        .sort((a, b) => a.timestamp - b.timestamp)
        .slice(-this.config.queueSize);
    }
  }

  private generateId(): string {
    return `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private loadOfflineQueue(): void {
    try {
      const saved = localStorage.getItem('offline_queue');
      if (saved) {
        this.offlineQueue = JSON.parse(saved);
      }
    } catch (error) {
      console.warn('Failed to load offline queue:', error);
    }
  }

  private saveOfflineQueue(): void {
    try {
      localStorage.setItem('offline_queue', JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.warn('Failed to save offline queue:', error);
    }
  }
}
