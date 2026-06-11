import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

import { ApiService } from '../../api/services/api.service';
import { WebSocketService } from '../../api/services/websocket.service';
import {
  ErrorHandlingService,
  ErrorNotification,
} from '../../core/services/error-handling.service';

@Component({
  selector: 'app-api-test',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="api-test-container">
      <h2>API Integration Test</h2>

      <!-- Health Check Section -->
      <div class="test-section">
        <h3>Health Check</h3>
        <button (click)="testHealthCheck()" [disabled]="loading">
          Test Health Check
        </button>
        <div *ngIf="healthStatus" class="result">
          <pre>{{ healthStatus | json }}</pre>
        </div>
      </div>

      <!-- Authentication Test Section -->
      <div class="test-section">
        <h3>Authentication Test</h3>
        <form (ngSubmit)="testLogin()">
          <div>
            <label>Username:</label>
            <input [(ngModel)]="loginForm.username" name="username" required />
          </div>
          <div>
            <label>Password:</label>
            <input
              [(ngModel)]="loginForm.password"
              name="password"
              type="password"
              required
            />
          </div>
          <button type="submit" [disabled]="loading">Test Login</button>
        </form>
        <div *ngIf="loginResult" class="result">
          <pre>{{ loginResult | json }}</pre>
        </div>
      </div>

      <!-- WebSocket Test Section -->
      <div class="test-section">
        <h3>WebSocket Connection Test</h3>
        <button (click)="testWebSocket()" [disabled]="loading">
          Test WebSocket
        </button>
        <div *ngIf="wsStatus" class="result">
          <p>Status: {{ wsStatus }}</p>
        </div>
        <div *ngIf="wsMessages.length > 0" class="result">
          <h4>Messages:</h4>
          <div *ngFor="let message of wsMessages" class="message">
            <pre>{{ message | json }}</pre>
          </div>
        </div>
      </div>

      <!-- Error Handling Test -->
      <div class="test-section">
        <h3>Error Handling Test</h3>
        <button (click)="testErrorHandling()" [disabled]="loading">
          Test Error Handling
        </button>
        <div *ngIf="errorTestResult" class="result">
          <pre>{{ errorTestResult | json }}</pre>
        </div>
      </div>

      <!-- Loading Indicator -->
      <div *ngIf="loading" class="loading">
        <p>Loading...</p>
      </div>

      <!-- Notifications -->
      <div
        *ngFor="let notification of notifications"
        class="notification"
        [ngClass]="notification.type"
      >
        <strong>{{ notification.title }}:</strong> {{ notification.message }}
        <button (click)="dismissNotification(notification.id)">×</button>
      </div>
    </div>
  `,
  styles: [
    `
      .api-test-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
      }

      .test-section {
        margin-bottom: 30px;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 8px;
      }

      .test-section h3 {
        margin-top: 0;
        color: #333;
      }

      .result {
        margin-top: 15px;
        padding: 10px;
        background-color: #f5f5f5;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
      }

      .message {
        margin-bottom: 10px;
        padding: 8px;
        background-color: #e8f4fd;
        border-radius: 4px;
      }

      .loading {
        text-align: center;
        padding: 20px;
        color: #666;
      }

      .notification {
        margin: 10px 0;
        padding: 10px;
        border-radius: 4px;
        position: relative;
      }

      .notification.error {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
      }

      .notification.warning {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
      }

      .notification.info {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
      }

      .notification button {
        position: absolute;
        right: 10px;
        top: 10px;
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
      }

      form div {
        margin-bottom: 10px;
      }

      label {
        display: inline-block;
        width: 100px;
        font-weight: bold;
      }

      input {
        padding: 5px;
        border: 1px solid #ccc;
        border-radius: 4px;
        width: 200px;
      }

      button {
        padding: 8px 16px;
        background-color: #2196f3;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }

      button:disabled {
        background-color: #ccc;
        cursor: not-allowed;
      }

      button:hover:not(:disabled) {
        background-color: #1976d2;
      }
    `,
  ],
})
export class ApiTestComponent implements OnInit, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  private destroy$ = new Subject<void>();

  loading = false;
  healthStatus: any = null;
  loginResult: any = null;
  wsStatus = 'Disconnected';
  wsMessages: any[] = [];
  errorTestResult: any = null;
  notifications: ErrorNotification[] = [];

  loginForm = {
    username: 'admin',
    password: 'test123',
  };

  constructor(
    private apiService: ApiService,
    private webSocketService: WebSocketService,
    private errorHandlingService: ErrorHandlingService
  ) {}

  ngOnInit(): void {
    // Get recent error notifications
    this.notifications = this.errorHandlingService.getRecentNotifications(10);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.webSocketService.disconnect();
  }

  testHealthCheck(): void {
    this.loading = true;
    this.apiService
      .healthCheck()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.healthStatus = result;
          this.errorHandlingService.showSuccessNotification(
            'Health Check',
            'API is healthy!'
          );
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.healthStatus = { error: error.message };
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  testLogin(): void {
    this.loading = true;
    this.apiService
      .login(this.loginForm)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.loginResult = result;
          localStorage.setItem('access_token', result.access_token);
          this.errorHandlingService.showSuccessNotification(
            'Login',
            'Successfully logged in!'
          );
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.loginResult = { error: error.message };
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  testWebSocket(): void {
    this.wsStatus = 'Connecting...';
    this.wsMessages = [];

    const wsConfig = {
      url: 'ws://localhost:8000/ws',
      protocols: [],
      reconnectInterval: 5000,
      maxReconnectAttempts: 3,
    };

    this.webSocketService
      .connect(wsConfig)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (message) => {
          this.wsMessages.push(message);
        },
        error: (error) => {
          this.wsStatus = 'Error: ' + error.message;
        },
      });

    // Monitor connection state
    this.webSocketService
      .getConnectionState()
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => {
        this.wsStatus = state;
      });
  }

  testErrorHandling(): void {
    this.loading = true;
    this.errorTestResult = null;

    // Test with invalid endpoint to trigger error
    this.apiService
      .testProtectedRoute()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.errorTestResult = result;
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.errorTestResult = { error: error.message, handled: true };
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  dismissNotification(notificationId: string): void {
    this.errorHandlingService.dismissNotification(notificationId);
  }
}
