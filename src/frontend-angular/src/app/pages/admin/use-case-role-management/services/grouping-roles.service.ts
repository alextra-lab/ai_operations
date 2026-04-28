import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../../../environments/environment';
import { GroupingRoleInfo } from '../../role-management/models/role-management.models';

interface CreateGroupingRoleRequest {
  role_name: string;
}

@Injectable({
  providedIn: 'root',
})
export class GroupingRolesService {
  private readonly apiUrl = `${environment.apiBaseUrl}/admin/grouping-roles`;

  constructor(private http: HttpClient) {}

  listRoles(): Observable<GroupingRoleInfo[]> {
    return this.http.get<GroupingRoleInfo[]>(this.apiUrl);
  }

  createRole(roleName: string): Observable<GroupingRoleInfo> {
    const body: CreateGroupingRoleRequest = { role_name: roleName };
    return this.http.post<GroupingRoleInfo>(this.apiUrl, body);
  }

  deleteRole(roleName: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${roleName}`);
  }
}
