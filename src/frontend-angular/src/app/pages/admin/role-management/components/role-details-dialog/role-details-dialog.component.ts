import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import {
  RoleInfo,
  RoleUseCaseAssignment,
} from '../../models/role-management.models';
import { RoleManagementService } from '../../services/role-management.service';

/**
 * Role Details Dialog Component
 *
 * Displays all use case assignments for a role with revoke capability.
 * WCAG 2.1 AA compliant.
 */
@Component({
  selector: 'app-role-details-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatTableModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  templateUrl: './role-details-dialog.component.html',
  styleUrls: ['./role-details-dialog.component.scss'],
})
export class RoleDetailsDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  assignments: RoleUseCaseAssignment[] = [];
  isLoading = false;
  error: string | null = null;

  displayedColumns: string[] = [
    'use_case_name',
    'granted_at',
    'expires_at',
    'status',
    'actions',
  ];

  constructor(
    private roleService: RoleManagementService,
    private dialogRef: MatDialogRef<RoleDetailsDialogComponent>,
    private snackBar: MatSnackBar,
    @Inject(MAT_DIALOG_DATA) public data: { role: RoleInfo }
  ) {}

  ngOnInit(): void {
    this.loadAssignments();
  }

  loadAssignments(): void {
    this.isLoading = true;
    this.error = null;

    this.roleService.getRoleUseCases(this.data.role.role_name, true).subscribe({
      next: (response) => {
        this.assignments = response.assignments;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = 'Failed to load use case assignments';
        this.isLoading = false;
        this.cdr.detectChanges();
        console.error('Error loading assignments:', err);
      },
    });
  }

  revokeAssignment(assignment: RoleUseCaseAssignment): void {
    if (!confirm(`Revoke access to "${assignment.use_case_name}"?`)) {
      return;
    }

    this.roleService
      .revokeUseCaseFromRole(this.data.role.role_name, assignment.use_case_id)
      .subscribe({
        next: () => {
          this.snackBar.open('Use case access revoked', 'Close', {
            duration: 3000,
          });
          this.loadAssignments();
        },
        error: (err) => {
          this.snackBar.open('Failed to revoke access', 'Close', {
            duration: 5000,
          });
          console.error('Error revoking assignment:', err);
        },
      });
  }

  isExpired(assignment: RoleUseCaseAssignment): boolean {
    if (!assignment.expires_at) return false;
    return new Date(assignment.expires_at) < new Date();
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
