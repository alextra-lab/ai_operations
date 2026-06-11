import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import { PasswordResetDialogComponent } from './user-management/components/password-reset-dialog/password-reset-dialog.component';
import { SessionViewerComponent } from './user-management/components/session-viewer/session-viewer.component';
import { UserCreateDialogComponent } from './user-management/components/user-create-dialog/user-create-dialog.component';
import { UserEditDialogComponent } from './user-management/components/user-edit-dialog/user-edit-dialog.component';
import {
  UserFilters,
  UserListItem,
} from './user-management/models/user-management.models';
import { UserManagementService } from './user-management/services/user-management.service';

/**
 * User Management Component
 *
 * Admin interface for managing users, roles, sessions, and passwords.
 * Follows ADR-012 Layered Page Layout Pattern.
 */
@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './user-management.component.html',
  styleUrls: ['./user-management.component.scss'],
})
export class UserManagementComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  users: UserListItem[] = [];
  totalUsers = 0;
  isLoading = false;
  error: string | null = null;
  userRolesMap: Record<string, string[]> = {};

  filters: UserFilters = {
    limit: 20,
    offset: 0,
    search: '',
    role: '',
    status: '',
  };

  displayedColumns: string[] = [
    'username',
    'full_name',
    'roles',
    'status',
    'last_login',
    'sessions',
    'actions',
  ];

  constructor(
    private userService: UserManagementService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading = true;
    this.error = null;

    this.userService.listUsers(this.filters).subscribe({
      next: (response: any) => {
        this.users = response.items;
        this.totalUsers = response.total;
        this.loadUserRolesForList(response.items);
      },
      error: (err: any) => {
        this.error = 'Failed to load users';
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
        console.error('Error loading users:', err);
      },
    });
  }

  onSearch(searchTerm: string): void {
    this.filters.search = searchTerm;
    this.filters.offset = 0;
    this.loadUsers();
  }

  onFilterChange(): void {
    this.filters.offset = 0;
    this.loadUsers();
  }

  onPageChange(event: any): void {
    this.filters.limit = event.pageSize;
    this.filters.offset = event.pageIndex * event.pageSize;
    this.loadUsers();
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(UserCreateDialogComponent, {
      width: '500px',
      disableClose: false,
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result) {
        this.snackBar.open('User created successfully', 'Close', {
          duration: 3000,
        });
        this.loadUsers();
      }
    });
  }

  openEditDialog(user: UserListItem): void {
    const dialogRef = this.dialog.open(UserEditDialogComponent, {
      width: '500px',
      data: { user },
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result) {
        this.snackBar.open('User updated successfully', 'Close', {
          duration: 3000,
        });
        this.loadUsers();
      }
    });
  }

  openPasswordResetDialog(user: UserListItem): void {
    const dialogRef = this.dialog.open(PasswordResetDialogComponent, {
      width: '500px',
      data: { user },
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result) {
        this.snackBar.open('Password reset successfully', 'Close', {
          duration: 3000,
        });
      }
    });
  }

  openSessionsDialog(user: UserListItem): void {
    this.dialog.open(SessionViewerComponent, {
      width: '700px',
      data: { user },
    });
  }

  deactivateUser(user: UserListItem): void {
    if (
      confirm(
        `Deactivate user ${user.username}? This will revoke all active sessions.`
      )
    ) {
      this.userService.deactivateUser(user.id).subscribe({
        next: () => {
          this.snackBar.open('User deactivated successfully', 'Close', {
            duration: 3000,
          });
          this.loadUsers();
        },
        error: (err: any) => {
          console.error('Error deactivating user:', err);
          this.snackBar.open('Failed to deactivate user', 'Close', {
            duration: 5000,
          });
        },
      });
    }
  }

  private loadUserRolesForList(users: UserListItem[]): void {
    if (!users.length) {
      this.userRolesMap = {};
      this.isLoading = false;
      queueMicrotask(() => this.cdr.detectChanges());
      return;
    }

    const requests = users.map((user) =>
      this.userService.getUserRoles(user.id).pipe(
        map((roles) => ({
          id: user.id,
          roles: [
            ...(roles.system_roles || []),
            ...(roles.grouping_roles || []),
            ...(roles.teams || []),
          ],
        })),
        catchError(() =>
          of({
            id: user.id,
            roles: user.role ? [user.role] : [],
          })
        )
      )
    );

    forkJoin(requests).subscribe({
      next: (roleResults) => {
        this.userRolesMap = roleResults.reduce<Record<string, string[]>>(
          (acc, item) => {
            acc[item.id] = item.roles;
            return acc;
          },
          {}
        );
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
      error: () => {
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
    });
  }
}
