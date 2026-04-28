/**
 * TypeScript models for user management operations.
 *
 * These models match the backend Pydantic schemas for user CRUD,
 * session management, and admin operations.
 */

export interface SessionInfo {
  id: string;
  created_at: string;
  last_activity: string;
  ip_address?: string;
  user_agent?: string;
  expires_at: string;
  revoked: boolean;
}

export interface UserListItem {
  id: string;
  username: string;
  full_name?: string;
  email?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  session_count: number;
}

export interface UserListResponse {
  items: UserListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface UserDetailResponse {
  id: string;
  username: string;
  full_name?: string;
  email?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string;
  active_sessions: SessionInfo[];
  metadata: Record<string, any>;
}

export interface UserUpdateRequest {
  full_name?: string;
  email?: string;
  role?: string;
  is_active?: boolean;
}

export interface UserCreateRequest {
  username: string;
  password: string;
  full_name?: string;
  email?: string;
  role: string;
}

export interface PasswordResetRequest {
  new_password: string;
  force_logout?: boolean;
}

export interface UserFilters {
  search?: string;
  role?: string;
  status?: 'active' | 'inactive' | '';
  limit?: number;
  offset?: number;
}

export interface UserRoleInfo {
  role: string;
  granted_by?: string;
  granted_at?: string;
  metadata: Record<string, any>;
}

export interface UserRolesResponse {
  user_id: string;
  system_roles: string[];
  grouping_roles: string[];
  teams: string[];
  all_roles: UserRoleInfo[];
}

export interface UpdateUserRolesRequest {
  system_roles: string[];
  grouping_roles: string[];
  teams: string[];
}
