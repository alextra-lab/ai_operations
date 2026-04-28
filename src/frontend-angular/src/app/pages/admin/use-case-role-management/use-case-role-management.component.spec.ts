import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { GroupingRoleInfo } from '../role-management/models/role-management.models';
import { GroupingRolesService } from './services/grouping-roles.service';
import { UseCaseRoleManagementComponent } from './use-case-role-management.component';

describe('UseCaseRoleManagementComponent', () => {
  let fixture: ComponentFixture<UseCaseRoleManagementComponent>;
  let component: UseCaseRoleManagementComponent;
  let service: jest.Mocked<GroupingRolesService>;
  let snackBar: jest.Mocked<MatSnackBar>;

  const mockRoles: GroupingRoleInfo[] = [
    {
      role_name: 'threat_hunting',
      user_count: 1,
      use_case_count: 2,
      collection_count: 0,
    },
  ];

  beforeEach(async () => {
    service = {
      listRoles: jest.fn().mockReturnValue(of(mockRoles)),
      createRole: jest.fn().mockReturnValue(of({})),
      deleteRole: jest.fn().mockReturnValue(of({})),
    } as unknown as jest.Mocked<GroupingRolesService>;

    snackBar = {
      open: jest.fn(),
    } as unknown as jest.Mocked<MatSnackBar>;

    await TestBed.configureTestingModule({
      imports: [
        UseCaseRoleManagementComponent,
        FormsModule,
        MatSnackBarModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: GroupingRolesService, useValue: service },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseRoleManagementComponent);
    component = fixture.componentInstance;
  });

  it('should load roles on init', () => {
    fixture.detectChanges();

    expect(service.listRoles).toHaveBeenCalled();
    expect(component.roles.length).toBe(1);
    expect(component.roles[0].role_name).toBe('threat_hunting');
  });

  it('should set error when loading fails', () => {
    service.listRoles.mockReturnValue(throwError(() => new Error('fail')));

    fixture.detectChanges();

    expect(component.error).toBe('Failed to load grouping roles');
    expect(component.isLoading).toBe(false);
  });

  it('should validate role name before create', () => {
    component.newRoleName = 'Invalid Name';
    fixture.detectChanges();

    component.createRole();

    expect(component.error).toContain('Invalid role name');
    expect(service.createRole).not.toHaveBeenCalled();
  });

  it('should create role when valid', () => {
    service.listRoles.mockReturnValue(of([]));
    service.createRole.mockReturnValue(of({}));

    fixture.detectChanges();

    component.newRoleName = 'threat_hunting';
    component.createRole();

    expect(service.createRole).toHaveBeenCalledWith('threat_hunting');
  });

  it('should delete role', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    service.listRoles.mockReturnValue(of([]));
    service.deleteRole.mockReturnValue(of({}));

    fixture.detectChanges();

    component.deleteRole({
      role_name: 'threat_hunting',
      user_count: 0,
      use_case_count: 0,
      collection_count: 0,
    });

    expect(service.deleteRole).toHaveBeenCalledWith('threat_hunting');
  });
});
