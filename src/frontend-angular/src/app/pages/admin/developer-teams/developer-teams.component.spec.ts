import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { DeveloperTeamInfo } from '../role-management/models/role-management.models';
import { DeveloperTeamsComponent } from './developer-teams.component';
import { DeveloperTeamsService } from './services/developer-teams.service';

describe('DeveloperTeamsComponent', () => {
  let fixture: ComponentFixture<DeveloperTeamsComponent>;
  let component: DeveloperTeamsComponent;
  let service: jest.Mocked<DeveloperTeamsService>;
  let snackBar: jest.Mocked<MatSnackBar>;

  const mockTeams: DeveloperTeamInfo[] = [
    {
      team_id: 'team:csirt',
      display_name: '',
      description: '',
      member_count: 2,
      draft_count: 1,
      published_count: 0,
    },
  ];

  beforeEach(async () => {
    service = {
      listTeams: jest.fn().mockReturnValue(of(mockTeams)),
      createTeam: jest.fn().mockReturnValue(
        of({
          team_id: 'team:csirt',
          user_id: 'user-1',
          added_at: '2025-12-08T10:00:00Z',
        })
      ),
      removeMember: jest.fn().mockReturnValue(of({})),
    } as unknown as jest.Mocked<DeveloperTeamsService>;

    snackBar = {
      open: jest.fn(),
    } as unknown as jest.Mocked<MatSnackBar>;

    await TestBed.configureTestingModule({
      imports: [
        DeveloperTeamsComponent,
        FormsModule,
        MatSnackBarModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: DeveloperTeamsService, useValue: service },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeveloperTeamsComponent);
    component = fixture.componentInstance;
  });

  it('should load teams on init', () => {
    fixture.detectChanges();

    expect(service.listTeams).toHaveBeenCalled();
    expect(component.teams.length).toBe(1);
    expect(component.teams[0].team_id).toBe('team:csirt');
  });

  it('should set error when load fails', () => {
    service.listTeams.mockReturnValue(throwError(() => new Error('fail')));

    fixture.detectChanges();

    expect(component.error).toBe('Failed to load teams');
    expect(component.isLoading).toBe(false);
  });

  it('should validate team id before create', () => {
    component.newTeamId = 'invalid';
    fixture.detectChanges();

    component.createTeam();

    expect(component.error).toContain('Invalid team ID');
    expect(service.createTeam).not.toHaveBeenCalled();
  });

  it('should create team when valid', () => {
    service.listTeams.mockReturnValue(of([]));
    service.createTeam.mockReturnValue(
      of({
        team_id: 'team:csirt',
        user_id: 'user-1',
        added_at: '2025-12-08T10:00:00Z',
      })
    );

    fixture.detectChanges();

    component.newTeamId = 'team:csirt';
    component.initialMemberId = '';
    component.createTeam();

    expect(service.createTeam).toHaveBeenCalledWith('team:csirt', undefined);
  });

  it('should remove member when confirmed', () => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    service.listTeams.mockReturnValue(of([]));
    service.removeMember.mockReturnValue(of({}));

    fixture.detectChanges();

    component.removeMember(
      {
        team_id: 'team:csirt',
        display_name: '',
        description: '',
        member_count: 1,
        draft_count: 0,
        published_count: 0,
      },
      'user-1'
    );

    expect(service.removeMember).toHaveBeenCalledWith('team:csirt', 'user-1');
  });
});
