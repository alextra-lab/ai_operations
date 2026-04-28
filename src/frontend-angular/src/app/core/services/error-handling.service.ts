import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';

export interface ErrorNotification {
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  details?: string;
  timestamp: Date;
  id: string;
}

export interface ErrorLogEntry {
  error: Error;
  context?: any;
  timestamp: Date;
  userId?: string;
  requestId?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

@Injectable({
  providedIn: 'root',
})
export class ErrorHandlingService {
  private errorNotifications: ErrorNotification[] = [];
  private errorLogs: ErrorLogEntry[] = [];

  constructor() {}

  /**
   * Handle HTTP errors with appropriate user feedback
   */
  handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';
    let errorTitle = 'Error';
    let errorType: ErrorNotification['type'] = 'error';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Network Error: ${error.error.message}`;
      errorTitle = 'Connection Error';
      this.logError(
        new Error(errorMessage),
        { type: 'client_error', error },
        'medium'
      );
    } else {
      // Server-side error
      switch (error.status) {
        case 400:
          errorTitle = 'Invalid Request';
          errorMessage =
            this.extractServerErrorMessage(error) || 'The request was invalid';
          errorType = 'warning';
          this.logError(
            new Error(errorMessage),
            { type: 'bad_request', error },
            'medium'
          );
          break;
        case 401:
          errorTitle = 'Authentication Required';
          errorMessage = 'Please log in to continue';
          errorType = 'warning';
          this.logError(
            new Error('Authentication failed'),
            { type: 'auth_error', error },
            'high'
          );
          break;
        case 403:
          errorTitle = 'Access Denied';
          errorMessage = 'You do not have permission to perform this action';
          errorType = 'warning';
          this.logError(
            new Error('Access denied'),
            { type: 'permission_error', error },
            'high'
          );
          break;
        case 404:
          errorTitle = 'Not Found';
          errorMessage = 'The requested resource was not found';
          errorType = 'warning';
          this.logError(
            new Error('Resource not found'),
            { type: 'not_found', error },
            'low'
          );
          break;
        case 409:
          errorTitle = 'Conflict';
          errorMessage =
            this.extractServerErrorMessage(error) || 'A conflict occurred';
          errorType = 'warning';
          this.logError(
            new Error(errorMessage),
            { type: 'conflict_error', error },
            'medium'
          );
          break;
        case 422:
          errorTitle = 'Validation Error';
          errorMessage =
            this.extractValidationErrors(error) || 'Please check your input';
          errorType = 'warning';
          this.logError(
            new Error(errorMessage),
            { type: 'validation_error', error },
            'medium'
          );
          break;
        case 429:
          errorTitle = 'Rate Limited';
          errorMessage = 'Too many requests. Please try again later';
          errorType = 'warning';
          this.logError(
            new Error('Rate limited'),
            { type: 'rate_limit', error },
            'medium'
          );
          break;
        case 500:
          errorTitle = 'Server Error';
          errorMessage =
            'An internal server error occurred. Please try again later';
          errorType = 'error';
          this.logError(
            new Error('Internal server error'),
            { type: 'server_error', error },
            'critical'
          );
          break;
        case 502:
        case 503:
        case 504:
          errorTitle = 'Service Unavailable';
          errorMessage =
            'The service is temporarily unavailable. Please try again later';
          errorType = 'warning';
          this.logError(
            new Error('Service unavailable'),
            { type: 'service_unavailable', error },
            'high'
          );
          break;
        default:
          errorMessage =
            this.extractServerErrorMessage(error) ||
            `Server Error: ${error.status}`;
          this.logError(
            new Error(errorMessage),
            { type: 'unknown_error', error },
            'high'
          );
      }
    }

    // Show user notification
    this.showErrorNotification(errorTitle, errorMessage, errorType);

    return throwError(() => new Error(errorMessage));
  }

  /**
   * Show error notification to user
   */
  showErrorNotification(
    title: string,
    message: string,
    type: ErrorNotification['type'] = 'error',
    details?: string
  ): void {
    const notification: ErrorNotification = {
      id: this.generateId(),
      type,
      title,
      message,
      details,
      timestamp: new Date(),
    };

    this.errorNotifications.unshift(notification);

    // Keep only last 50 notifications
    if (this.errorNotifications.length > 50) {
      this.errorNotifications = this.errorNotifications.slice(0, 50);
    }

    // Log to console for development
    if (type === 'error') {
      console.error(`${title}: ${message}`, details);
    } else if (type === 'warning') {
      console.warn(`${title}: ${message}`, details);
    } else {
      console.info(`${title}: ${message}`, details);
    }
  }

  /**
   * Show success notification
   */
  showSuccessNotification(title: string, message: string): void {
    this.showErrorNotification(title, message, 'info');
  }

  /**
   * Show warning notification
   */
  showWarningNotification(
    title: string,
    message: string,
    details?: string
  ): void {
    this.showErrorNotification(title, message, 'warning', details);
  }

  /**
   * Log error for debugging and monitoring
   */
  logError(
    error: Error,
    context?: any,
    severity: ErrorLogEntry['severity'] = 'medium'
  ): void {
    const logEntry: ErrorLogEntry = {
      error,
      context,
      timestamp: new Date(),
      userId: this.getCurrentUserId(),
      requestId: this.generateRequestId(),
      severity,
    };

    this.errorLogs.unshift(logEntry);

    // Keep only last 100 log entries
    if (this.errorLogs.length > 100) {
      this.errorLogs = this.errorLogs.slice(0, 100);
    }

    // Send to external logging service in production
    this.sendToExternalLogging(logEntry);
  }

  /**
   * Get recent error notifications
   */
  getRecentNotifications(limit = 10): ErrorNotification[] {
    return this.errorNotifications.slice(0, limit);
  }

  /**
   * Get recent error logs
   */
  getRecentLogs(limit = 10): ErrorLogEntry[] {
    return this.errorLogs.slice(0, limit);
  }

  /**
   * Clear error notifications
   */
  clearNotifications(): void {
    this.errorNotifications = [];
  }

  /**
   * Clear error logs
   */
  clearLogs(): void {
    this.errorLogs = [];
  }

  /**
   * Dismiss specific notification
   */
  dismissNotification(notificationId: string): void {
    this.errorNotifications = this.errorNotifications.filter(
      (n) => n.id !== notificationId
    );
  }

  private extractServerErrorMessage(error: HttpErrorResponse): string | null {
    if (error.error?.detail) {
      if (typeof error.error.detail === 'string') {
        return error.error.detail;
      } else if (Array.isArray(error.error.detail)) {
        return error.error.detail
          .map((err: any) => err.msg || err.message)
          .join(', ');
      }
    }
    return error.error?.message || null;
  }

  private extractValidationErrors(error: HttpErrorResponse): string | null {
    if (error.error?.detail && Array.isArray(error.error.detail)) {
      return error.error.detail
        .map((err: any) => {
          const field =
            err.loc && err.loc.length > 1
              ? err.loc.slice(1).join('.')
              : 'field';
          return `${field}: ${err.msg}`;
        })
        .join(', ');
    }
    return null;
  }

  private getCurrentUserId(): string | undefined {
    // This would typically get the user ID from your auth service
    try {
      const user = localStorage.getItem('current_user');
      return user ? JSON.parse(user).id : undefined;
    } catch {
      return undefined;
    }
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private sendToExternalLogging(logEntry: ErrorLogEntry): void {
    // In production, this would send to your logging service
    // For now, just log to console
    if (logEntry.severity === 'critical' || logEntry.severity === 'high') {
      console.error('Critical/High severity error:', logEntry);
    }
  }
}
