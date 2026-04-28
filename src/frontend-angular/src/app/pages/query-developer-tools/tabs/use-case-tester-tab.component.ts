/**
 * UseCaseTesterTabComponent
 *
 * Placeholder for Use Case Tester tab.
 * Full implementation planned for P4-TOOLS-05 (Parameter Injection).
 *
 * Related: P4-TOOLS-04, P4-TOOLS-05, ADR-045
 */

import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-use-case-tester-tab',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <div
      class="flex flex-col items-center justify-center
                    p-12 md:p-16 text-center min-h-[400px]
                    text-gray-600
                    placeholder-content"
    >
      <mat-icon
        class="!text-[120px] !w-[120px] !h-[120px]
                             text-gray-400 mb-6
                             placeholder-icon"
        >construction</mat-icon
      >
      <h2 class="m-0 mb-2 text-3xl font-medium text-gray-800">
        Use Case Tester
      </h2>
      <p class="m-0 mb-8 text-lg text-gray-500 italic">Coming in P4-TOOLS-05</p>
      <div
        class="max-w-2xl text-left mt-6 p-6
                        bg-gray-100 rounded-lg
                        feature-list"
      >
        <p class="m-0 mb-4 font-medium text-gray-800">This tab will provide:</p>
        <ul class="m-0 pl-6 space-y-2">
          <li class="leading-relaxed">Test queries within Use Case context</li>
          <li class="leading-relaxed">
            Apply discovered parameters to Use Cases
          </li>
          <li class="leading-relaxed">Clone Use Cases with injected config</li>
          <li class="leading-relaxed">Parameter validation and warnings</li>
          <li class="leading-relaxed">Audit trail for parameter changes</li>
        </ul>
      </div>
    </div>
  `,
  styles: [
    `
      // ====================================================================
      // ADR-012 Compliant Styles - Use Case Tester Placeholder
      // Tailwind: layout, spacing, colors, typography
      // SCSS: Material icon size override only
      // ====================================================================

      // Material icon sizing (large placeholder icon)
      .placeholder-icon {
        font-size: 120px;
        width: 120px;
        height: 120px;
      }

      // ====================================================================
      // Responsive Overrides
      // ====================================================================

      @media (max-width: 768px) {
        .placeholder-icon {
          font-size: 96px;
          width: 96px;
          height: 96px;
        }
      }
    `,
  ],
})
export class UseCaseTesterTabComponent {}
