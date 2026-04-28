/**
 * QueryDeveloperToolsComponent
 *
 * Unified interface for query testing and tuning tools.
 *
 * Features:
 * - Three tabs: Semantic Search, RAG Q&A, Use Case Tester
 * - Shared configuration state across tabs
 * - Tab state persistence to localStorage
 * - Lazy loading of tab content
 * - Layered page layout following ADR-012
 *
 * Related: P4-TOOLS-04, ADR-045, ADR-012
 */

import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTabChangeEvent, MatTabsModule } from '@angular/material/tabs';
import { Router } from '@angular/router';

import { QueryConfig } from '../../api/models/query-config.models';
import {
  UseCaseSelectorDialogComponent,
  UseCaseSelectorDialogData
} from './components/use-case-selector-dialog/use-case-selector-dialog.component';
import { SharedConfigService } from './services/shared-config.service';
import { RagQaTabComponent } from './tabs/rag-qa-tab.component';
import { SemanticSearchTabComponent } from './tabs/semantic-search-tab.component';
import { UseCaseTesterTabComponent } from './tabs/use-case-tester-tab.component';

@Component({
  selector: 'app-query-developer-tools',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    MatMenuModule,
    MatTabsModule,
    SemanticSearchTabComponent,
    RagQaTabComponent,
    UseCaseTesterTabComponent,
  ],
  providers: [SharedConfigService],
  template: `
    <!-- Page Container - LAYERED_PAGE_LAYOUT_PATTERN compliant -->
    <div class="page-container">
      <!-- Layer 2: Page Header + Tabs (NEVER SCROLLS) -->
      <div class="page-header-section">
        <!-- Page Title - December 2025 Standard -->
        <div class="page-title">
          <h1>
            <mat-icon>science</mat-icon>
            Query Developer Tools
          </h1>
          <p class="subtitle">
            Test, tune, and optimize query configurations
          </p>
        </div>

        <!-- Material Tabs (part of Layer 2) -->
        <mat-tab-group
          [(selectedIndex)]="activeTab"
          (selectedTabChange)="onTabChange($event)"
          class="dev-tools-tabs"
          animationDuration="300ms"
        >
          <!-- Tab 1: Semantic Search -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">search</mat-icon>
              Semantic Search
            </ng-template>
            <ng-template matTabContent>
              <app-semantic-search-tab></app-semantic-search-tab>
            </ng-template>
          </mat-tab>

          <!-- Tab 2: RAG Q&A -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">quiz</mat-icon>
              RAG Q&A
            </ng-template>
            <ng-template matTabContent>
              <app-rag-qa-tab></app-rag-qa-tab>
            </ng-template>
          </mat-tab>

          <!-- Tab 3: Use Case Tester -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">construction</mat-icon>
              Use Case Tester
            </ng-template>
            <ng-template matTabContent>
              <app-use-case-tester-tab></app-use-case-tester-tab>
            </ng-template>
          </mat-tab>
        </mat-tab-group>
      </div>

      <!-- Layer 4: Page Footer (NEVER SCROLLS) - Apply to Use Case -->
      <div class="page-footer">
        <button
          mat-raised-button
          [matMenuTriggerFor]="applyMenu"
          [disabled]="!hasValidConfig()"
          color="accent"
          aria-label="Apply parameters to use case"
        >
          <mat-icon class="mr-2">check_circle</mat-icon>
          Apply to Use Case
        </button>

        <!-- Apply Menu -->
        <mat-menu #applyMenu="matMenu">
          <button mat-menu-item (click)="openUseCaseSelector('update')">
            <mat-icon>edit</mat-icon>
            <span>Update Existing Draft</span>
          </button>
          <button mat-menu-item (click)="openUseCaseSelector('clone')">
            <mat-icon>content_copy</mat-icon>
            <span>Clone Published & Apply</span>
          </button>
          <mat-divider></mat-divider>
          <button mat-menu-item (click)="createNewUseCase()">
            <mat-icon>add_circle</mat-icon>
            <span>Create New Use Case</span>
          </button>
        </mat-menu>
      </div>
    </div>
  `,
  styles: [
    `
      // ====================================================================
      // LAYERED_PAGE_LAYOUT_PATTERN + ADR-012 Compliant Styles
      // December 2025 Controls Container Standard
      // ====================================================================

      // Layer 1: Page Container (CRITICAL: overflow hidden, fixed height)
      .page-container {
        display: flex;
        flex-direction: column;
        height: calc(100vh - 200px);
        margin: -24px -32px;
        padding: 0;
        overflow: hidden;
        background: #fafafa;
      }

      // Layer 2: Page Header + Tabs (NEVER SCROLLS)
      .page-header-section {
        flex: 0 0 auto;
        z-index: 100;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);

        .page-title {
          padding: 16px 24px 12px 24px;

          h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            height: 36px;

            mat-icon {
              font-size: 28px;
              width: 28px;
              height: 28px;
              color: #1976d2;
            }
          }

          .subtitle {
            margin: 4px 0 0 0;
            color: #666;
            font-size: 13px;
          }
        }
      }

      // Layer 4: Page Footer (NEVER SCROLLS)
      .page-footer {
        flex: 0 0 auto;
        z-index: 90;
        background: white;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.08);
        padding: 12px 24px;
        display: flex;
        justify-content: flex-end;
        align-items: center;
      }

      // ====================================================================
      // Material Tabs Overrides (::ng-deep required for Material internals)
      // ====================================================================

      ::ng-deep .dev-tools-tabs {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 0;

        // Tab labels background and padding
        .mat-mdc-tab-labels {
          padding: 0 24px;
          background: white;
        }

        // Tab sizing
        .mat-mdc-tab {
          min-width: 160px;

          .tab-icon {
            margin-right: 8px;
            vertical-align: middle;
            font-size: 20px;
            width: 20px;
            height: 20px;
          }
        }

        // Tab body wrapper - takes remaining space (Layer 3)
        .mat-mdc-tab-body-wrapper {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow: hidden;
        }

        .mat-mdc-tab-body {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
        }

        .mat-mdc-tab-body-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow-y: auto;
          overflow-x: hidden;
        }
      }

      // ====================================================================
      // Apply Menu Styling (::ng-deep for Material menu)
      // ====================================================================

      ::ng-deep .mat-mdc-menu-panel {
        min-width: 250px;

        .mat-mdc-menu-item {
          mat-icon {
            margin-right: 12px;
            color: var(--mat-sys-on-surface-variant, #757575);
            transition: color 0.2s ease-in-out;
          }

          &:hover mat-icon {
            color: var(--mat-sys-primary, #1976d2);
          }
        }
      }

      // ====================================================================
      // Responsive Overrides
      // ====================================================================

      @media (max-width: 768px) {
        .page-container {
          height: calc(100vh - 150px);
          margin: -16px;
        }

        .page-header-section {
          .page-title {
            padding: 12px 16px 8px 16px;

            h1 {
              font-size: 20px;
              height: 32px;

              mat-icon {
                font-size: 24px;
                width: 24px;
                height: 24px;
              }
            }

            .subtitle {
              font-size: 12px;
            }
          }
        }

        .page-footer {
          padding: 12px 16px;
        }

        ::ng-deep .dev-tools-tabs {
          .mat-mdc-tab-labels {
            padding: 0 16px;
          }

          .mat-mdc-tab {
            min-width: 120px;
            font-size: 13px;

            .tab-icon {
              font-size: 18px;
              width: 18px;
              height: 18px;
            }
          }
        }
      }

      // ====================================================================
      // Accessibility: Respect reduced motion preference
      // ====================================================================

      @media (prefers-reduced-motion: reduce) {
        .page-header-section,
        .page-footer,
        ::ng-deep .mat-mdc-menu-item mat-icon {
          transition: none;
        }
      }
    `,
  ],
})
export class QueryDeveloperToolsComponent implements OnInit {
  activeTab = 0;

  constructor(
    private readonly sharedConfigService: SharedConfigService,
    private readonly dialog: MatDialog,
    private readonly router: Router
  ) { }

  ngOnInit(): void {
    // Load saved tab preference from localStorage
    this.activeTab = this.sharedConfigService.loadActiveTab();
  }

  onTabChange(event: MatTabChangeEvent): void {
    // Persist tab selection to localStorage
    this.sharedConfigService.saveActiveTab(event.index);
  }

  /**
   * Check if current configuration has valid parameters
   */
  hasValidConfig(): boolean {
    const config = this.sharedConfigService.getCurrentConfig();

    // Must have at least LLM model selected
    if (!config.llm_model) {
      return false;
    }

    // Must have some meaningful configuration
    return !!(
      config.sampling ||
      config.rag?.vector_collections?.length ||
      config.rag?.top_k
    );
  }

  /**
   * Get current configuration for parameter injection
   */
  private getCurrentConfig(): Partial<QueryConfig> {
    return this.sharedConfigService.getCurrentConfig();
  }

  /**
   * Open Use Case selector dialog
   */
  openUseCaseSelector(mode: 'update' | 'clone'): void {
    const dialogData: UseCaseSelectorDialogData = {
      mode,
      discoveredParams: this.getCurrentConfig(),
    };

    const dialogRef = this.dialog.open(UseCaseSelectorDialogComponent, {
      width: '700px',
      maxHeight: '90vh',
      data: dialogData,
      disableClose: false,
      autoFocus: true,
      restoreFocus: true,
    });
  }

  /**
   * Create new Use Case with pre-filled parameters
   */
  createNewUseCase(): void {
    const config = this.getCurrentConfig();

    // Navigate to wizard with pre-filled parameters
    this.router.navigate(['/dev/use-cases/new'], {
      queryParams: {
        prefill: btoa(
          JSON.stringify({
            config,
            source: 'query_developer_tools',
          })
        ),
      },
    });
  }
}
