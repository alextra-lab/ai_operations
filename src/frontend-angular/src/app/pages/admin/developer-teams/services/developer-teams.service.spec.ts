import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { DeveloperTeamInfo } from '../../role-management/models/role-management.models';
import { DeveloperTeamsService } from './developer-teams.service';

describe('DeveloperTeamsService', () => {
  let service: DeveloperTeamsService;
  let httpMock: HttpTestingController;

  const apiUrl = '/api/v1/admin/developer-teams';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [DeveloperTeamsService],
    });

    service = TestBed.inject(DeveloperTeamsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should list teams', () => {
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

    service.listTeams().subscribe((teams) => {
      expect(teams).toEqual(mockTeams);
    });

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('GET');
    req.flush(mockTeams);
  });

  it('should create team', () => {
    service.createTeam('team:csirt', 'user-1').subscribe();

    const req = httpMock.expectOne(apiUrl);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      team_id: 'team:csirt',
      member_user_id: 'user-1',
    });
    req.flush({});
  });

  it('should add member', () => {
    service.addMember('team:csirt', 'user-1').subscribe();

    const req = httpMock.expectOne(`${apiUrl}/team:csirt/members/user-1`);
    expect(req.request.method).toBe('POST');
    req.flush({});
  });

  it('should remove member', () => {
    service.removeMember('team:csirt', 'user-1').subscribe();

    const req = httpMock.expectOne(`${apiUrl}/team:csirt/members/user-1`);
    expect(req.request.method).toBe('DELETE');
    req.flush({});
  });

  it('should list team use cases', () => {
    service.listTeamUseCases('team:csirt').subscribe();

    const req = httpMock.expectOne(`${apiUrl}/team:csirt/use-cases`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });
});
