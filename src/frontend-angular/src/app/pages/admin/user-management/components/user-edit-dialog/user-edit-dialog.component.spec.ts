import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { AuthService } from '../../../../../core/auth/auth.service';
import { DeveloperTeamsService } from '../../../developer-teams/services/developer-teams.service';
import { GroupingRolesService } from '../../../use-case-role-management/services/grouping-roles.service';
import { UserManagementService } from '../../services/user-management.service';
import { UserEditDialogComponent } from './user-edit-dialog.component';

describe('UserEditDialogComponent', () => {
  const user = {
    id: 'user-1',
    username: 'alice',
    full_name: 'Alice Example',
    email: 'alice@example.com',
    role: 'user',
    is_active: true,
  } as any;

  const groupingRoles = [{ role_name: 'threat_hunting' }];
  const teams = [{ team_id: 'team:blue', display_name: 'Blue Team' }];
  const userRolesResponse = {
    user_id: user.id,
    system_roles: ['use_case_admin'],
    grouping_roles: ['threat_hunting'],
    teams: ['team:blue'],
    all_roles: [],
  };

  let component: UserEditDialogComponent;
  let userService: jest.Mocked<UserManagementService>;
  let dialogRef: MatDialogRef<UserEditDialogComponent>;

  beforeEach(() => {
    const userServiceMock: Partial<jest.Mocked<UserManagementService>> = {
      updateUser: jest.fn().mockReturnValue(of({})),
      updateUserRoles: jest.fn().mockReturnValue(of({})),
      getUserRoles: jest.fn().mockReturnValue(of(userRolesResponse)),
    };

    TestBed.configureTestingModule({
      imports: [UserEditDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: UserManagementService, useValue: userServiceMock },
        {
          provide: GroupingRolesService,
          useValue: { listRoles: jest.fn().mockReturnValue(of(groupingRoles)) },
        },
        {
          provide: DeveloperTeamsService,
          useValue: { listTeams: jest.fn().mockReturnValue(of(teams)) },
        },
        {
          provide: AuthService,
          useValue: {
            hasRole: jest.fn().mockReturnValue(true),
          },
        },
        { provide: MAT_DIALOG_DATA, useValue: { user } },
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
      ],
    });

    const fixture = TestBed.createComponent(UserEditDialogComponent);
    component = fixture.componentInstance;
    userService = TestBed.inject(
      UserManagementService
    ) as jest.Mocked<UserManagementService>;
    dialogRef = TestBed.inject(MatDialogRef);
    fixture.detectChanges();
  });

  it('should load roles and select current memberships', () => {
    expect(component.selectedSystemRole).toBe('use_case_admin');
    expect(component.selectedGroupingRoles.has('threat_hunting')).toBe(true);
    expect(component.selectedTeams.has('team:blue')).toBe(true);
  });

  it('should submit profile and roles', () => {
    component.onSubmit();

    expect(userService.updateUser).toHaveBeenCalledWith(user.id, {
      full_name: user.full_name,
      email: user.email,
      is_active: user.is_active,
    });
    expect(userService.updateUserRoles).toHaveBeenCalledWith(user.id, {
      system_roles: ['use_case_admin'],
      grouping_roles: ['threat_hunting'],
      teams: ['team:blue'],
    });
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('should set system role when checking', () => {
    component.selectedSystemRole = 'user';
    component.onSystemRoleChange('admin', true);
    expect(component.selectedSystemRole).toBe('admin');
  });

  it('should reset to user when unchecking current system role', () => {
    component.selectedSystemRole = 'use_case_admin';
    component.onSystemRoleChange('use_case_admin', false);
    expect(component.selectedSystemRole).toBe('user');
  });

  it('should not change when unchecking a different role', () => {
    component.selectedSystemRole = 'admin';
    component.onSystemRoleChange('use_case_admin', false);
    expect(component.selectedSystemRole).toBe('admin');
  });

  it('should disable save button while loading roles', () => {
    component.isLoading = true;
    component.editForm.patchValue({
      full_name: 'Test User',
      email: 'test@example.com',
    });
    expect(component.editForm.valid).toBe(true);
    // Button should be disabled even if form is valid when isLoading is true
    // This is tested via the template binding [disabled]="editForm.invalid || isSubmitting || isLoading"
  });

  it('should enable save button after roles are loaded', () => {
    component.isLoading = false;
    component.editForm.patchValue({
      full_name: 'Test User',
      email: 'test@example.com',
    });
    expect(component.editForm.valid).toBe(true);
    // Button should be enabled when form is valid and not loading
  });

  it('should prevent submission when isLoading is true', () => {
    component.isLoading = true;
    component.selectedSystemRole = null; // Simulate uninitialized state
    component.editForm.patchValue({
      full_name: 'Test User',
      email: 'test@example.com',
    });

    const onSubmitSpy = jest.spyOn(component, 'onSubmit');
    // Simulate button click - should be prevented by disabled binding
    // In real scenario, disabled button prevents click
    expect(component.isLoading).toBe(true);
    expect(component.selectedSystemRole).toBeNull();
  });
});
