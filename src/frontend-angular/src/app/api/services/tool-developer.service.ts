import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Tool, ToolListItem } from '../models/tool.models';

@Injectable({
  providedIn: 'root',
})
export class ToolDeveloperService {
  private readonly API_BASE = '/api/v1/tools';

  constructor(private http: HttpClient) {}

  /**
   * List tools available to current user based on role.
   * @param category Optional category filter
   */
  listAvailableTools(category?: string): Observable<ToolListItem[]> {
    let params = new HttpParams();
    if (category) {
      params = params.set('category', category);
    }
    return this.http.get<ToolListItem[]>(`${this.API_BASE}/available`, {
      params,
    });
  }

  /**
   * Get detailed tool information.
   * @param toolId Tool UUID
   */
  getToolDetails(toolId: string): Observable<Tool> {
    return this.http.get<Tool>(`${this.API_BASE}/${toolId}/details`);
  }
}
