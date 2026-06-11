import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * P3-PERF-01: Mermaid removed from global loading
 * Now loaded on-demand via LibraryLoaderService
 * Impact: ~500KB reduction in initial bundle
 */

bootstrapApplication(AppComponent, appConfig).catch((err) =>
  console.error(err)
);
