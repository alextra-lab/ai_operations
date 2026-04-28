/**
 * SemanticSearchTabComponent
 *
 * Wrapper for Semantic Search component within Query Developer Tools.
 * Integrates with SharedConfigService for cross-tab state management.
 *
 * Related: P4-TOOLS-02, P4-TOOLS-04, ADR-045
 */

import { Component, inject } from '@angular/core';

import { SemanticSearchComponent } from '../../query/semantic-search.component';
import { SharedConfigService } from '../services/shared-config.service';

@Component({
  selector: 'app-semantic-search-tab',
  standalone: true,
  imports: [SemanticSearchComponent],
  template: ` <app-semantic-search></app-semantic-search> `,
  styles: [
    `
      :host {
        display: block;
        height: 100%;
      }
    `,
  ],
})
export class SemanticSearchTabComponent {
  // Inject shared config service (available to child via DI)
  readonly sharedConfig = inject(SharedConfigService);
}
