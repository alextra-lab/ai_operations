import { CommonModule } from '@angular/common';
import { Component, Inject, OnDestroy, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { interval, Subscription } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import { SessionInfo, UserListItem } from '../../models/user-management.models';
import { UserManagementService } from '../../services/user-management.service';

/**
 * Session Viewer Component
 *
 * Dialog for viewing and managing user sessions.
 * Auto-refreshes every 30 seconds.
 * WCAG 2.1 AA compliant.
 */
@Component({
  selector: 'app-session-viewer',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatTableModule,
    MatTooltipModule,
  ],
  templateUrl: './session-viewer.component.html',
  styleUrls: ['./session-viewer.component.scss'],
})
export class SessionViewerComponent implements OnInit, OnDestroy {
  sessions: SessionInfo[] = [];
  isLoading = false;
  error: string | null = null;
  private refreshSubscription?: Subscription;

  displayedColumns = ['created_at', 'last_activity', 'expires_at', 'actions'];

  constructor(
    private userService: UserManagementService,
    private dialogRef: MatDialogRef<SessionViewerComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { user: UserListItem }
  ) {}

  ngOnInit(): void {
    this.loadSessions();

    // Auto-refresh every 30 seconds
    this.refreshSubscription = interval(30000).subscribe(() => {
      this.loadSessions();
    });
  }

  ngOnDestroy(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  loadSessions(): void {
    this.isLoading = true;
    this.error = null;

    this.userService.getUserSessions(this.data.user.id).subscribe({
      next: (sessions: SessionInfo[]) => {
        this.sessions = sessions;
        this.isLoading = false;
      },
      error: (err: any) => {
        this.error = 'Failed to load sessions';
        this.isLoading = false;
        console.error('Error loading sessions:', err);
      },
    });
  }

  forceLogout(session: SessionInfo): void {
    if (!confirm('Force logout this session?')) {
      return;
    }

    this.userService.forceLogout(this.data.user.id, session.id).subscribe({
      next: () => {
        this.loadSessions();
      },
      error: (err: any) => {
        alert('Failed to revoke session');
        console.error('Error revoking session:', err);
      },
    });
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
