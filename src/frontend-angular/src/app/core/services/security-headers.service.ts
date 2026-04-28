import { HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';

const HEADER_REQUEST_ID = 'X-Request-ID';
const HEADER_CLIENT_TIMESTAMP = 'X-Client-Timestamp';

/**
 * Enhanced security headers service with validation capabilities.
 * Provides client-side security header validation and CSP policy management.
 */
@Injectable({ providedIn: 'root' })
export class SecurityHeadersService {
  private readonly expectedHeaders = new Set([
    'Strict-Transport-Security',
    'X-Content-Type-Options',
    'X-Frame-Options',
    'Referrer-Policy',
    'X-XSS-Protection',
    'Permissions-Policy',
    'Content-Security-Policy',
  ]);

  /**
   * Gets dynamic security headers for outbound requests.
   */
  getDynamicHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};

    headers[HEADER_REQUEST_ID] = this.generateRequestId();
    headers[HEADER_CLIENT_TIMESTAMP] = this.generateTimestamp();
    headers['X-Client-Version'] = this.getClientVersion();

    return headers;
  }

  /**
   * Validates that all required security headers are present in the response.
   */
  validateSecurityHeaders(
    response: HttpResponse<any>
  ): SecurityHeaderValidation {
    const missingHeaders: string[] = [];
    const presentHeaders: Record<string, string> = {};

    this.expectedHeaders.forEach((header) => {
      const value = response.headers.get(header);
      if (value) {
        presentHeaders[header] = value;
      } else {
        missingHeaders.push(header);
      }
    });

    return {
      isValid: missingHeaders.length === 0,
      missingHeaders,
      presentHeaders,
      score:
        ((this.expectedHeaders.size - missingHeaders.length) /
          this.expectedHeaders.size) *
        100,
    };
  }

  /**
   * Validates Content Security Policy configuration.
   */
  validateCSP(cspHeader: string): CSPValidation {
    const violations: string[] = [];
    const directives = this.parseCSPDirectives(cspHeader);

    // Check for required directives
    const requiredDirectives = ['default-src', 'script-src', 'style-src'];
    requiredDirectives.forEach((directive) => {
      if (!directives[directive]) {
        violations.push(`Missing required directive: ${directive}`);
      }
    });

    // Check for unsafe practices
    if (directives['script-src']?.includes("'unsafe-inline'")) {
      violations.push("CSP contains 'unsafe-inline' in script-src");
    }

    if (directives['style-src']?.includes("'unsafe-inline'")) {
      violations.push("CSP contains 'unsafe-inline' in style-src");
    }

    // Check for report-uri or report-to
    if (!directives['report-uri'] && !directives['report-to']) {
      violations.push('CSP missing report-uri or report-to directive');
    }

    return {
      isValid: violations.length === 0,
      violations,
      directives,
      score: Math.max(0, 100 - violations.length * 20),
    };
  }

  /**
   * Reports CSP violations to the backend.
   */
  reportViolation(violation: CSPViolation): void {
    // Send violation report to backend
    fetch('/api/security/csp-report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(violation),
    }).catch((error) => {
      console.error('Failed to report CSP violation:', error);
    });
  }

  /**
   * Sets up CSP violation reporting.
   */
  setupCSPReporting(): void {
    // Listen for CSP violations
    document.addEventListener('securitypolicyviolation', (event) => {
      const violation: CSPViolation = {
        documentUri: event.documentURI,
        violatedDirective: event.violatedDirective,
        blockedUri: event.blockedURI,
        effectiveDirective: event.effectiveDirective,
        originalPolicy: event.originalPolicy,
        referrer: event.referrer,
        sourceFile: event.sourceFile,
        lineNumber: event.lineNumber,
        columnNumber: event.columnNumber,
        statusCode: event.statusCode,
        timestamp: new Date().toISOString(),
      };

      this.reportViolation(violation);
    });
  }

  private parseCSPDirectives(cspHeader: string): Record<string, string> {
    const directives: Record<string, string> = {};
    const parts = cspHeader.split(';');

    parts.forEach((part) => {
      const trimmed = part.trim();
      if (trimmed) {
        const [directive, ...values] = trimmed.split(/\s+/);
        if (directive && values.length > 0) {
          directives[directive] = values.join(' ');
        }
      }
    });

    return directives;
  }

  private generateRequestId(): string {
    const globalCrypto = (globalThis as { crypto?: Crypto }).crypto;

    if (typeof globalCrypto?.randomUUID === 'function') {
      try {
        return globalCrypto.randomUUID();
      } catch {
        // Fall back to manual ID generation below.
      }
    }

    const random = Math.random().toString(16).slice(2, 10);
    const timestamp = Date.now().toString(16);
    return `${timestamp}-${random}`;
  }

  private generateTimestamp(): string {
    return Date.now().toString();
  }

  private getClientVersion(): string {
    return '1.0.0'; // This should come from package.json or build info
  }

  /**
   * Generates a unique event ID for security events.
   */
  generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export interface SecurityHeaderValidation {
  isValid: boolean;
  missingHeaders: string[];
  presentHeaders: Record<string, string>;
  score: number;
}

export interface CSPValidation {
  isValid: boolean;
  violations: string[];
  directives: Record<string, string>;
  score: number;
}

export interface CSPViolation {
  documentUri: string;
  violatedDirective: string;
  blockedUri: string;
  effectiveDirective: string;
  originalPolicy: string;
  referrer: string;
  sourceFile: string;
  lineNumber: number;
  columnNumber: number;
  statusCode: number;
  timestamp: string;
}
