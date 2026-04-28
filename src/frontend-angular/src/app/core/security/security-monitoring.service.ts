import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject, timer } from 'rxjs';
import {
  catchError,
  debounceTime,
  map,
  tap,
  throttleTime,
} from 'rxjs/operators';

/**
 * Service for monitoring security events and violations.
 * Provides real-time security monitoring and alerting capabilities.
 */
@Injectable({ providedIn: 'root' })
export class SecurityMonitoringService {
  private readonly securityEvents$ = new BehaviorSubject<SecurityEvent[]>([]);
  private readonly securityAlerts$ = new BehaviorSubject<SecurityAlert[]>([]);
  private readonly violationCount$ = new BehaviorSubject<number>(0);

  private readonly reportEndpoint = '/api/security/events';
  private readonly alertEndpoint = '/api/security/alerts';

  private monitoringInterval: any;
  private isMonitoring = false;
  private eventThrottle$ = new Subject<SecurityEvent>();

  constructor(private http: HttpClient) {
    this.setupGlobalSecurityMonitoring();
    this.setupEventThrottling();
  }

  /**
   * Setup throttling for security events to prevent spam
   */
  private setupEventThrottling(): void {
    this.eventThrottle$
      .pipe(
        throttleTime(5000), // Throttle to max 1 event per 5 seconds per type
        debounceTime(1000) // Debounce to batch similar events
      )
      .subscribe((event) => {
        this.processSecurityEvent(event);
      });
  }

  /**
   * Process security event with throttling
   */
  private processSecurityEvent(event: SecurityEvent): void {
    const events = this.securityEvents$.value;
    const newEvents = [event, ...events].slice(0, 1000); // Keep last 1000 events
    this.securityEvents$.next(newEvents);

    // Send to backend
    this.reportSecurityEvent(event).subscribe({
      error: (error) =>
        console.error('Failed to report security event:', error),
    });
  }

  /**
   * Gets observable of security events.
   */
  getSecurityEvents(): Observable<SecurityEvent[]> {
    return this.securityEvents$.asObservable();
  }

  /**
   * Gets observable of security alerts.
   */
  getSecurityAlerts(): Observable<SecurityAlert[]> {
    return this.securityAlerts$.asObservable();
  }

  /**
   * Gets observable of violation count.
   */
  getViolationCount(): Observable<number> {
    return this.violationCount$.asObservable();
  }

  /**
   * Logs a security event with throttling to prevent spam.
   */
  logSecurityEvent(event: SecurityEvent): void {
    // Use throttled approach to prevent excessive logging
    this.eventThrottle$.next(event);
  }

  /**
   * Detects security anomalies based on event patterns.
   */
  detectAnomalies(): Observable<SecurityAlert[]> {
    return this.getSecurityEvents().pipe(
      map((events) => this.analyzeEventPatterns(events)),
      tap((alerts) => {
        if (alerts.length > 0) {
          this.addSecurityAlerts(alerts);
        }
      })
    );
  }

  /**
   * Reports a security threat.
   */
  reportThreat(threat: ThreatReport): Observable<void> {
    return this.http.post<void>(`${this.reportEndpoint}/threat`, threat);
  }

  /**
   * Starts continuous security monitoring.
   */
  startMonitoring(): void {
    if (this.isMonitoring) return;

    this.isMonitoring = true;
    this.monitoringInterval = timer(0, 30000).subscribe(() => {
      this.performSecurityCheck();
    });
  }

  /**
   * Stops security monitoring.
   */
  stopMonitoring(): void {
    if (this.monitoringInterval) {
      this.monitoringInterval.unsubscribe();
      this.monitoringInterval = null;
    }
    this.isMonitoring = false;
  }

  /**
   * Clears all security events and alerts.
   */
  clearSecurityData(): void {
    this.securityEvents$.next([]);
    this.securityAlerts$.next([]);
    this.violationCount$.next(0);
  }

  /**
   * Gets security metrics summary.
   */
  getSecurityMetrics(): SecurityMetrics {
    const events = this.securityEvents$.value;
    const alerts = this.securityAlerts$.value;

    const now = new Date();
    const last24Hours = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const recentEvents = events.filter(
      (event) => new Date(event.timestamp) > last24Hours
    );

    const recentAlerts = alerts.filter(
      (alert) => new Date(alert.timestamp) > last24Hours
    );

    return {
      totalEvents: events.length,
      recentEvents: recentEvents.length,
      totalAlerts: alerts.length,
      recentAlerts: recentAlerts.length,
      violationCount: this.violationCount$.value,
      riskLevel: this.calculateOverallRiskLevel(events, alerts),
      lastUpdated: now.toISOString(),
    };
  }

  private setupGlobalSecurityMonitoring(): void {
    // Monitor for CSP violations
    document.addEventListener('securitypolicyviolation', (event) => {
      const violation: SecurityEvent = {
        id: this.generateEventId(),
        type: 'CSP_VIOLATION',
        severity: 'medium',
        message: `CSP violation: ${event.violatedDirective}`,
        details: {
          violatedDirective: event.violatedDirective,
          blockedUri: event.blockedURI,
          documentUri: event.documentURI,
          sourceFile: event.sourceFile,
          lineNumber: event.lineNumber,
        },
        timestamp: new Date().toISOString(),
        source: 'browser',
      };

      this.logSecurityEvent(violation);
    });

    // Monitor for XSS attempts
    this.monitorXSSAttempts();

    // Monitor for suspicious network activity
    this.monitorNetworkActivity();
  }

  private monitorXSSAttempts(): void {
    // Override innerHTML setter to detect XSS attempts
    const originalInnerHTML = Object.getOwnPropertyDescriptor(
      Element.prototype,
      'innerHTML'
    )?.set;

    if (originalInnerHTML) {
      // Capture service reference for use in closure
      const serviceInstance = this;

      Object.defineProperty(Element.prototype, 'innerHTML', {
        set: function (this: Element, value: string) {
          // Check for suspicious content using the service instance
          if (serviceInstance.containsSuspiciousContent(value)) {
            const event: SecurityEvent = {
              id: serviceInstance.generateEventId(),
              type: 'XSS_ATTEMPT',
              severity: 'high',
              message: 'Potential XSS attempt detected',
              details: {
                element: this.tagName,
                content: value.substring(0, 100) + '...',
                stack: new Error().stack,
              },
              timestamp: new Date().toISOString(),
              source: 'browser',
            };

            serviceInstance.logSecurityEvent(event);
          }

          originalInnerHTML.call(this, value);
        },
        get: Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML')
          ?.get,
      });
    }
  }

  private monitorNetworkActivity(): void {
    // Monitor fetch requests for suspicious patterns
    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      const url = args[0]?.toString() || '';

      if (this.isSuspiciousUrl(url)) {
        const event: SecurityEvent = {
          id: this.generateEventId(),
          type: 'SUSPICIOUS_REQUEST',
          severity: 'medium',
          message: 'Suspicious network request detected',
          details: {
            url: url,
            method: args[1]?.method || 'GET',
          },
          timestamp: new Date().toISOString(),
          source: 'browser',
        };

        this.logSecurityEvent(event);
      }

      return originalFetch.apply(window, args);
    };
  }

  private containsSuspiciousContent(content: string): boolean {
    const suspiciousPatterns = [
      /<script/i,
      /javascript:/i,
      /on\w+\s*=/i,
      /eval\s*\(/i,
      /document\.cookie/i,
    ];

    return suspiciousPatterns.some((pattern) => pattern.test(content));
  }

  private isSuspiciousUrl(url: string): boolean {
    const suspiciousPatterns = [
      /javascript:/i,
      /data:text\/html/i,
      /file:\/\//i,
      /ftp:\/\//i,
    ];

    return suspiciousPatterns.some((pattern) => pattern.test(url));
  }

  private analyzeEventPatterns(events: SecurityEvent[]): SecurityAlert[] {
    const alerts: SecurityAlert[] = [];
    const now = new Date();
    const last5Minutes = new Date(now.getTime() - 5 * 60 * 1000);

    // Check for high frequency of violations
    const recentViolations = events.filter(
      (event) =>
        new Date(event.timestamp) > last5Minutes &&
        event.type === 'CSP_VIOLATION'
    );

    if (recentViolations.length > 10) {
      alerts.push({
        id: this.generateAlertId(),
        type: 'HIGH_FREQUENCY_VIOLATIONS',
        severity: 'high',
        title: 'High frequency of security violations',
        message: `${recentViolations.length} violations detected in the last 5 minutes`,
        details: {
          violationCount: recentViolations.length,
          timeWindow: '5 minutes',
        },
        timestamp: new Date().toISOString(),
        acknowledged: false,
      });
    }

    // Check for XSS attempts
    const xssAttempts = events.filter((event) => event.type === 'XSS_ATTEMPT');

    if (xssAttempts.length > 0) {
      alerts.push({
        id: this.generateAlertId(),
        type: 'XSS_ATTEMPT_DETECTED',
        severity: 'critical',
        title: 'XSS attempt detected',
        message: `${xssAttempts.length} XSS attempts detected`,
        details: {
          attemptCount: xssAttempts.length,
          recentAttempts: xssAttempts.slice(0, 5),
        },
        timestamp: new Date().toISOString(),
        acknowledged: false,
      });
    }

    return alerts;
  }

  private addSecurityAlerts(alerts: SecurityAlert[]): void {
    const currentAlerts = this.securityAlerts$.value;
    const newAlerts = [...alerts, ...currentAlerts].slice(0, 100); // Keep last 100 alerts
    this.securityAlerts$.next(newAlerts);
  }

  private performSecurityCheck(): void {
    // Check for security header compliance
    this.checkSecurityHeaders();

    // Check for CSP compliance
    this.checkCSPCompliance();

    // Update violation count
    this.updateViolationCount();
  }

  private checkSecurityHeaders(): void {
    // This would typically check response headers from recent requests
    // For now, we'll simulate a check
    const hasRequiredHeaders = this.checkRequiredHeadersPresent();

    if (!hasRequiredHeaders) {
      const event: SecurityEvent = {
        id: this.generateEventId(),
        type: 'MISSING_SECURITY_HEADERS',
        severity: 'medium',
        message: 'Required security headers missing',
        details: {
          checkType: 'security_headers',
        },
        timestamp: new Date().toISOString(),
        source: 'monitoring',
      };

      this.logSecurityEvent(event);
    }
  }

  private checkCSPCompliance(): void {
    // Check if CSP is properly configured
    const cspHeader = this.getCSPHeader();

    if (!cspHeader) {
      const event: SecurityEvent = {
        id: this.generateEventId(),
        type: 'MISSING_CSP',
        severity: 'high',
        message: 'Content Security Policy not configured',
        details: {
          checkType: 'csp_compliance',
        },
        timestamp: new Date().toISOString(),
        source: 'monitoring',
      };

      this.logSecurityEvent(event);
    }
  }

  private checkRequiredHeadersPresent(): boolean {
    // This would check actual response headers
    // For now, return true as a placeholder
    return true;
  }

  private getCSPHeader(): string | null {
    // This would get the actual CSP header from the response
    // For now, return null as a placeholder
    return null;
  }

  private updateViolationCount(): void {
    const events = this.securityEvents$.value;
    const violationCount = events.filter(
      (event) =>
        event.type.includes('VIOLATION') || event.type.includes('ATTEMPT')
    ).length;

    this.violationCount$.next(violationCount);
  }

  private calculateOverallRiskLevel(
    events: SecurityEvent[],
    alerts: SecurityAlert[]
  ): 'low' | 'medium' | 'high' | 'critical' {
    const criticalAlerts = alerts.filter(
      (alert) => alert.severity === 'critical'
    ).length;
    const highAlerts = alerts.filter(
      (alert) => alert.severity === 'high'
    ).length;
    const recentEvents = events.filter(
      (event) =>
        new Date(event.timestamp) > new Date(Date.now() - 24 * 60 * 60 * 1000)
    ).length;

    if (criticalAlerts > 0 || recentEvents > 100) return 'critical';
    if (highAlerts > 2 || recentEvents > 50) return 'high';
    if (highAlerts > 0 || recentEvents > 20) return 'medium';
    return 'low';
  }

  private reportSecurityEvent(event: SecurityEvent): Observable<void> {
    return this.http.post<void>(this.reportEndpoint, event).pipe(
      catchError((error) => {
        console.error('Failed to report security event:', error);
        return [];
      })
    );
  }

  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateAlertId(): string {
    return `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export interface SecurityEvent {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: Record<string, any>;
  timestamp: string;
  source: 'browser' | 'monitoring' | 'user' | 'interceptor' | 'initialization';
}

export interface SecurityAlert {
  id: string;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  details: Record<string, any>;
  timestamp: string;
  acknowledged: boolean;
}

export interface ThreatReport {
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface SecurityMetrics {
  totalEvents: number;
  recentEvents: number;
  totalAlerts: number;
  recentAlerts: number;
  violationCount: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  lastUpdated: string;
}
