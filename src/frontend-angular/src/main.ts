import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * P3-PERF-01: Mermaid removed from global loading
 * Now loaded on-demand via LibraryLoaderService
 * Impact: ~500KB reduction in initial bundle
 */

// eslint-disable-next-line no-console
console.log(
  '%c 🐤🐤🐤  AIO-CANARY-XHR-v3 — HttpClient forced to XHR backend (zone-patched CD)  🐤🐤🐤 ',
  'background:#0ea5e9;color:#fff;font-size:22px;font-weight:bold;padding:8px 12px;border-radius:6px'
);

bootstrapApplication(AppComponent, appConfig).catch((err) =>
  console.error(err)
);
