import {
  HttpHeaders,
  HttpInterceptorFn,
} from '@angular/common/http';
import { tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';

const MAX_BODY_CHARS = 2000;

export const loggingInterceptor: HttpInterceptorFn = (req, next) => {
  const startTime = Date.now();
  const requestId = generateRequestId();
  const safeUrl = req.url.split('?')[0];

  // Add request ID to headers for tracking
  const modifiedRequest = req.clone({
    headers: req.headers.set('X-Request-ID', requestId),
  });

  const requestMeta: Record<string, unknown> = {};
  if (environment.verboseLogging) {
    requestMeta['headers'] = sanitizeHeaders(modifiedRequest.headers);
    requestMeta['body'] = sanitizeBody(modifiedRequest.body);
  }
  console.log(
    `[${requestId}] ${req.method} ${safeUrl}`,
    requestMeta
  );

  return next(modifiedRequest).pipe(
    tap({
      next: (event) => {
        if (event.type === 4) {
          // HttpResponse event type
          const duration = Date.now() - startTime;
          const responseMeta: Record<string, unknown> = {
            status: event.status,
            statusText: event.statusText,
          };
          if (environment.verboseLogging) {
            responseMeta['headers'] = sanitizeHeaders(event.headers);
            responseMeta['body'] = sanitizeBody(event.body);
          }
          console.log(
            `[${requestId}] Response received in ${duration}ms`,
            responseMeta
          );
        }
      },
      error: (error) => {
        const duration = Date.now() - startTime;
        const errorUrl = error.url
          ? error.url.split('?')[0]
          : safeUrl;
        console.error(
          `[${requestId}] Request failed after ${duration}ms`,
          {
            status: error.status,
            statusText: error.statusText,
            url: errorUrl,
          }
        );
      },
    })
  );
};

function generateRequestId(): string {
  const randomId = Math.random().toString(36).substr(2, 9);
  return `req_${Date.now()}_${randomId}`;
}

function sanitizeHeaders(headers: HttpHeaders): Record<string, string> {
  const sanitized: Record<string, string> = {};
  headers.keys().forEach((key) => {
    if (!isSensitiveHeader(key)) {
      const value = headers.get(key);
      if (value) {
        sanitized[key] = value;
      }
    }
  });
  return sanitized;
}

function sanitizeBody(body: unknown): unknown {
  if (!body) {
    return body;
  }

  if (typeof body === 'string') {
    if (body.includes('=')) {
      const params = new URLSearchParams(body);
      const sanitizedParams: string[] = [];
      params.forEach((value, key) => {
        if (isSensitiveField(key)) {
          sanitizedParams.push(`${key}=[REDACTED]`);
        } else {
          sanitizedParams.push(`${key}=${value}`);
        }
      });
      return truncateString(sanitizedParams.join('&'));
    }
    return truncateString(body);
  }

  if (Array.isArray(body)) {
    return { arrayLength: body.length };
  }

  if (typeof body === 'object') {
    const sanitized: Record<string, unknown> = {
      ...(body as object),
    };
    const sensitiveFields = [
      'password',
      'token',
      'secret',
      'key',
      'authorization',
      'refresh_token',
      'access_token',
    ];
    sensitiveFields.forEach((field) => {
      if (field in sanitized) {
        sanitized[field] = '[REDACTED]';
      }
    });
    return sanitized;
  }

  return body;
}

function truncateString(value: string): string {
  if (value.length <= MAX_BODY_CHARS) {
    return value;
  }
  const preview = value.slice(0, MAX_BODY_CHARS);
  return `${preview}...[truncated]`;
}

function isSensitiveField(fieldName: string): boolean {
  const sensitiveFields = [
    'password',
    'token',
    'secret',
    'key',
    'authorization',
    'refresh_token',
    'access_token',
  ];
  return sensitiveFields.some((field) =>
    fieldName.toLowerCase().includes(
      field.toLowerCase()
    )
  );
}

function isSensitiveHeader(headerName: string): boolean {
  const sensitiveHeaders = [
    'authorization',
    'x-api-key',
    'cookie',
  ];
  return sensitiveHeaders.some((sensitive) =>
    headerName.toLowerCase().includes(
      sensitive.toLowerCase()
    )
  );
}
