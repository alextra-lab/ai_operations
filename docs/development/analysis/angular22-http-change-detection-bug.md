# Angular 22 — HTTP responses do not trigger change detection (known bug + workaround)

**Status:** Worked around (per-panel `detectChanges`). Root cause NOT fully understood — flagged for a future deep-dive.
**First observed:** after the design-system reskin (PR #130), which coincided with the Angular **21 → 22** bump.
**Affected:** every data-bound component app-wide — admin panels, dev tools, analytics, documents,
collections, templates, use-cases, and shared dialogs/charts (~64 components patched).

## Symptom

A panel loads data via `HttpClient.subscribe()` and sets `this.isLoading = false`, but the view
stays on **"Loading…"** until the user clicks *anything* (a filter, the page) — then the
already-arrived data paints instantly. The HTTP response is `200` and fast (~60 ms, confirmed in
nginx access logs and DevTools). So the data reaches the component; **automatic change detection
simply does not run after the response.** A DOM click *does* trigger CD (the panel paints on click).
The one panel that always worked is `developer-teams` — it is `OnPush` **and** calls
`cdr.markForCheck()` after its subscribe.

## What was ruled out (evidence-backed)

| Hypothesis | Test | Result |
|---|---|---|
| fetch vs XHR backend | `provideHttpClient(withXhr())` (PR #161) — Network type flipped `fetch`→`xhr` | **Not it** — bug persists on XHR |
| `eventCoalescing` deferring the tick | `provideZoneChangeDetection()` w/o coalescing (PR #162) | **Not it** — bug persists |
| Response resolving outside the zone | Runtime diag interceptor logging `NgZone.isInAngularZone()` per response | **`inAngularZone: true`** for the data request — it IS in the zone |
| Global `ApplicationRef.tick()` in an interceptor `finalize()` | PR #159 | Did **not** repaint |
| Global `NgZone.run(() => {})` in an interceptor `finalize()` | PR #160 | Did **not** repaint |
| OnPush ancestor gating the subtree | grep of `app.component` / `layouts/main-layout` | None — both default CD |
| Existing interceptors escaping the zone | read `auth`/`security`/`error`/`logging` interceptors | Clean RxJS, no `runOutsideAngular`/scheduler/`setTimeout` |
| Custom / Noop NgZone, zoneless provider, duplicate `provideZoneChangeDetection` | grep of `src/` | None found |

## The core unexplained finding

With `eventCoalescing` **off**, the data response resolving **inside** the Angular zone
(`inAngularZone: true`), and **no** OnPush ancestor, an in-zone async (XHR/fetch) completion still
does **not** schedule a change-detection tick — while an in-zone DOM event (click) does. A
per-component `cdr.detectChanges()` in the subscribe callback **does** repaint (proven on
`provider-management` via a deployed canary build).

This points at the Angular 22 change-detection **scheduler** (the zone `onMicrotaskEmpty` →
`ApplicationRef.tick()` wiring, or the v18+ hybrid scheduler) treating async task completions
differently from DOM events — but the exact mechanism was not pinned. A diagnostic also showed
`runOutsideAngular` being called frequently (normal for Angular Material/CDK), which is a possible
but unconfirmed thread.

## Workaround in place

Per-component change detection: each affected component injects
`private readonly cdr = inject(ChangeDetectorRef)` and repaints after its loading flag clears.
Two patterns are used, both **deferred** so CD runs after the *whole* synchronous handler:

- **Subscribe handlers:** after each `this.<loading> = false`, insert
  `queueMicrotask(() => this.cdr.detectChanges())`.
- **`finalize` teardown:** `finalize(() => { this.<loading> = false; this.cdr.detectChanges(); })`
  (the `finalize` callback already runs after the synchronous `next` body, so no extra defer needed).

**Why deferred (the `queueMicrotask`):** an earlier rollout (PR #164) called `detectChanges()`
*synchronously* inside the subscribe handler. On reactive-form panels (e.g. `config-editor`) that fired
CD on the line *before* `buildForm()` ran, so `formControlName` bound to a null control and threw
`TypeError: Cannot read properties of null (reading '_rawValidators')`. Deferring to a microtask runs
CD after the entire handler completes (form built), fixing both the stuck-panel symptom and the
`_rawValidators` regression. Applied app-wide via a one-off codemod; `tsc --noEmit` clean.
(`developer-teams` already did the equivalent with `markForCheck`.)

Also retained but **not** themselves a fix (harmless, kept for predictability):
`provideHttpClient(withXhr())` and `provideZoneChangeDetection()` (no `eventCoalescing`).

## For the future deep-dive

1. Build a minimal repro: fresh Angular 22 standalone app, `provideZoneChangeDetection()`, one
   component doing `HttpClient.get().subscribe(() => this.x = …)` — does the view update without a
   manual tick? If yes, the cause is something this app adds (Material theme, lucide-angular,
   `provideAnimationsAsync`, the service worker, `SafeLucideIconProvider`).
2. Instrument `NgZone.onMicrotaskEmpty` and the `ChangeDetectionScheduler` to confirm whether the
   tick is scheduled-but-skipped or never-scheduled for HTTP task completions.
3. Inspect the `runOutsideAngular` stack traces (the diag interceptor captured them) for a library
   wrapping HttpClient work.
4. Consider migrating to **zoneless** + signals/`markForCheck` as the long-term direction (Angular's
   own trajectory), which would make the workaround unnecessary.

## References

- PRs: #159, #160 (failed global interceptor attempts), #161 (withXhr), #162 (drop eventCoalescing),
  #163 (diagnostics build), plus the per-panel `detectChanges` rollout.
- Code: `src/frontend-angular/src/app/app.config.ts` (comment block), the affected components under
  `pages/admin/`.
- Build canary: `AIO-CANARY-CD-v6-DETECTCHANGES` in `main.ts` confirms the workaround build is live.
