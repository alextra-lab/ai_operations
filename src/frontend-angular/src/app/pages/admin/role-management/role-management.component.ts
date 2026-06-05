import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { AssignUseCaseDialogComponent } from './components/assign-use-case-dialog/assign-use-case-dialog.component';
import { RoleDetailsDialogComponent } from './components/role-details-dialog/role-details-dialog.component';
import {
  RoleFilters,
  RoleInfo,
  SYSTEM_ROLES,
} from './models/role-management.models';
import { RoleManagementService } from './services/role-management.service';

/**
 * Role Management Component
 *
 * Admin interface for managing role-based use case assignments.
 * Follows ADR-012 Layered Page Layout Pattern.
 * Implements ADR-041 Role-Based Use Case Permissions.
 */
@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatTableModule,
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
  templateUrl: './role-management.component.html',
  styleUrls: ['./role-management.component.scss'],
})
export class RoleManagementComponent implements OnInit {
  roles: RoleInfo[] = [];
  isLoading = false;
  error: string | null = null;

  filters: RoleFilters = {
    search: '',
    include_system: true,
    include_custom: true,
  };

  displayedColumns: string[] = [
    'role_name',
    'display_name',
    'description',
    'type',
    'use_case_count',
    'actions',
  ];

  constructor(
    private roleService: RoleManagementService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadRoles();
  }

  loadRoles(): void {
    this.isLoading = true;
    this.error = null;

    // Fetch system roles dynamically from backend API
    this.roleService.getSystemRoles().subscribe({
      next: (systemRoles) => {
        // Filter roles based on current filters
        this.roles = systemRoles.filter((role) => {
          if (!this.filters.include_system && role.is_system_role) {
            return false;
          }
          if (!this.filters.include_custom && !role.is_system_role) {
            return false;
          }
          if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            return (
              role.role_name.toLowerCase().includes(search) ||
              role.display_name.toLowerCase().includes(search) ||
              role.description.toLowerCase().includes(search)
            );
          }
          return true;
        });

        // Load use case counts for each role
        this.roles.forEach((role) => {
          this.roleService.getRoleUseCases(role.role_name).subscribe({
            next: (response) => {
              role.use_case_count = response.active;
            },
            error: (err) => {
              console.error(
                `Failed to load use cases for role ${role.role_name}:`,
                err
              );
              role.use_case_count = 0;
            },
          });
        });

        this.isLoading = false;
      },
      error: (err) => {
        console.error(
          'Failed to load system roles from API, using fallback:',
          err
        );
        // Fallback to hardcoded SYSTEM_ROLES if API fails
        this.roles = SYSTEM_ROLES.filter((role) => {
          if (!this.filters.include_system && role.is_system_role) {
            return false;
          }
          if (!this.filters.include_custom && !role.is_system_role) {
            return false;
          }
          if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            return (
              role.role_name.toLowerCase().includes(search) ||
              role.display_name.toLowerCase().includes(search) ||
              role.description.toLowerCase().includes(search)
            );
          }
          return true;
        });

        // Load use case counts for each role
        this.roles.forEach((role) => {
          this.roleService.getRoleUseCases(role.role_name).subscribe({
            next: (response) => {
              role.use_case_count = response.active;
            },
            error: (err) => {
              console.error(
                `Failed to load use cases for role ${role.role_name}:`,
                err
              );
              role.use_case_count = 0;
            },
          });
        });

        this.isLoading = false;
      },
    });
  }

  onSearch(): void {
    this.loadRoles();
  }

  onFilterChange(): void {
    this.loadRoles();
  }

  openAssignDialog(role: RoleInfo): void {
    const dialogRef = this.dialog.open(AssignUseCaseDialogComponent, {
      width: '600px',
      data: { roleName: role.role_name },
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result) {
        this.snackBar.open('Use case assigned successfully', 'Close', {
          duration: 3000,
        });
        this.loadRoles();
      }
    });
  }

  openDetailsDialog(role: RoleInfo): void {
    this.dialog.open(RoleDetailsDialogComponent, {
      width: '1000px',
      maxWidth: '95vw',
      data: { role },
    });
  }

  revokeAccess(role: RoleInfo, useCaseId: string): void {
    if (!confirm('Are you sure you want to revoke this use case access?')) {
      return;
    }

    this.roleService
      .revokeUseCaseFromRole(role.role_name, useCaseId)
      .subscribe({
        next: () => {
          this.snackBar.open('Use case access revoked', 'Close', {
            duration: 3000,
          });
          this.loadRoles();
        },
        error: (err) => {
          this.snackBar.open('Failed to revoke use case access', 'Close', {
            duration: 5000,
          });
          console.error('Error revoking use case:', err);
        },
      });
  }

  getRoleTypeLabel(role: RoleInfo): string {
    return role.is_system_role ? 'System' : 'Custom';
  }
}
