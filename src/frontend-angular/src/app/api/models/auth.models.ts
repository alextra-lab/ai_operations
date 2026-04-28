/**
 * Authentication-related models generated from FastAPI OpenAPI spec
 */

export interface LoginRequest {
  grant_type?: string | null;
  username: string;
  password: string;
  scope?: string;
  client_id?: string | null;
  client_secret?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface UserCreate {
  username: string;
  full_name?: string | null;
  email?: string | null;
  role?: string;
  is_active?: boolean;
  user_metadata?: Record<string, any>;
  password: string;
}

export interface UserUpdate {
  full_name?: string | null;
  email?: string | null;
  role?: string | null;
  is_active?: boolean | null;
  metadata?: Record<string, any> | null;
}

export interface UserResponse {
  username: string;
  full_name?: string | null;
  email?: string | null;
  role?: string;
  is_active?: boolean;
  user_metadata?: Record<string, any>;
  id: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_login?: string | null;
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}
