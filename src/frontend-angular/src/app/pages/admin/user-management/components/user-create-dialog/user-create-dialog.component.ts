import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { debounceTime, distinctUntilChanged, forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { DeveloperTeamsService } from '../../../developer-teams/services/developer-teams.service';
import {
  DeveloperTeamInfo,
  GroupingRoleInfo,
  SYSTEM_ROLES,
} from '../../../role-management/models/role-management.models';
import { GroupingRolesService } from '../../../use-case-role-management/services/grouping-roles.service';
import { UpdateUserRolesRequest } from '../../models/user-management.models';
import { UserManagementService } from '../../services/user-management.service';

/**
 * User Create Dialog Component
 *
 * Dialog for creating new users with validation.
 * WCAG 2.1 AA compliant with proper labels and error messages.
 */
@Component({
  selector: 'app-user-create-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
  ],
  templateUrl: './user-create-dialog.component.html',
  styleUrls: ['./user-create-dialog.component.scss'],
})
export class UserCreateDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  createForm: FormGroup;
  isSubmitting = false;
  error: string | null = null;

  systemRoles = SYSTEM_ROLES;
  groupingRoles: GroupingRoleInfo[] = [];
  teams: DeveloperTeamInfo[] = [];

  selectedSystemRole = 'user';
  selectedGroupingRoles = new Set<string>();
  selectedTeams = new Set<string>();

  constructor(
    private fb: FormBuilder,
    private userService: UserManagementService,
    private dialogRef: MatDialogRef<UserCreateDialogComponent>,
    private groupingRolesService: GroupingRolesService,
    private developerTeamsService: DeveloperTeamsService
  ) {
    this.createForm = this.fb.group(
      {
        username: [
          '',
          [
            Validators.required,
            Validators.minLength(3),
            Validators.maxLength(50),
          ],
        ],
        full_name: ['', Validators.required],
        email: ['', [Validators.email]],
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required],
      },
      { validators: this.passwordMatchValidator }
    );
  }

  ngOnInit(): void {
    // Username availability check (debounced)
    this.createForm
      .get('username')
      ?.valueChanges.pipe(debounceTime(500), distinctUntilChanged())
      .subscribe(() => {
        // TODO: Add username uniqueness check API call
      });

    this.loadRoleData();
  }

  passwordMatchValidator(group: FormGroup): Record<string, boolean> | null {
    const password = group.get('password')?.value;
    const confirm = group.get('confirmPassword')?.value;
    return password === confirm ? null : { passwordMismatch: true };
  }

  getPasswordStrength(): string {
    const password = this.createForm.get('password')?.value || '';
    if (password.length === 0) return '';
    if (password.length < 8) return 'weak';
    if (
      password.length >= 12 &&
      /[A-Z]/.test(password) &&
      /[0-9]/.test(password) &&
      /[^A-Za-z0-9]/.test(password)
    ) {
      return 'strong';
    }
    return 'medium';
  }

  onSubmit(): void {
    if (this.createForm.invalid) {
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const formValue = this.createForm.value;
    const request = {
      username: formValue.username,
      password: formValue.password,
      full_name: formValue.full_name,
      email: formValue.email || undefined,
      role: this.selectedSystemRole || 'user',
    };

    this.userService.createUser(request).subscribe({
      next: (created: any) => {
        const newUserId = created?.id;
        if (!newUserId) {
          this.isSubmitting = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.error = 'User created but id not returned';
          return;
        }

        const roleRequest: UpdateUserRolesRequest = {
          system_roles: [this.selectedSystemRole || 'user'],
          grouping_roles: Array.from(this.selectedGroupingRoles),
          teams: Array.from(this.selectedTeams),
        };

        this.userService.updateUserRoles(newUserId, roleRequest).subscribe({
          next: () => {
            this.isSubmitting = false;
            queueMicrotask(() => this.cdr.detectChanges());
            this.dialogRef.close(true);
          },
          error: (err: any) => {
            this.isSubmitting = false;
            queueMicrotask(() => this.cdr.detectChanges());
            this.error =
              err?.error?.detail || 'User created but role update failed';
          },
        });
      },
      error: (err: any) => {
        this.isSubmitting = false;
        queueMicrotask(() => this.cdr.detectChanges());
        this.error = err.error?.detail || 'Failed to create user';
      },
    });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }

  onSystemRoleChange(roleName: string, checked: boolean): void {
    if (checked) {
      this.selectedSystemRole = roleName;
      return;
    }

    // When unchecking the currently selected role, reset to default 'user'
    if (this.selectedSystemRole === roleName) {
      this.selectedSystemRole = 'user';
    }
  }

  toggleGroupingRole(roleName: string, checked: boolean): void {
    if (checked) {
      this.selectedGroupingRoles.add(roleName);
    } else {
      this.selectedGroupingRoles.delete(roleName);
    }
  }

  toggleTeam(teamId: string, checked: boolean): void {
    if (checked) {
      this.selectedTeams.add(teamId);
    } else {
      this.selectedTeams.delete(teamId);
    }
  }

  private loadRoleData(): void {
    forkJoin({
      groupingRoles: this.groupingRolesService
        .listRoles()
        .pipe(catchError(() => of([] as GroupingRoleInfo[]))),
      teams: this.developerTeamsService
        .listTeams()
        .pipe(catchError(() => of([] as DeveloperTeamInfo[]))),
    }).subscribe({
      next: ({ groupingRoles, teams }) => {
        this.groupingRoles = groupingRoles;
        this.teams = teams;
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Failed to load roles';
      },
    });
  }
}
