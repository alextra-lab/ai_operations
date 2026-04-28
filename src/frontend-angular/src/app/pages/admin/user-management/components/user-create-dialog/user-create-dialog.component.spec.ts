import { TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';

import { DeveloperTeamsService } from '../../../developer-teams/services/developer-teams.service';
import { GroupingRolesService } from '../../../use-case-role-management/services/grouping-roles.service';
import { UserManagementService } from '../../services/user-management.service';
import { UserCreateDialogComponent } from './user-create-dialog.component';

describe('UserCreateDialogComponent', () => {
  const groupingRoles = [{ role_name: 'threat_hunting' }];
  const teams = [{ team_id: 'team:red', display_name: 'Red Team' }];

  let component: UserCreateDialogComponent;
  let userService: jest.Mocked<UserManagementService>;
  let dialogRef: MatDialogRef<UserCreateDialogComponent>;

  beforeEach(() => {
    const userServiceMock: Partial<jest.Mocked<UserManagementService>> = {
      createUser: jest
        .fn()
        .mockReturnValue(of({ id: 'new-user', role: 'user' })),
      updateUserRoles: jest.fn().mockReturnValue(of({})),
    };

    TestBed.configureTestingModule({
      imports: [UserCreateDialogComponent, NoopAnimationsModule],
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
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
      ],
    });

    const fixture = TestBed.createComponent(UserCreateDialogComponent);
    component = fixture.componentInstance;
    userService = TestBed.inject(
      UserManagementService
    ) as jest.Mocked<UserManagementService>;
    dialogRef = TestBed.inject(MatDialogRef);
    fixture.detectChanges();
  });

  it('should default system role to user', () => {
    expect(component.selectedSystemRole).toBe('user');
  });

  it('should create user and assign roles', () => {
    component.createForm.patchValue({
      username: 'newuser',
      full_name: 'New User',
      password: 'StrongPass123!',
      confirmPassword: 'StrongPass123!',
    });
    component.toggleGroupingRole('threat_hunting', true);
    component.toggleTeam('team:red', true);

    component.onSubmit();

    expect(userService.createUser).toHaveBeenCalled();
    expect(userService.updateUserRoles).toHaveBeenCalledWith('new-user', {
      system_roles: ['user'],
      grouping_roles: ['threat_hunting'],
      teams: ['team:red'],
    });
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('should set system role when checking', () => {
    component.selectedSystemRole = 'user';
    component.onSystemRoleChange('admin', true);
    expect(component.selectedSystemRole).toBe('admin');
  });

  it('should reset to user when unchecking current system role', () => {
    component.selectedSystemRole = 'admin';
    component.onSystemRoleChange('admin', false);
    expect(component.selectedSystemRole).toBe('user');
  });

  it('should not change when unchecking a different role', () => {
    component.selectedSystemRole = 'use_case_admin';
    component.onSystemRoleChange('admin', false);
    expect(component.selectedSystemRole).toBe('use_case_admin');
  });
});
