import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';

import {
  GroupingRoleInfo,
  SYSTEM_ROLES,
} from '../role-management/models/role-management.models';
import { GroupingRolesService } from './services/grouping-roles.service';
import { LucideAngularModule } from 'lucide-angular';

const ROLE_PATTERN = /^[a-z][a-z0-9_-]{1,49}$/;

@Component({
  selector: 'app-use-case-role-management',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './use-case-role-management.component.html',
  styleUrls: ['./use-case-role-management.component.scss'],
})
export class UseCaseRoleManagementComponent implements OnInit {
  roles: GroupingRoleInfo[] = [];
  isLoading = false;
  isSaving = false;
  error: string | null = null;
  newRoleName = '';

  displayedColumns: string[] = [
    'role_name',
    'user_count',
    'use_case_count',
    'collection_count',
    'actions',
  ];

  constructor(
    private readonly groupingRoles: GroupingRolesService,
    private readonly snackBar: MatSnackBar,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadRoles();
  }

  loadRoles(): void {
    this.isLoading = true;
    this.error = null;
    this.cdr.markForCheck();

    this.groupingRoles.listRoles().subscribe({
      next: (roles) => {
        this.roles = roles.filter(
          (role) => !SYSTEM_ROLES.some((s) => s.role_name === role.role_name)
        );
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load grouping roles', err);
        this.error = 'Failed to load grouping roles';
        this.isLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  createRole(): void {
    const trimmedName = this.newRoleName.trim();

    if (!trimmedName) {
      this.error = 'Role name is required';
      this.cdr.markForCheck();
      return;
    }

    if (!ROLE_PATTERN.test(trimmedName)) {
      this.error =
        'Invalid role name. Use lowercase letters, digits, _ or -, 2-50 chars.';
      this.cdr.markForCheck();
      return;
    }

    if (SYSTEM_ROLES.some((role) => role.role_name === trimmedName)) {
      this.error = 'System role names are reserved';
      this.cdr.markForCheck();
      return;
    }

    this.isSaving = true;
    this.error = null;
    this.cdr.markForCheck();

    this.groupingRoles.createRole(trimmedName).subscribe({
      next: () => {
        this.snackBar.open('Role created', 'Close', { duration: 3000 });
        this.newRoleName = '';
        this.isSaving = false;
        this.loadRoles();
      },
      error: (err) => {
        console.error('Failed to create role', err);
        this.error = 'Failed to create role';
        this.isSaving = false;
        this.cdr.markForCheck();
      },
    });
  }

  deleteRole(role: GroupingRoleInfo): void {
    const confirmed = window.confirm(
      `Delete grouping role "${role.role_name}"? This removes all assignments.`
    );

    if (!confirmed) {
      return;
    }

    this.isSaving = true;
    this.cdr.markForCheck();

    this.groupingRoles.deleteRole(role.role_name).subscribe({
      next: () => {
        this.snackBar.open('Role deleted', 'Close', { duration: 3000 });
        this.isSaving = false;
        this.loadRoles();
      },
      error: (err) => {
        console.error('Failed to delete role', err);
        this.error = 'Failed to delete role';
        this.isSaving = false;
        this.cdr.markForCheck();
      },
    });
  }
}
