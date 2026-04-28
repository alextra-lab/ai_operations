/**
 * RagQaTabComponent
 *
 * Wrapper for RAG Q&A component within Query Developer Tools.
 * Integrates with SharedConfigService for cross-tab state management.
 *
 * Related: P4-TOOLS-03, P4-TOOLS-04, ADR-045
 */

import { Component, inject } from '@angular/core';

import { RagQaComponent } from '../../query/rag-qa.component';
import { SharedConfigService } from '../services/shared-config.service';

@Component({
  selector: 'app-rag-qa-tab',
  standalone: true,
  imports: [RagQaComponent],
  template: ` <app-rag-qa></app-rag-qa> `,
  styles: [
    `
      :host {
        display: block;
        height: 100%;
      }
    `,
  ],
})
export class RagQaTabComponent {
  // Inject shared config service (available to child via DI)
  readonly sharedConfig = inject(SharedConfigService);
}
