import { provideHttpClient, withInterceptors } from '@angular/common/http';
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
    provideZoneChangeDetection({ eventCoalescing: true }),
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
