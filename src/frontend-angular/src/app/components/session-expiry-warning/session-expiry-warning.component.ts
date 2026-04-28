/**
 * Session expiry warning component (ADR-030).
 *
 * Displays warnings when conversations are approaching expiration.
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { interval, Subscription } from 'rxjs';
import { ExportService } from '../../services/export.service';
import { SessionStorageService } from '../../services/session-storage.service';

@Component({
  selector: 'app-session-expiry-warning',
  standalone: true,
  imports: [CommonModule, MatSnackBarModule, MatButtonModule, MatIconModule],
  template: `
    <div class="session-expiry-container" *ngIf="warningVisible">
      <mat-icon class="warning-icon">warning</mat-icon>
      <span class="warning-text">
        {{ warningMessage }}
      </span>
      <button mat-button (click)="onExport()">
        <mat-icon>download</mat-icon>
        Export
      </button>
      <button mat-icon-button (click)="onDismiss()">
        <mat-icon>close</mat-icon>
      </button>
    </div>
  `,
  styles: [
    `
      .session-expiry-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 4px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        max-width: 500px;
      }

      .warning-icon {
        color: #ff9800;
      }

      .warning-text {
        flex: 1;
        font-size: 14px;
        color: #856404;
      }
    `,
  ],
})
export class SessionExpiryWarningComponent implements OnInit, OnDestroy {
  warningVisible = false;
  warningMessage = '';

  private checkInterval!: Subscription;
  private expiringSessions: any[] = [];

  constructor(
    private sessionStorage: SessionStorageService,
    private exportService: ExportService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    // Check for expiring sessions every 5 minutes
    this.checkInterval = interval(5 * 60 * 1000).subscribe(() => {
      this.checkExpiringSessions();
    });

    // Initial check
    this.checkExpiringSessions();
  }

  ngOnDestroy(): void {
    if (this.checkInterval) {
      this.checkInterval.unsubscribe();
    }
  }

  async checkExpiringSessions(): Promise<void> {
    try {
      this.expiringSessions = await this.sessionStorage.getExpiringSessions();

      if (this.expiringSessions.length > 0) {
        const count = this.expiringSessions.length;
        this.warningMessage =
          count === 1
            ? '1 conversation will expire soon'
            : `${count} conversations will expire soon`;
        this.warningVisible = true;
      } else {
        this.warningVisible = false;
      }
    } catch (error) {
      console.error('[SessionExpiry] Error checking expiring sessions:', error);
    }
  }

  async onExport(): Promise<void> {
    if (this.expiringSessions.length === 0) return;

    try {
      // Export the first expiring session
      const session = this.expiringSessions[0];

      this.exportService.exportAsJson(session.id).subscribe({
        next: (response) => {
          const filename = this.exportService.generateFilename(
            session.title,
            'json'
          );
          this.exportService.downloadExport(response.content, filename, 'json');

          this.snackBar.open('Conversation exported successfully', 'Close', {
            duration: 3000,
          });

          // Recheck after export
          this.checkExpiringSessions();
        },
        error: (error) => {
          console.error('[SessionExpiry] Export failed:', error);
          this.snackBar.open('Failed to export conversation', 'Close', {
            duration: 3000,
          });
        },
      });
    } catch (error) {
      console.error('[SessionExpiry] Error during export:', error);
    }
  }

  onDismiss(): void {
    this.warningVisible = false;
  }
}
