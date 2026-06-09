/**
 * Test Result Viewer Component
 *
 * T6-F4: Displays test execution results with JSON viewer.
 * Shows status, duration, and formatted response/error data.
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  inject,
  Input,
  signal,
  WritableSignal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { TestExecutionResult } from '../../../../../api/services/tool-testing.service';
import {
  formatDuration,
  TestHistoryEntry,
} from '../../models/tool-testing.models';

@Component({
  selector: 'app-test-result-viewer',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './test-result-viewer.component.html',
  styleUrls: ['./test-result-viewer.component.scss'],
})
export class TestResultViewerComponent {
  @Input({ required: true }) result!: TestExecutionResult;
  @Input() historyEntry: TestHistoryEntry | null = null;

  isCollapsed: WritableSignal<boolean> = signal(false);

  private readonly snackBar = inject(MatSnackBar);

  /**
   * Get status display text
   */
  get statusText(): string {
    return this.result.success ? 'Success' : 'Failed';
  }

  /**
   * Get status icon
   */
  get statusIcon(): string {
    return this.result.success ? 'circle-check' : 'circle-alert';
  }

  /**
   * Get status CSS class
   */
  get statusClass(): string {
    return this.result.success ? 'success' : 'error';
  }

  /**
   * Format duration for display
   */
  get formattedDuration(): string {
    return formatDuration(this.result.duration_ms);
  }

  /**
   * Get formatted result JSON
   */
  get formattedResult(): string {
    if (this.result.result === undefined || this.result.result === null) {
      return 'null';
    }
    try {
      return JSON.stringify(this.result.result, null, 2);
    } catch {
      return String(this.result.result);
    }
  }

  /**
   * Get timestamp if from history
   */
  get timestamp(): string | null {
    if (!this.historyEntry) {
      return null;
    }
    return this.historyEntry.timestamp.toLocaleString();
  }

  /**
   * Toggle collapsed state
   */
  toggleCollapsed(): void {
    this.isCollapsed.set(!this.isCollapsed());
  }

  /**
   * Copy result to clipboard
   */
  async copyResult(): Promise<void> {
    const textToCopy = this.result.success
      ? this.formattedResult
      : this.result.error || '';

    try {
      await navigator.clipboard.writeText(textToCopy);
      this.snackBar.open('Copied to clipboard', 'Close', { duration: 2000 });
    } catch {
      this.snackBar.open('Failed to copy', 'Close', { duration: 3000 });
    }
  }

  /**
   * Copy full result object to clipboard
   */
  async copyFullResult(): Promise<void> {
    try {
      const fullResult = JSON.stringify(this.result, null, 2);
      await navigator.clipboard.writeText(fullResult);
      this.snackBar.open('Full result copied', 'Close', { duration: 2000 });
    } catch {
      this.snackBar.open('Failed to copy', 'Close', { duration: 3000 });
    }
  }
}
