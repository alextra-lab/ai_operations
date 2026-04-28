import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export enum ToolRegistrationPhase {
  BASIC_INFO = 'basic_info',
  MCP_CONFIG = 'mcp_config',
  CONNECTION_TEST = 'connection_test',
  SECURITY_CONFIG = 'security_config',
  PERMISSIONS = 'permissions',
  REVIEW = 'review',
  COMMIT = 'commit',
}

export interface ToolRegistrationRequest {
  session_id: string | null;
  phase: ToolRegistrationPhase;
  data: Record<string, any>;
}

export interface ToolRegistrationResponse {
  session_id: string;
  current_phase: ToolRegistrationPhase;
  next_phase: ToolRegistrationPhase | null;
  validation_errors: Record<string, string[]>;
  can_proceed: boolean;
  discovered_capabilities?: Record<string, any>;
  tool_id?: string;
  message: string;
}

export interface RegistrationSessionResponse {
  session_id: string;
  current_phase: ToolRegistrationPhase;
  created_at: string;
  updated_at: string;
  expires_at: string;
  collected_data: Record<string, any>;
  validation_status: Record<string, boolean>;
}

@Injectable({
  providedIn: 'root',
})
export class ToolRegistrationService {
  private readonly baseUrl = '/api/v1/admin/tools/register';

  constructor(private http: HttpClient) {}

  processPhase(
    request: ToolRegistrationRequest
  ): Observable<ToolRegistrationResponse> {
    return this.http.post<ToolRegistrationResponse>(this.baseUrl, request);
  }

  getSession(sessionId: string): Observable<RegistrationSessionResponse> {
    return this.http.get<RegistrationSessionResponse>(
      `${this.baseUrl}/session/${sessionId}`
    );
  }

  cancelRegistration(sessionId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/session/${sessionId}`);
  }
}
