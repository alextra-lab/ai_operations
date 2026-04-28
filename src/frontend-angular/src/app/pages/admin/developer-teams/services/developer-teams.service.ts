import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../../environments/environment';
import { DeveloperTeamInfo } from '../../role-management/models/role-management.models';

interface CreateTeamRequest {
  team_id: string;
  member_user_id?: string;
}

@Injectable({
  providedIn: 'root',
})
export class DeveloperTeamsService {
  private readonly apiUrl = `${environment.apiBaseUrl}/admin/developer-teams`;

  constructor(private http: HttpClient) {}

  listTeams(): Observable<DeveloperTeamInfo[]> {
    return this.http.get<DeveloperTeamInfo[]>(this.apiUrl);
  }

  createTeam(
    teamId: string,
    memberUserId?: string
  ): Observable<DeveloperTeamInfo> {
    const body: CreateTeamRequest = {
      team_id: teamId,
      member_user_id: memberUserId,
    };
    return this.http.post<DeveloperTeamInfo>(this.apiUrl, body);
  }

  addMember(teamId: string, userId: string): Observable<void> {
    return this.http.post<void>(
      `${this.apiUrl}/${teamId}/members/${userId}`,
      undefined
    );
  }

  removeMember(teamId: string, userId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${teamId}/members/${userId}`);
  }

  listTeamUseCases(teamId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/${teamId}/use-cases`);
  }
}
