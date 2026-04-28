export type UserRole =
  | 'admin'
  | 'corpus_admin'
  | 'developer'
  | 'use_case_admin'
  | 'tools_admin'
  | 'role_admin'
  | 'use_case_publisher'
  | 'conversations_privileged'
  | 'user'
  | 'service';

export interface LoginRequest {
  readonly username: string;
  readonly password: string;
}

export interface AuthResponse {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly token_type: 'bearer';
  readonly expires_in?: number;
  readonly refresh_expires_in?: number;
}

export interface RefreshTokenRequest {
  readonly token: string;
}

export interface RevokeTokenRequest {
  readonly refresh_token: string;
}

export interface UserProfile {
  readonly id: string;
  readonly username: string;
  readonly full_name: string;
  readonly roles: readonly UserRole[];
  readonly expires_at?: number;
}

export interface AuthTokens {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly accessTokenExpiresAt?: number;
  readonly refreshTokenExpiresAt?: number;
}

export interface AuthState {
  readonly isAuthenticated: boolean;
  readonly user: UserProfile | null;
  readonly tokens: AuthTokens | null;
}

export const enum TokenType {
  Access = 'access',
  Refresh = 'refresh',
}

export interface JwtPayload {
  readonly exp?: number;
  readonly iat?: number;
  readonly iss?: string;
  readonly jti?: string;
  readonly role?: string | string[]; // Legacy: single role or array
  readonly roles?: string[]; // New: multi-role support (ADR-060)
  readonly sub?: string;
  readonly token_type?: TokenType;
}
