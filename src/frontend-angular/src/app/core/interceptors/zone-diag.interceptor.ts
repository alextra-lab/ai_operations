/*
 * Temporary runtime diagnostics for AIO-CANARY-CD-v5-COALESCE-OFF.
 *
 * Healthy console output:
 * - [AIO-DIAG] Bootstrap zone diagnostics ... isNoopNgZone: false, xhrSendPatched: true
 * - [AIO-DIAG] HTTP response zone ... inAngularZone: true, insideRunOutsideAngular: false
 * - No "[AIO-DIAG] Zone miss — forced tick" warnings.
 *
 * Broken console output:
 * - [AIO-DIAG] HTTP response zone ... inAngularZone: false, insideRunOutsideAngular: true
 * - [AIO-DIAG] Zone miss — forced tick
 *
 * If broken output persists, the next diagnostic step is to inspect the
 * "[AIO-DIAG] runOutsideAngular called" stack traces and find the caller that
 * schedules HttpClient work outside Angular's zone.
 */
import {
  HttpInterceptorFn,
  HttpResponse,
} from '@angular/common/http';
import { ApplicationRef, inject, NgZone } from '@angular/core';
import { tap } from 'rxjs/operators';

type ZoneLike = {
  current?: {
    name?: string;
    get?: (key: string) => unknown;
  };
};

type XhrPrototypeLike = {
  send: XMLHttpRequest['send'];
};

let diagnosticsInstalled = false;
let runOutsideAngularCallCount = 0;

export function installZoneDiagnostics(): void {
  const ngZone = inject(NgZone);

  if (!diagnosticsInstalled) {
    diagnosticsInstalled = true;
    patchRunOutsideAngular(ngZone);
  }

  const ngZoneConstructorName = ngZone.constructor?.name ?? '(unknown)';
  const xhrSendSource = getXhrSendSource();
  const xhrSendPatched =
    xhrSendSource.includes('__zone_symbol__') ||
    xhrSendSource.includes('__zone');

  console.log('[AIO-DIAG] Bootstrap zone diagnostics', {
    ngZoneConstructorName,
    isNgZoneInstance: ngZone instanceof NgZone,
    isNoopNgZone: ngZoneConstructorName === 'NoopNgZone',
    xhrSendPatched,
    xhrSendSourcePreview: xhrSendSource.slice(0, 160),
    currentZone: getZoneContext(),
    runOutsideAngularCallCount,
  });
}

export const zoneDiagInterceptor: HttpInterceptorFn = (req, next) => {
  const appRef = inject(ApplicationRef);

  return next(req).pipe(
    tap((event) => {
      if (!(event instanceof HttpResponse)) {
        return;
      }

      const inAngularZone = NgZone.isInAngularZone();
      const zoneContext = getZoneContext();
      const insideRunOutsideAngular = !inAngularZone;

      console.log('[AIO-DIAG] HTTP response zone', {
        method: req.method,
        url: req.urlWithParams,
        status: event.status,
        inAngularZone,
        insideRunOutsideAngular,
        zoneContext,
        runOutsideAngularCallCount,
      });

      if (!inAngularZone) {
        console.warn('[AIO-DIAG] Zone miss — forced tick', {
          method: req.method,
          url: req.urlWithParams,
          zoneContext,
        });
        appRef.tick();
      }
    })
  );
};

function patchRunOutsideAngular(ngZone: NgZone): void {
  const originalRunOutsideAngular = ngZone.runOutsideAngular.bind(ngZone);

  ngZone.runOutsideAngular = ((fn: (...args: any[]) => unknown) => {
    runOutsideAngularCallCount++;
    console.warn('[AIO-DIAG] runOutsideAngular called', {
      count: runOutsideAngularCallCount,
      currentZone: getZoneContext(),
      stack: new Error().stack,
    });

    return originalRunOutsideAngular(fn);
  }) as NgZone['runOutsideAngular'];
}

function getZoneContext() {
  const zoneGlobal = (globalThis as { Zone?: ZoneLike }).Zone;
  const currentZone = zoneGlobal?.current;

  return {
    zoneName: currentZone?.name ?? '(no Zone.current)',
    isAngularZoneProperty: currentZone?.get?.('isAngularZone') ?? false,
  };
}

function getXhrSendSource(): string {
  if (typeof XMLHttpRequest === 'undefined') {
    return '(XMLHttpRequest unavailable)';
  }

  const xhrPrototype = XMLHttpRequest.prototype as XhrPrototypeLike;
  return xhrPrototype.send.toString();
}
