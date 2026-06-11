import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthService } from '../../../../../core/auth/auth.service';
import { DeveloperTeamsService } from '../../../developer-teams/services/developer-teams.service';
import {
  DeveloperTeamInfo,
  GroupingRoleInfo,
  SYSTEM_ROLES,
} from '../../../role-management/models/role-management.models';
import { GroupingRolesService } from '../../../use-case-role-management/services/grouping-roles.service';
import {
  UpdateUserRolesRequest,
  UserListItem,
  UserRolesResponse,
} from '../../models/user-management.models';
import { UserManagementService } from '../../services/user-management.service';

/**
 * User Edit Dialog Component
 *
 * Dialog for editing existing user details.
 * WCAG 2.1 AA compliant.
 */
@Component({
  selector: 'app-user-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSlideToggleModule,
    MatCheckboxModule,
  ],
  templateUrl: './user-edit-dialog.component.html',
  styleUrls: ['./user-edit-dialog.component.scss'],
})
export class UserEditDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  editForm: FormGroup;
  isSubmitting = false;
  error: string | null = null;

  systemRoles = SYSTEM_ROLES;
  groupingRoles: GroupingRoleInfo[] = [];
  teams: DeveloperTeamInfo[] = [];

  selectedSystemRole: string | null = null;
  selectedGroupingRoles = new Set<string>();
  selectedTeams = new Set<string>();
  initialTeams = new Set<string>();

  isLoading = true;
  canAssignTeams = false;

  constructor(
    private fb: FormBuilder,
    private userService: UserManagementService,
    private dialogRef: MatDialogRef<UserEditDialogComponent>,
    private groupingRolesService: GroupingRolesService,
    private developerTeamsService: DeveloperTeamsService,
    private authService: AuthService,
    @Inject(MAT_DIALOG_DATA) public data: { user: UserListItem }
  ) {
    this.editForm = this.fb.group({
      full_name: [data.user.full_name || '', Validators.required],
      email: [data.user.email || '', Validators.email],
      is_active: [data.user.is_active],
    });
  }

  ngOnInit(): void {
    this.canAssignTeams =
      this.authService.hasRole('use_case_admin') ||
      this.authService.hasRole('admin');
    this.loadRoleData();
  }

  onSubmit(): void {
    if (this.editForm.invalid) {
      return;
    }

    const systemRole = this.selectedSystemRole || 'user';
    const groupingRoles = Array.from(this.selectedGroupingRoles);
    const teams = this.canAssignTeams
      ? Array.from(this.selectedTeams)
      : Array.from(this.initialTeams);

    const roleRequest: UpdateUserRolesRequest = {
      system_roles: [systemRole],
      grouping_roles: groupingRoles,
      teams,
    };

    const updates = this.editForm.value;

    this.isSubmitting = true;
    this.error = null;

    forkJoin([
      this.userService.updateUser(this.data.user.id, updates),
      this.userService.updateUserRoles(this.data.user.id, roleRequest),
    ]).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.dialogRef.close(true);
      },
      error: (err: any) => {
        this.isSubmitting = false;
        this.error = err?.error?.detail || 'Failed to update user';
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
    if (!this.canAssignTeams) {
      return;
    }
    if (checked) {
      this.selectedTeams.add(teamId);
    } else {
      this.selectedTeams.delete(teamId);
    }
  }

  private loadRoleData(): void {
    this.isLoading = true;
    forkJoin({
      groupingRoles: this.groupingRolesService
        .listRoles()
        .pipe(catchError(() => of([] as GroupingRoleInfo[]))),
      teams: this.developerTeamsService
        .listTeams()
        .pipe(catchError(() => of([] as DeveloperTeamInfo[]))),
      userRoles: this.userService
        .getUserRoles(this.data.user.id)
        .pipe(catchError(() => of(null as UserRolesResponse | null))),
    }).subscribe({
      next: ({ groupingRoles, teams, userRoles }) => {
        this.groupingRoles = groupingRoles;
        this.teams = teams;

        if (userRoles) {
          const systemRole =
            userRoles.system_roles?.[0] || this.data.user.role || 'user';
          this.selectedSystemRole = systemRole;

          userRoles.grouping_roles?.forEach((r) =>
            this.selectedGroupingRoles.add(r)
          );
          userRoles.teams?.forEach((t) => {
            this.selectedTeams.add(t);
            this.initialTeams.add(t);
          });
        } else {
          this.selectedSystemRole = this.data.user.role || 'user';
        }
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Failed to load roles';
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }
}
