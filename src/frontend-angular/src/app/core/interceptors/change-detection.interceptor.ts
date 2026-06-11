import { HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { inject, NgZone } from '@angular/core';
import { finalize } from 'rxjs/operators';

// Logged once, loudly, so we can confirm at a glance that THIS build is running and
// the interceptor is actually wired in. v2 (NGZONE) vs the earlier ApplicationRef.tick().
let canaryLogged = false;

/**
 * Trigger Angular change detection after every HTTP response.
 *
 * Angular 22's HttpClient uses the **fetch** backend by default, and fetch responses
 * resolve **outside** the Angular zone — so zone.js never schedules change detection
 * after an HTTP call. Data arrives, but the view stays stale until some unrelated user
 * event triggers a tick (the "panel stuck on Loading… until you click" symptom).
 *
 * A user *click* already repaints these panels, which proves the zone's normal change
 * detection is healthy — it's simply never fired for the out-of-zone fetch response.
 * So we re-enter the zone with `NgZone.run()` in `finalize()` (after the response has
 * reached the subscriber), which schedules exactly that same change-detection pass.
 *
 * (An earlier attempt used `ApplicationRef.tick()`, but a forced full-tree tick can
 * throw if any single component errors mid-render; re-entering the zone uses the same
 * resilient path as a click.)
 */
export function changeDetectionInterceptor(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) {
  const ngZone = inject(NgZone);

  if (!canaryLogged) {
    canaryLogged = true;
    // eslint-disable-next-line no-console
    console.log(
      '%c 🐤🐤🐤  AIO-CANARY-CDFIX-v2-NGZONE — change-detection interceptor ACTIVE  🐤🐤🐤 ',
      'background:#16a34a;color:#fff;font-size:22px;font-weight:bold;padding:8px 12px;border-radius:6px'
    );
  }

  return next(req).pipe(
    finalize(() => {
      // Re-enter the Angular zone → schedules the standard (click-equivalent) CD pass.
      ngZone.run(() => {});
    })
  );
}
