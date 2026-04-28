import { Injectable, inject } from '@angular/core';
import { SecurityHeadersService } from './security-headers.service';
import { SecurityMonitoringService } from './security-monitoring.service';

/**
 * Service responsible for initializing security features on application startup.
 * Sets up CSP reporting, security monitoring, and other security measures.
 */
@Injectable({ providedIn: 'root' })
export class SecurityInitializationService {
  private securityHeadersService = inject(SecurityHeadersService);
  private securityMonitoring = inject(SecurityMonitoringService);

  /**
   * Initializes all security features.
   * This should be called during application startup.
   */
  initializeSecurity(): void {
    // Set up CSP violation reporting
    this.setupCSPReporting();

    // Start security monitoring
    this.startSecurityMonitoring();

    // Set up global security event listeners
    this.setupGlobalSecurityListeners();

    // Log security initialization
    this.securityMonitoring.logSecurityEvent({
      id: this.generateEventId(),
      type: 'SECURITY_INITIALIZATION',
      severity: 'low',
      message: 'Security features initialized successfully',
      details: {
        timestamp: new Date().toISOString(),
        features: [
          'CSP reporting',
          'Security monitoring',
          'XSS protection',
          'Security headers validation',
        ],
      },
      timestamp: new Date().toISOString(),
      source: 'initialization',
    });
  }

  /**
   * Sets up Content Security Policy violation reporting.
   */
  private setupCSPReporting(): void {
    this.securityHeadersService.setupCSPReporting();
  }

  /**
   * Starts the security monitoring service.
   */
  private startSecurityMonitoring(): void {
    this.securityMonitoring.startMonitoring();
  }

  /**
   * Sets up global security event listeners.
   */
  private setupGlobalSecurityListeners(): void {
    // Listen for page visibility changes to detect potential attacks
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.securityMonitoring.logSecurityEvent({
          id: this.generateEventId(),
          type: 'PAGE_HIDDEN',
          severity: 'low',
          message: 'Page became hidden',
          details: {
            timestamp: new Date().toISOString(),
          },
          timestamp: new Date().toISOString(),
          source: 'browser',
        });
      }
    });

    // Listen for beforeunload to detect potential navigation attacks
    window.addEventListener('beforeunload', (event) => {
      this.securityMonitoring.logSecurityEvent({
        id: this.generateEventId(),
        type: 'PAGE_UNLOAD',
        severity: 'low',
        message: 'Page is being unloaded',
        details: {
          timestamp: new Date().toISOString(),
          returnValue: event.returnValue,
        },
        timestamp: new Date().toISOString(),
        source: 'browser',
      });
    });

    // Listen for focus events to detect potential clickjacking
    window.addEventListener('focus', () => {
      this.securityMonitoring.logSecurityEvent({
        id: this.generateEventId(),
        type: 'WINDOW_FOCUS',
        severity: 'low',
        message: 'Window gained focus',
        details: {
          timestamp: new Date().toISOString(),
        },
        timestamp: new Date().toISOString(),
        source: 'browser',
      });
    });

    // Listen for blur events
    window.addEventListener('blur', () => {
      this.securityMonitoring.logSecurityEvent({
        id: this.generateEventId(),
        type: 'WINDOW_BLUR',
        severity: 'low',
        message: 'Window lost focus',
        details: {
          timestamp: new Date().toISOString(),
        },
        timestamp: new Date().toISOString(),
        source: 'browser',
      });
    });
  }

  /**
   * Gets current security status and metrics.
   */
  getSecurityStatus(): {
    isInitialized: boolean;
    metrics: any;
    alerts: any[];
  } {
    let alerts: any[] = [];
    this.securityMonitoring.getSecurityAlerts().subscribe((alertsList) => {
      alerts = alertsList;
    });

    return {
      isInitialized: true,
      metrics: this.securityMonitoring.getSecurityMetrics(),
      alerts: alerts,
    };
  }

  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
