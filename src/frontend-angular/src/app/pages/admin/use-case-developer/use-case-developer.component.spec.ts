import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  flush,
} from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  UseCaseListResponse,
  UseCaseResponse,
} from '../../../api/models/use-case-management.models';
import { UseCaseManagementService } from '../../../api/services/use-case-management.service';
import { UserProfile } from '../../../core/auth/auth.models';
import { AuthService } from '../../../core/auth/auth.service';
import { UserManagementService } from '../user-management/services/user-management.service';
import { UseCaseDeveloperComponent } from './use-case-developer.component';

describe('UseCaseDeveloperComponent', () => {
  let component: UseCaseDeveloperComponent;
  let fixture: ComponentFixture<UseCaseDeveloperComponent>;
  let userManagementService: jest.Mocked<UserManagementService>;
  let router: jest.Mocked<Router>;

  const currentUser: UserProfile = {
    id: 'user-1',
    username: 'alice',
    full_name: 'Alice Example',
    roles: ['use_case_admin'],
  };

  const userRolesResponse = {
    user_id: 'user-1',
    system_roles: ['use_case_admin'],
    grouping_roles: [],
    teams: ['team:red'],
    all_roles: [],
  };

  const draftUseCases: UseCaseResponse[] = [
    {
      id: '1',
      use_case_id: 'uc-1',
      name: 'My Draft',
      description: '',
      category: '',
      intent_type: 'QUERY',
      version: 1,
      lifecycle_state: 'draft',
      is_active: false,
      config_json: {},
      metadata_json: {},
      created_at: '',
      updated_at: '2025-12-09T00:00:00Z',
      created_by_user_id: 'user-1',
      team_id: 'team:red',
    },
    {
      id: '2',
      use_case_id: 'uc-2',
      name: 'Team Draft',
      description: '',
      category: '',
      intent_type: 'QUERY',
      version: 1,
      lifecycle_state: 'draft',
      is_active: false,
      config_json: {},
      metadata_json: {},
      created_at: '',
      updated_at: '2025-12-08T00:00:00Z',
      created_by_user_id: 'user-2',
      team_id: 'team:blue',
    },
  ];

  const reviewUseCases: UseCaseResponse[] = [
    {
      id: '3',
      use_case_id: 'uc-3',
      name: 'Review Item',
      description: '',
      category: '',
      intent_type: 'QUERY',
      version: 1,
      lifecycle_state: 'review',
      is_active: false,
      config_json: {},
      metadata_json: {},
      created_at: '',
      updated_at: '2025-12-07T00:00:00Z',
    },
  ];

  const publishedUseCases: UseCaseResponse[] = [
    {
      id: '4',
      use_case_id: 'uc-4',
      name: 'Published Item',
      description: '',
      category: '',
      intent_type: 'QUERY',
      version: 1,
      lifecycle_state: 'published',
      is_active: true,
      config_json: {},
      metadata_json: {},
      created_at: '',
      updated_at: '2025-12-06T00:00:00Z',
    },
  ];

  beforeEach(async () => {
    const useCaseServiceMock: Partial<jest.Mocked<UseCaseManagementService>> = {
      listUseCases: jest.fn().mockImplementation((args) => {
        if (args.lifecycle_state === 'draft') {
          const response: UseCaseListResponse = {
            use_cases: draftUseCases,
          };
          return of(response);
        }
        if (args.lifecycle_state === 'review') {
          return of({ use_cases: reviewUseCases });
        }
        return of({ use_cases: publishedUseCases });
      }),
    };

    const userManagementServiceMock: Partial<
      jest.Mocked<UserManagementService>
    > = {
      getUserRoles: jest.fn().mockReturnValue(of(userRolesResponse)),
    };

    const routerMock = {
      navigate: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [UseCaseDeveloperComponent, NoopAnimationsModule],
      providers: [
        { provide: UseCaseManagementService, useValue: useCaseServiceMock },
        {
          provide: AuthService,
          useValue: {
            getCurrentUser: jest.fn().mockReturnValue(of(currentUser)),
          },
        },
        {
          provide: UserManagementService,
          useValue: userManagementServiceMock,
        },
        { provide: Router, useValue: routerMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseDeveloperComponent);
    component = fixture.componentInstance;
    userManagementService = TestBed.inject(
      UserManagementService
    ) as jest.Mocked<UserManagementService>;
    router = TestBed.inject(Router) as jest.Mocked<Router>;
  });

  it('should split drafts into my drafts and team drafts', () => {
    // Manually set up user teams before loading
    component.user = currentUser;
    component.userTeams = ['team:red'];
    component.hasTeams = true;

    // Simulate the draft response handling
    const response: UseCaseListResponse = {
      use_cases: draftUseCases,
    };
    component['handleDrafts'](response);

    expect(component.myDrafts.data.length).toBe(1);
    // Team drafts should only include drafts from user's teams (team:red)
    // uc-2 has team:blue, which user doesn't belong to, so it should be filtered out
    expect(component.teamDrafts.data.length).toBe(0);
    expect(component.userTeams).toEqual(['team:red']);
    expect(component.hasTeams).toBe(true);
  });

  it('should load user teams from RBAC V2 API', fakeAsync(() => {
    component.user = currentUser;
    // Mock the service call
    const getUserRolesSpy = jest.spyOn(userManagementService, 'getUserRoles');
    getUserRolesSpy.mockReturnValue(of(userRolesResponse));

    component['loadUserTeams']('user-1');
    flush(); // Flush all pending microtasks and timers

    // Verify the service was called
    expect(userManagementService.getUserRoles).toHaveBeenCalledWith('user-1');

    // The state should be updated after the observable completes
    expect(component.userTeams).toEqual(['team:red']);
    expect(component.hasTeams).toBe(true);
  }));

  it('should hide team drafts tab when user has no teams', fakeAsync(() => {
    const noTeamsResponse = {
      ...userRolesResponse,
      teams: [],
    };
    (userManagementService.getUserRoles as jest.Mock).mockReturnValueOnce(
      of(noTeamsResponse)
    );

    component.user = currentUser;
    component['loadUserTeams']('user-1');
    flush(); // Flush all pending microtasks and timers

    expect(component.hasTeams).toBe(false);
    expect(component.userTeams).toEqual([]);
  }));

  it('should filter team drafts to only show drafts from user teams', () => {
    // First, ensure user teams are loaded
    component.user = currentUser;
    component.userTeams = ['team:red'];
    component.hasTeams = true;

    // Add a draft from user's team
    const teamDraftFromUserTeam: UseCaseResponse = {
      id: '5',
      use_case_id: 'uc-5',
      name: 'Team Draft from Red',
      description: '',
      category: '',
      intent_type: 'QUERY',
      version: 1,
      lifecycle_state: 'draft',
      is_active: false,
      config_json: {},
      metadata_json: {},
      created_at: '',
      updated_at: '2025-12-09T00:00:00Z',
      created_by_user_id: 'user-2',
      team_id: 'team:red',
    };

    const allDrafts = [...draftUseCases, teamDraftFromUserTeam];
    const response: UseCaseListResponse = {
      use_cases: allDrafts,
    };

    component['handleDrafts'](response);

    // Should only show team draft from team:red (user's team)
    expect(component.teamDrafts.data.length).toBe(1);
    expect(component.teamDrafts.data[0].team_id).toBe('team:red');
  });

  it('should handle errors gracefully', () => {
    const error = { error: { detail: 'failed' } };
    const result = component['handleTabError']('draft', error);

    // handleTabError sets the error state and returns an observable
    expect(component.myDrafts.error).toBe('failed');
    expect(component.teamDrafts.error).toBe('failed');
    expect(component.myDrafts.isLoading).toBe(false);
    expect(component.teamDrafts.isLoading).toBe(false);
    expect(result).toBeDefined();
  });

  it('should handle RBAC API errors gracefully', fakeAsync(() => {
    (userManagementService.getUserRoles as jest.Mock).mockReturnValueOnce(
      throwError(() => ({ error: { detail: 'RBAC API failed' } }))
    );

    component.user = currentUser;
    component['loadUserTeams']('user-1');
    flush(); // Flush all pending microtasks and timers

    // Error handler should set empty teams
    expect(component.userTeams).toEqual([]);
    expect(component.hasTeams).toBe(false);
  }));

  it('should preserve userTeams and hasTeams when loadAllTabs is called after loadUserTeams', fakeAsync(() => {
    // This test verifies Bug 2 fix: userTeams and hasTeams should persist
    // when loadAllTabs() calls resetState()
    component.user = currentUser;

    // Mock getUserRoles to return teams
    (userManagementService.getUserRoles as jest.Mock).mockReturnValueOnce(
      of(userRolesResponse)
    );

    // Load user teams - this will call loadAllTabs() internally
    component['loadUserTeams']('user-1');
    flush();

    // Verify teams are set
    expect(component.userTeams).toEqual(['team:red']);
    expect(component.hasTeams).toBe(true);

    // Now manually call loadAllTabs (simulating a refresh)
    // This should NOT clear userTeams and hasTeams
    component['loadAllTabs']();
    flush();

    // Verify teams are still preserved after resetState
    expect(component.userTeams).toEqual(['team:red']);
    expect(component.hasTeams).toBe(true);
  }));

  it('should navigate to edit mode when openUseCase is called with edit', () => {
    component.openUseCase('uc-123', 'edit');
    expect(router.navigate).toHaveBeenCalledWith([
      '/dev/use-cases/edit/uc-123',
    ]);
  });

  it('should navigate to view mode when openUseCase is called with view', () => {
    component.openUseCase('uc-456', 'view');
    expect(router.navigate).toHaveBeenCalledWith([
      '/dev/use-cases/view/uc-456',
    ]);
  });

  it('should filter team drafts by selected team', () => {
    component.user = currentUser;
    component.userTeams = ['team:red', 'team:blue'];
    component.hasTeams = true;
    component.selectedTeam = 'team:red';

    const teamDraft1: UseCaseResponse = {
      ...draftUseCases[1],
      team_id: 'team:red',
    };
    const teamDraft2: UseCaseResponse = {
      ...draftUseCases[1],
      use_case_id: 'uc-10',
      team_id: 'team:blue',
    };

    component.teamDrafts.data = [teamDraft1, teamDraft2];

    const filtered = component.filteredTeamDrafts();
    expect(filtered.length).toBe(1);
    expect(filtered[0].team_id).toBe('team:red');
  });

  it('should return all team drafts when no team is selected', () => {
    component.user = currentUser;
    component.userTeams = ['team:red', 'team:blue'];
    component.hasTeams = true;
    component.selectedTeam = null;

    component.teamDrafts.data = draftUseCases.filter((uc) => uc.team_id);

    const filtered = component.filteredTeamDrafts();
    expect(filtered.length).toBe(component.teamDrafts.data.length);
  });

  it('should select team when selectTeam is called', () => {
    component.selectTeam('team:blue');
    expect(component.selectedTeam).toBe('team:blue');
  });

  it('should track use cases by id', () => {
    const useCase = draftUseCases[0];
    const result = component.trackByUseCaseId(0, useCase);
    expect(result).toBe(useCase.id);
  });

  it('should sort use cases by updated_at descending', () => {
    const unsorted: UseCaseResponse[] = [
      { ...draftUseCases[0], updated_at: '2025-12-06T00:00:00Z' },
      { ...draftUseCases[1], updated_at: '2025-12-09T00:00:00Z' },
      { ...reviewUseCases[0], updated_at: '2025-12-07T00:00:00Z' },
    ];

    const sorted = component['sortByUpdatedAt'](unsorted);
    expect(sorted[0].updated_at).toBe('2025-12-09T00:00:00Z');
    expect(sorted[1].updated_at).toBe('2025-12-07T00:00:00Z');
    expect(sorted[2].updated_at).toBe('2025-12-06T00:00:00Z');
  });

  it('should handle review tab errors separately from draft tabs', () => {
    const error = { error: { detail: 'Review API failed' } };
    component['handleTabError']('review', error);

    expect(component.reviewTab.error).toBe('Review API failed');
    expect(component.reviewTab.isLoading).toBe(false);
    expect(component.myDrafts.error).toBeNull();
    expect(component.teamDrafts.error).toBeNull();
  });

  it('should handle published tab errors separately', () => {
    const error = { error: { detail: 'Published API failed' } };
    component['handleTabError']('published', error);

    expect(component.publishedTab.error).toBe('Published API failed');
    expect(component.publishedTab.isLoading).toBe(false);
    expect(component.myDrafts.error).toBeNull();
    expect(component.reviewTab.error).toBeNull();
  });

  it('should use default error message when detail is missing', () => {
    const error = {};
    component['handleTabError']('draft', error);

    expect(component.myDrafts.error).toBe(
      'Failed to load use cases. Please try again.'
    );
  });
});
