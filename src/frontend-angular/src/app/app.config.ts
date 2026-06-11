import {
  provideHttpClient,
  withInterceptors,
  withXhr,
} from '@angular/common/http';
import {
  ApplicationConfig,
  importProvidersFrom,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';
import { LUCIDE_ICONS, LucideAngularModule } from 'lucide-angular';

import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { environment } from '../environments/environment';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { loggingInterceptor } from './core/interceptors/logging.interceptor';
import { securityInterceptor } from './core/interceptors/security.interceptor';
import { APP_ICONS } from './shared/icons/lucide-icons';
import { SafeLucideIconProvider } from './shared/icons/safe-lucide-icon-provider';

export const appConfig: ApplicationConfig = {
  providers: [
    // Keep zone-driven change detection immediate for HttpClient's XHR load
    // events. In Angular 22 + zone.js 0.16, XHR completion is delivered through
    // a patched XMLHttpRequestEventTarget "load" eventTask; coalescing that task
    // can leave data-bound admin panels stale until the next user event.
    provideZoneChangeDetection(),
    importProvidersFrom(LucideAngularModule.pick(APP_ICONS)),
    // Safety net: registered icons resolve via the provider above; any
    // unregistered name falls through to this provider and renders a neutral
    // fallback glyph instead of throwing and aborting change detection.
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new SafeLucideIconProvider(APP_ICONS),
    },
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient(
      // Angular 22 defaults HttpClient to the fetch backend, whose responses resolve
      // OUTSIDE the Angular zone — so zone.js never schedules change detection after an
      // HTTP call and data-bound views stay stale until a user event (every admin panel
      // stuck on "Loading…" until you click). withXhr() puts HttpClient back on the
      // zone-patched XMLHttpRequest backend, restoring automatic change detection.
      withXhr(),
      withInterceptors([
        authInterceptor,
        securityInterceptor,
        errorInterceptor,
        loggingInterceptor,
      ])
    ),
    provideServiceWorker('ngsw-worker.js', {
      enabled: environment.production,
      registrationStrategy: 'registerWhenStable:30000',
    }),
    {
      provide: 'API_BASE_URL',
      useValue: environment.apiBaseUrl,
    },
  ],
};
