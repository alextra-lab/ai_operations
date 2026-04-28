import { HttpHandlerFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { BYPASS_SECURITY_INTERCEPTOR } from '../auth/http-context-tokens';
import { SecurityMonitoringService } from '../security/security-monitoring.service';
import { SecurityHeadersService } from '../services/security-headers.service';

const SECURITY_HEADERS: Readonly<Record<string, string>> = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'SAMEORIGIN',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy':
    'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
};

/**
 * Enhanced security interceptor that adds security headers to requests
 * and validates security headers in responses.
 */
export function securityInterceptor(
  request: HttpRequest<unknown>,
  next: HttpHandlerFn
) {
  const context = request.context;

  if (context.get(BYPASS_SECURITY_INTERCEPTOR)) {
    return next(request);
  }

  const securityHeadersService = inject(SecurityHeadersService);
  const securityMonitoring = inject(SecurityMonitoringService);

  const dynamicHeaders = securityHeadersService.getDynamicHeaders();
  const hardened = request.clone({
    setHeaders: {
      ...SECURITY_HEADERS,
      ...dynamicHeaders,
    },
  });

  return next(hardened).pipe(
    tap((response) => {
      if (response instanceof HttpResponse) {
        // Only validate security headers for external API calls, not internal ones
        const isExternalApi =
          request.url.startsWith('/api/') &&
          !request.url.includes('/security/events');

        if (isExternalApi) {
          // Validate security headers in response (throttled to avoid spam)
          const validation =
            securityHeadersService.validateSecurityHeaders(response);

          if (!validation.isValid && validation.missingHeaders.length > 0) {
            // Only log if there are critical missing headers
            const criticalHeaders = validation.missingHeaders.filter((header) =>
              [
                'Content-Security-Policy',
                'X-Frame-Options',
                'X-Content-Type-Options',
              ].includes(header)
            );

            if (criticalHeaders.length > 0) {
              securityMonitoring.logSecurityEvent({
                id: securityHeadersService.generateEventId(),
                type: 'MISSING_SECURITY_HEADERS',
                severity: 'medium',
                message: `Missing critical security headers: ${criticalHeaders.join(', ')}`,
                details: {
                  missingHeaders: criticalHeaders,
                  presentHeaders: validation.presentHeaders,
                  score: validation.score,
                  url: request.url,
                },
                timestamp: new Date().toISOString(),
                source: 'interceptor',
              });
            }
          }

          // Validate CSP if present (only for external responses)
          const cspHeader = response.headers.get('Content-Security-Policy');
          if (cspHeader) {
            const cspValidation = securityHeadersService.validateCSP(cspHeader);

            if (!cspValidation.isValid && cspValidation.violations.length > 0) {
              securityMonitoring.logSecurityEvent({
                id: securityHeadersService.generateEventId(),
                type: 'CSP_VIOLATION',
                severity: 'high',
                message: `CSP validation failed: ${cspValidation.violations.join(', ')}`,
                details: {
                  violations: cspValidation.violations,
                  directives: cspValidation.directives,
                  score: cspValidation.score,
                  url: request.url,
                },
                timestamp: new Date().toISOString(),
                source: 'interceptor',
              });
            }
          }
        }
      }
    }),
    catchError((error) => {
      // Only log security-related errors for critical endpoints or 4xx/5xx errors
      const isSecurityCritical =
        request.url.includes('/api/auth/') ||
        request.url.includes('/api/admin/') ||
        request.url.includes('/api/security/');

      const isServerError = error.status >= 400;

      if (isSecurityCritical || (isServerError && error.status >= 500)) {
        securityMonitoring.logSecurityEvent({
          id: securityHeadersService.generateEventId(),
          type: 'HTTP_SECURITY_ERROR',
          severity: error.status >= 500 ? 'high' : 'medium',
          message: `HTTP request failed: ${error.message}`,
          details: {
            url: request.url,
            method: request.method,
            error: error.message,
            status: error.status,
          },
          timestamp: new Date().toISOString(),
          source: 'interceptor',
        });
      }

      return of(error);
    })
  );
}
