import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';

import { LucideAngularModule } from 'lucide-angular';
import {
  SecurityAlert,
  SecurityEvent,
  SecurityMetrics,
  SecurityMonitoringService,
} from '../../core/security/security-monitoring.service';
import { SecurityHeadersService } from '../../core/services/security-headers.service';

/**
 * Security dashboard component that displays security status, events, and alerts.
 * This component demonstrates the security monitoring capabilities.
 */
@Component({
  selector: 'app-security-dashboard',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatProgressBarModule,
    MatChipsModule,
    MatTableModule,
    MatTabsModule,
    MatBadgeModule,
  ],
  template: `
    <div class="security-dashboard">
      <h1>Security Dashboard</h1>

      <!-- Security Metrics Overview -->
      <div class="metrics-grid">
        <mat-card class="metric-card">
          <mat-card-header>
            <mat-card-title>Security Score</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="score-display">
              <span class="score-value">{{ securityMetrics.score }}%</span>
              <mat-progress-bar
                mode="determinate"
                [value]="securityMetrics.score"
                [color]="getScoreColor(securityMetrics.score)"
              >
              </mat-progress-bar>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="metric-card">
          <mat-card-header>
            <mat-card-title>Recent Events</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="metric-value">{{ securityMetrics.recentEvents }}</div>
            <div class="metric-label">Last 24 hours</div>
          </mat-card-content>
        </mat-card>

        <mat-card class="metric-card">
          <mat-card-header>
            <mat-card-title>Active Alerts</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="metric-value">{{ securityMetrics.recentAlerts }}</div>
            <div class="metric-label">Unacknowledged</div>
          </mat-card-content>
        </mat-card>

        <mat-card class="metric-card">
          <mat-card-header>
            <mat-card-title>Risk Level</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <mat-chip [color]="getRiskColor(securityMetrics.riskLevel)">
              {{ securityMetrics.riskLevel.toUpperCase() }}
            </mat-chip>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Security Events and Alerts Tabs -->
      <mat-tab-group>
        <mat-tab label="Recent Events">
          <div class="events-container">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Security Events</mat-card-title>
                <mat-card-subtitle
                  >Real-time security event monitoring</mat-card-subtitle
                >
              </mat-card-header>
              <mat-card-content>
                <div
                  class="events-list"
                  *ngIf="recentEvents.length > 0; else noEvents"
                >
                  <div
                    *ngFor="let event of recentEvents"
                    class="event-item"
                    [ngClass]="'severity-' + event.severity"
                  >
                    <div class="event-header">
                      <lucide-icon
                        [ngClass]="'severity-' + event.severity"
                        [name]="getEventIcon(event.type)"
                      ></lucide-icon>
                      <span class="event-type">{{ event.type }}</span>
                      <span class="event-time">{{
                        formatTime(event.timestamp)
                      }}</span>
                    </div>
                    <div class="event-message">{{ event.message }}</div>
                    <div class="event-details" *ngIf="event.details">
                      <pre>{{ formatDetails(event.details) }}</pre>
                    </div>
                  </div>
                </div>
                <ng-template #noEvents>
                  <div class="no-events">
                    <lucide-icon name="shield"></lucide-icon>
                    <p>No security events detected</p>
                  </div>
                </ng-template>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <mat-tab label="Security Alerts">
          <div class="alerts-container">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Security Alerts</mat-card-title>
                <mat-card-subtitle
                  >High-priority security notifications</mat-card-subtitle
                >
              </mat-card-header>
              <mat-card-content>
                <div
                  class="alerts-list"
                  *ngIf="securityAlerts.length > 0; else noAlerts"
                >
                  <div
                    *ngFor="let alert of securityAlerts"
                    class="alert-item"
                    [ngClass]="'severity-' + alert.severity"
                  >
                    <div class="alert-header">
                      <lucide-icon
                        [ngClass]="'severity-' + alert.severity"
                        [name]="getAlertIcon(alert.severity)"
                      ></lucide-icon>
                      <span class="alert-title">{{ alert.title }}</span>
                      <span class="alert-time">{{
                        formatTime(alert.timestamp)
                      }}</span>
                      <mat-chip
                        *ngIf="!alert.acknowledged"
                        color="warn"
                        class="unacknowledged"
                      >
                        NEW
                      </mat-chip>
                    </div>
                    <div class="alert-message">{{ alert.message }}</div>
                    <div class="alert-actions">
                      <button
                        mat-button
                        color="primary"
                        (click)="acknowledgeAlert(alert.id)"
                        *ngIf="!alert.acknowledged"
                      >
                        Acknowledge
                      </button>
                    </div>
                  </div>
                </div>
                <ng-template #noAlerts>
                  <div class="no-alerts">
                    <lucide-icon name="circle-check"></lucide-icon>
                    <p>No active security alerts</p>
                  </div>
                </ng-template>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <mat-tab label="Security Headers">
          <div class="headers-container">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Security Headers Status</mat-card-title>
                <mat-card-subtitle
                  >HTTP security header compliance</mat-card-subtitle
                >
              </mat-card-header>
              <mat-card-content>
                <div class="headers-status">
                  <div
                    class="header-item"
                    *ngFor="let header of expectedHeaders"
                  >
                    <lucide-icon
                      [color]="isHeaderPresent(header) ? 'primary' : 'warn'"
                      [name]="
                        isHeaderPresent(header)
                          ? 'circle-check'
                          : 'circle-alert'
                      "
                    ></lucide-icon>
                    <span class="header-name">{{ header }}</span>
                    <span class="header-value" *ngIf="isHeaderPresent(header)">
                      {{ getHeaderValue(header) }}
                    </span>
                  </div>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <button
          mat-raised-button
          color="primary"
          (click)="refreshSecurityData()"
        >
          <lucide-icon name="refresh-cw"></lucide-icon>
          Refresh
        </button>
        <button mat-raised-button color="accent" (click)="clearSecurityData()">
          <lucide-icon name="list-x"></lucide-icon>
          Clear Data
        </button>
        <button mat-raised-button color="warn" (click)="testSecurityFeatures()">
          <lucide-icon name="bug"></lucide-icon>
          Test Security
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .security-dashboard {
        padding: 20px;
        max-width: 1200px;
        margin: 0 auto;
      }

      .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
      }

      .metric-card {
        text-align: center;
      }

      .score-display {
        margin: 20px 0;
      }

      .score-value {
        font-size: 2em;
        font-weight: bold;
        color: #1976d2;
      }

      .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #1976d2;
      }

      .metric-label {
        color: #666;
        font-size: 0.9em;
      }

      .events-container,
      .alerts-container,
      .headers-container {
        margin-top: 20px;
      }

      .events-list,
      .alerts-list {
        max-height: 400px;
        overflow-y: auto;
      }

      .event-item,
      .alert-item {
        border-left: 4px solid #ddd;
        padding: 15px;
        margin-bottom: 10px;
        background: #f9f9f9;
      }

      .event-item.severity-high,
      .alert-item.severity-high {
        border-left-color: #f44336;
        background: #ffebee;
      }

      .event-item.severity-medium,
      .alert-item.severity-medium {
        border-left-color: #ff9800;
        background: #fff3e0;
      }

      .event-item.severity-low,
      .alert-item.severity-low {
        border-left-color: #4caf50;
        background: #e8f5e8;
      }

      .event-item.severity-critical,
      .alert-item.severity-critical {
        border-left-color: #d32f2f;
        background: #ffcdd2;
      }

      .event-header,
      .alert-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
      }

      .event-type,
      .alert-title {
        font-weight: bold;
        flex: 1;
      }

      .event-time,
      .alert-time {
        color: #666;
        font-size: 0.9em;
      }

      .event-message,
      .alert-message {
        margin-bottom: 10px;
      }

      .event-details pre {
        background: #f5f5f5;
        padding: 10px;
        border-radius: 4px;
        font-size: 0.8em;
        overflow-x: auto;
      }

      .alert-actions {
        margin-top: 10px;
      }

      .unacknowledged {
        font-size: 0.7em;
      }

      .headers-status {
        display: grid;
        gap: 10px;
      }

      .header-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px;
        background: #f9f9f9;
        border-radius: 4px;
      }

      .header-name {
        font-weight: bold;
        min-width: 200px;
      }

      .header-value {
        color: #666;
        font-family: monospace;
        font-size: 0.9em;
      }

      .no-events,
      .no-alerts {
        text-align: center;
        padding: 40px;
        color: #666;
      }

      .no-events mat-icon,
      .no-alerts mat-icon {
        font-size: 3em;
        margin-bottom: 20px;
      }

      .action-buttons {
        display: flex;
        gap: 10px;
        margin-top: 30px;
        justify-content: center;
      }

      .action-buttons button {
        margin: 0 5px;
      }
    `,
  ],
})
export class SecurityDashboardComponent implements OnInit {
  private securityMonitoring = inject(SecurityMonitoringService);
  private securityHeaders = inject(SecurityHeadersService);

  securityMetrics: SecurityMetrics = {
    totalEvents: 0,
    recentEvents: 0,
    totalAlerts: 0,
    recentAlerts: 0,
    violationCount: 0,
    riskLevel: 'low',
    lastUpdated: new Date().toISOString(),
  };

  recentEvents: SecurityEvent[] = [];
  securityAlerts: SecurityAlert[] = [];
  expectedHeaders = [
    'Strict-Transport-Security',
    'X-Content-Type-Options',
    'X-Frame-Options',
    'Referrer-Policy',
    'X-XSS-Protection',
    'Permissions-Policy',
    'Content-Security-Policy',
  ];

  ngOnInit(): void {
    this.loadSecurityData();
  }

  private loadSecurityData(): void {
    // Load security metrics
    this.securityMetrics = this.securityMonitoring.getSecurityMetrics();

    // Load recent events
    this.securityMonitoring.getSecurityEvents().subscribe((events) => {
      this.recentEvents = events.slice(0, 20); // Show last 20 events
    });

    // Load security alerts
    this.securityMonitoring.getSecurityAlerts().subscribe((alerts) => {
      this.securityAlerts = alerts.slice(0, 10); // Show last 10 alerts
    });
  }

  refreshSecurityData(): void {
    this.loadSecurityData();
  }

  clearSecurityData(): void {
    this.securityMonitoring.clearSecurityData();
    this.loadSecurityData();
  }

  testSecurityFeatures(): void {
    // Test XSS protection
    this.securityMonitoring.logSecurityEvent({
      id: this.generateEventId(),
      type: 'XSS_TEST',
      severity: 'low',
      message: 'Testing XSS protection capabilities',
      details: {
        testType: 'xss_protection',
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date().toISOString(),
      source: 'user',
    });

    // Test CSP validation
    this.securityMonitoring.logSecurityEvent({
      id: this.generateEventId(),
      type: 'CSP_TEST',
      severity: 'low',
      message: 'Testing CSP validation',
      details: {
        testType: 'csp_validation',
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date().toISOString(),
      source: 'user',
    });
  }

  acknowledgeAlert(alertId: string): void {
    // In a real implementation, this would call a service method
  }

  getScoreColor(score: number): string {
    if (score >= 90) return 'primary';
    if (score >= 70) return 'accent';
    return 'warn';
  }

  getRiskColor(riskLevel: string): string {
    switch (riskLevel) {
      case 'low':
        return 'primary';
      case 'medium':
        return 'accent';
      case 'high':
        return 'warn';
      case 'critical':
        return 'warn';
      default:
        return 'primary';
    }
  }

  getEventIcon(eventType: string): string {
    switch (eventType) {
      case 'CSP_VIOLATION':
        return 'shield';
      case 'XSS_ATTEMPT':
        return 'triangle-alert';
      case 'MISSING_SECURITY_HEADERS':
        return 'circle-alert';
      case 'HTTP_SECURITY_ERROR':
        return 'circle-alert';
      default:
        return 'info';
    }
  }

  getAlertIcon(severity: string): string {
    switch (severity) {
      case 'critical':
        return 'circle-alert';
      case 'high':
        return 'triangle-alert';
      case 'medium':
        return 'info';
      case 'low':
        return 'circle-check';
      default:
        return 'info';
    }
  }

  formatTime(timestamp: string): string {
    return new Date(timestamp).toLocaleString();
  }

  formatDetails(details: any): string {
    return JSON.stringify(details, null, 2);
  }

  isHeaderPresent(header: string): boolean {
    // In a real implementation, this would check actual response headers
    // For now, we'll simulate some headers being present
    const presentHeaders = [
      'X-Content-Type-Options',
      'X-Frame-Options',
      'Referrer-Policy',
    ];
    return presentHeaders.includes(header);
  }

  getHeaderValue(header: string): string {
    // In a real implementation, this would return actual header values
    const mockValues: Record<string, string> = {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'SAMEORIGIN',
      'Referrer-Policy': 'no-referrer',
    };
    return mockValues[header] || 'Not set';
  }

  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
