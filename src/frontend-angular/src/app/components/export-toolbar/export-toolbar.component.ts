import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { finalize, take } from 'rxjs/operators';

import { ExportService } from '../../services/export.service';
import { LucideAngularModule } from 'lucide-angular';

/**
 * Export Toolbar Component
 *
 * Provides export controls for conversations/sessions (ADR-031).
 * Supports markdown/JSON export and summary generation.
 *
 * Follows ADR-012 (Hybrid CSS Strategy):
 * - Material for UI primitives (buttons, menu, tooltips)
 * - Tailwind for layout and spacing
 * - Component SCSS for custom styling
 *
 * Follows WCAG 2.1 AA accessibility guidelines
 */
@Component({
  selector: 'app-export-toolbar',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatDividerModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="export-toolbar flex items-center gap-2">
      <!-- Export Menu -->
      <button
        mat-icon-button
        [matMenuTriggerFor]="exportMenu"
        [disabled]="!sessionId || isExporting"
        matTooltip="Export conversation"
        aria-label="Export conversation menu"
      >
        <lucide-icon name="download"></lucide-icon>
      </button>

      <mat-menu #exportMenu="matMenu">
        <!-- Copy Markdown -->
        <button
          mat-menu-item
          (click)="copyMarkdown()"
          aria-label="Copy conversation as markdown"
        >
          <lucide-icon name="copy"></lucide-icon>
          <span>Copy as Markdown</span>
        </button>

        <!-- Download Markdown -->
        <button
          mat-menu-item
          (click)="downloadMarkdown()"
          aria-label="Download conversation as markdown file"
        >
          <lucide-icon name="download"></lucide-icon>
          <span>Download Markdown</span>
        </button>

        <!-- Download JSON -->
        <button
          mat-menu-item
          (click)="downloadJson()"
          aria-label="Download conversation as JSON file"
        >
          <lucide-icon name="braces"></lucide-icon>
          <span>Download JSON</span>
        </button>

        <mat-divider></mat-divider>

        <!-- Generate Summary -->
        <button
          mat-menu-item
          [matMenuTriggerFor]="summaryMenu"
          aria-label="Generate summary submenu"
        >
          <lucide-icon name="file-text"></lucide-icon>
          <span>Generate Summary</span>
        </button>
      </mat-menu>

      <!-- Summary Type Menu -->
      <mat-menu #summaryMenu="matMenu">
        <button
          mat-menu-item
          (click)="generateSummary('executive')"
          aria-label="Generate executive summary"
        >
          <lucide-icon name="building-2"></lucide-icon>
          <span>Executive Summary</span>
        </button>
        <button
          mat-menu-item
          (click)="generateSummary('technical')"
          aria-label="Generate technical summary"
        >
          <lucide-icon name="hard-hat"></lucide-icon>
          <span>Technical Summary</span>
        </button>
        <button
          mat-menu-item
          (click)="generateSummary('brief')"
          aria-label="Generate brief summary"
        >
          <lucide-icon name="sticky-note"></lucide-icon>
          <span>Brief Summary</span>
        </button>
      </mat-menu>

      <!-- Loading Indicator -->
      <mat-spinner
        *ngIf="isExporting"
        diameter="20"
        aria-label="Export in progress"
      >
      </mat-spinner>

      <!-- Session Info (optional) -->
      <span
        *ngIf="showSessionInfo && sessionTitle"
        class="session-info text-sm text-gray-600"
      >
        {{ sessionTitle }}
      </span>
    </div>
  `,
  styles: [
    `
      .export-toolbar {
        padding: 8px;
        background-color: #f5f5f5;
        border-radius: 4px;
      }

      .session-info {
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      /* Ensure proper focus indicators for accessibility */
      button:focus-visible {
        outline: 2px solid var(--mat-primary);
        outline-offset: 2px;
      }

      mat-spinner {
        display: inline-block;
      }
    `,
  ],
})
export class ExportToolbarComponent {
  @Input() sessionId: string | null = null;
  @Input() sessionTitle: string | null = null;
  @Input() showSessionInfo = false;

  @Output() exportComplete = new EventEmitter<{
    format: string;
    filename: string;
  }>();
  @Output() summaryGenerated = new EventEmitter<{
    summary: string;
    type: string;
  }>();

  isExporting = false;

  constructor(
    private exportService: ExportService,
    private snackBar: MatSnackBar
  ) {}

  /**
   * Copy conversation as Markdown to clipboard
   */
  copyMarkdown(): void {
    if (!this.sessionId) {
      this.showError('No session selected');
      return;
    }

    this.isExporting = true;

    this.exportService
      .exportAsMarkdown(this.sessionId)
      .pipe(
        take(1),
        finalize(() => (this.isExporting = false))
      )
      .subscribe({
        next: (response) => {
          this.copyToClipboard(response.content);
          this.snackBar.open('Conversation copied to clipboard', 'Close', {
            duration: 3000,
          });
          this.exportComplete.emit({
            format: 'markdown',
            filename: 'clipboard',
          });
        },
        error: (error) => {
          this.showError(
            'Failed to copy markdown: ' + (error.message || 'Unknown error')
          );
        },
      });
  }

  /**
   * Download conversation as Markdown file
   */
  downloadMarkdown(): void {
    if (!this.sessionId) {
      this.showError('No session selected');
      return;
    }

    this.isExporting = true;

    this.exportService
      .exportAsMarkdown(this.sessionId)
      .pipe(
        take(1),
        finalize(() => (this.isExporting = false))
      )
      .subscribe({
        next: (response) => {
          const filename = this.exportService.generateFilename(
            this.sessionTitle || 'conversation',
            'markdown'
          );
          this.exportService.downloadExport(
            response.content,
            filename,
            'markdown'
          );
          this.snackBar.open('Markdown downloaded successfully', 'Close', {
            duration: 3000,
          });
          this.exportComplete.emit({ format: 'markdown', filename });
        },
        error: (error) => {
          this.showError(
            'Failed to download markdown: ' + (error.message || 'Unknown error')
          );
        },
      });
  }

  /**
   * Download conversation as JSON file
   */
  downloadJson(): void {
    if (!this.sessionId) {
      this.showError('No session selected');
      return;
    }

    this.isExporting = true;

    this.exportService
      .exportAsJson(this.sessionId)
      .pipe(
        take(1),
        finalize(() => (this.isExporting = false))
      )
      .subscribe({
        next: (response) => {
          const filename = this.exportService.generateFilename(
            this.sessionTitle || 'conversation',
            'json'
          );
          this.exportService.downloadExport(response.content, filename, 'json');
          this.snackBar.open('JSON downloaded successfully', 'Close', {
            duration: 3000,
          });
          this.exportComplete.emit({ format: 'json', filename });
        },
        error: (error) => {
          this.showError(
            'Failed to download JSON: ' + (error.message || 'Unknown error')
          );
        },
      });
  }

  /**
   * Generate summary of conversation
   */
  generateSummary(type: 'executive' | 'technical' | 'brief'): void {
    if (!this.sessionId) {
      this.showError('No session selected');
      return;
    }

    this.isExporting = true;

    this.exportService
      .generateSummary(this.sessionId, type)
      .pipe(
        take(1),
        finalize(() => (this.isExporting = false))
      )
      .subscribe({
        next: (response) => {
          this.snackBar.open(
            `${type.charAt(0).toUpperCase() + type.slice(1)} summary generated`,
            'Close',
            {
              duration: 3000,
            }
          );
          this.summaryGenerated.emit({ summary: response.summary, type });
        },
        error: (error) => {
          this.showError(
            `Failed to generate ${type} summary: ` +
              (error.message || 'Unknown error')
          );
        },
      });
  }

  /**
   * Copy text to clipboard using Clipboard API
   */
  private copyToClipboard(text: string): void {
    if (navigator.clipboard && window.isSecureContext) {
      // Use modern Clipboard API
      navigator.clipboard.writeText(text).catch((err) => {
        console.error('Failed to copy to clipboard:', err);
        this.fallbackCopyToClipboard(text);
      });
    } else {
      // Fallback for older browsers or non-secure contexts
      this.fallbackCopyToClipboard(text);
    }
  }

  /**
   * Fallback clipboard copy method for older browsers
   */
  private fallbackCopyToClipboard(text: string): void {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }

    document.body.removeChild(textArea);
  }

  /**
   * Show error message
   */
  private showError(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }
}
