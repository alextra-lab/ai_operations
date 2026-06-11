import { HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { ApplicationRef, inject } from '@angular/core';
import { finalize } from 'rxjs/operators';

// Logged once, loudly, so we can confirm at a glance that THIS build is running and
// the interceptor is actually wired in.
let canaryLogged = false;

/**
 * Run one change-detection pass after every HTTP response.
 *
 * Angular 22's HttpClient uses the **fetch** backend by default, and fetch responses
 * resolve **outside** the Angular zone — so zone.js never schedules change detection
 * after an HTTP call. The data arrives, but the view stays stale until some unrelated
 * user event triggers a tick (the "panel stuck on Loading… until you click" symptom
 * seen across every data-bound admin panel).
 *
 * Calling `ApplicationRef.tick()` in `finalize()` — i.e. once the response has been
 * delivered to the subscriber — repaints the affected views. The try/catch guards the
 * rare case where a change-detection cycle is already in progress.
 */
export function changeDetectionInterceptor(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) {
  const appRef = inject(ApplicationRef);

  if (!canaryLogged) {
    canaryLogged = true;
    // eslint-disable-next-line no-console
    console.log(
      '%c 🐤🐤🐤  AIO-CANARY-CDFIX-20260611 — change-detection interceptor ACTIVE  🐤🐤🐤 ',
      'background:#7c3aed;color:#fff;font-size:22px;font-weight:bold;padding:8px 12px;border-radius:6px'
    );
  }

  return next(req).pipe(
    finalize(() => {
      try {
        appRef.tick();
      } catch {
        // A change-detection cycle is already running; nothing to do.
      }
    })
  );
}
