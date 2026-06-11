import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * P3-PERF-01: Mermaid removed from global loading
 * Now loaded on-demand via LibraryLoaderService
 * Impact: ~500KB reduction in initial bundle
 */

// Build canary — confirms which bundle is deployed. Bump on each fix so a stale build
// is obvious in the console. (Cheap; remove once the deploy pipeline is trusted.)
// eslint-disable-next-line no-console
console.log(
  '%c AIO-CANARY-CD-v6-DETECTCHANGES — per-panel detectChanges workaround active ',
  'background:#16a34a;color:#fff;font-size:18px;font-weight:bold;padding:6px 10px;border-radius:6px'
);

bootstrapApplication(AppComponent, appConfig).catch((err) =>
  console.error(err)
);
