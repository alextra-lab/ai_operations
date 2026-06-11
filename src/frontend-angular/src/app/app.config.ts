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
    // KNOWN BUG (Angular 22): HTTP responses do not trigger an automatic change-detection
    // tick even when they resolve inside the zone, so data panels stay on "Loading…" until
    // a user event. See docs/development/analysis/angular22-http-change-detection-bug.md.
    // withXhr() + dropping eventCoalescing were tried here and kept (harmless) but did NOT
    // fix it; the actual workaround is per-component cdr.detectChanges() in each panel.
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
      // withXhr() keeps HttpClient on the XMLHttpRequest backend (Angular 22 defaults to
      // fetch). Kept for predictability; it does NOT by itself fix the CD bug noted above.
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
