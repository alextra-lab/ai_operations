import {
  HttpClient,
  HttpContext,
  HttpErrorResponse,
  HttpHeaders,
} from '@angular/common/http';
import { inject, Inject, Injectable } from '@angular/core';
import { Router } from '@angular/router';
import {
  BehaviorSubject,
  catchError,
  map,
  Observable,
  of,
  tap,
  throwError,
} from 'rxjs';

import { SecureStorageService } from '../services/secure-storage.service';
import {
  AuthResponse,
  AuthState,
  AuthTokens,
  JwtPayload,
  LoginRequest,
  RefreshTokenRequest,
  RevokeTokenRequest,
  TokenType,
  UserProfile,
  UserRole,
} from './auth.models';
import {
  BYPASS_AUTH_INTERCEPTOR,
  BYPASS_SECURITY_INTERCEPTOR,
} from './http-context-tokens';

const AUTH_API_PREFIX = '/auth';

const AUTH_STATE_INITIAL: AuthState = {
  isAuthenticated: false,
  user: null,
  tokens: null,
};

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly state$ = new BehaviorSubject<AuthState>(AUTH_STATE_INITIAL);

  private readonly http = inject(HttpClient);
  private readonly storage = inject(SecureStorageService);
  private readonly router = inject(Router);

  constructor(@Inject('API_BASE_URL') private readonly apiBaseUrl: string) {
    this.restoreState();
  }

  login(credentials: LoginRequest): Observable<UserProfile> {
    const context = new HttpContext()
      .set(BYPASS_AUTH_INTERCEPTOR, true)
      .set(BYPASS_SECURITY_INTERCEPTOR, true);

    const body = new URLSearchParams();
    body.set('username', credentials.username);
    body.set('password', credentials.password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http
      .post<AuthResponse>(
        `${this.apiBaseUrl}${AUTH_API_PREFIX}/token`,
        body.toString(),
        {
          context,
          headers,
        }
      )
      .pipe(
        map((response) => {
          const tokens = this.mapTokens(response);
          this.persistTokens(tokens);
          return tokens;
        }),
        map((tokens) => this.decodeUserProfile(tokens.accessToken)),
        tap((profile) => {
          this.setState({
            isAuthenticated: true,
            user: profile,
            tokens: this.state$.value.tokens,
          });
        }),
        catchError((error) => {
          this.clearSession();
          return throwError(() => error);
        })
      );
  }

  refreshToken(): Observable<AuthTokens | null> {
    const tokens = this.storage.getToken(TokenType.Refresh);
    if (!tokens) {
      return of(null);
    }

    const context = new HttpContext()
      .set(BYPASS_AUTH_INTERCEPTOR, true)
      .set(BYPASS_SECURITY_INTERCEPTOR, true);

    const body: RefreshTokenRequest = { token: tokens };

    return this.http
      .post<AuthResponse>(
        `${this.apiBaseUrl}${AUTH_API_PREFIX}/refresh`,
        body,
        { context }
      )
      .pipe(
        map((response) => {
          const updatedTokens = this.mergeTokens(response);
          this.persistTokens(updatedTokens);
          const currentUser = this.decodeUserProfile(updatedTokens.accessToken);
          this.setState({
            isAuthenticated: true,
            user: currentUser,
            tokens: updatedTokens,
          });
          return updatedTokens;
        }),
        catchError((error) => {
          if (error.status === 401) {
            this.handlePostLogout();
          }
          return throwError(() => error);
        })
      );
  }

  logout(): Observable<void> {
    const refreshToken = this.storage.getToken(TokenType.Refresh);

    // If no refresh token, just clear local state and redirect
    if (!refreshToken) {
      this.handlePostLogout();
      return of(void 0);
    }

    const body: RevokeTokenRequest = { refresh_token: refreshToken };

    // Don't require auth interceptor since we're revoking the token
    const context = new HttpContext().set(BYPASS_SECURITY_INTERCEPTOR, true);

    return this.http
      .post<void>(`${this.apiBaseUrl}${AUTH_API_PREFIX}/revoke`, body, {
        context,
      })
      .pipe(
        catchError((httpError: HttpErrorResponse) => {
          console.error('Failed to revoke token on server');
          // Even if server revocation fails, clear local state
          this.handlePostLogout();
          return of(void 0);
        }),
        map(() => {
          this.handlePostLogout();
          return void 0;
        })
      );
  }

  getCurrentUser(): Observable<UserProfile | null> {
    return this.state$.asObservable().pipe(map((state) => state.user));
  }

  isAuthenticated(): boolean {
    return this.state$.value.isAuthenticated;
  }

  hasRole(role: UserRole | string): boolean {
    const user = this.state$.value.user;
    if (!user) {
      return false;
    }
    return user.roles.includes(role as UserRole);
  }

  hasAnyRole(roles: readonly (UserRole | string)[]): boolean {
    const user = this.state$.value.user;
    if (!user) {
      return false;
    }
    return roles.some((role) => user.roles.includes(role as UserRole));
  }

  getAccessToken(): string | null {
    return this.storage.getToken(TokenType.Access);
  }

  private decodeUserProfile(token: string): UserProfile {
    const payload = this.decodeJwt(token);
    // Support both new multi-role format (roles) and legacy format (role)
    const roles = this.normalizeRoles(payload.roles ?? payload.role);

    const expiresAt = payload.exp ? payload.exp * 1000 : undefined;

    const profile: UserProfile = {
      id: payload.user_id ?? payload.sub ?? '',
      username: payload.sub ?? '',
      full_name: payload.full_name ?? payload.sub ?? '',
      roles,
      expires_at: expiresAt,
    };

    this.storage.setUserProfile(profile);

    return profile;
  }

  private decodeJwt(token: string): JwtPayload & {
    readonly user_id?: string;
    readonly full_name?: string;
    readonly roles?: string[];
  } {
    try {
      const [, payload] = token.split('.');
      const decoded = this.decodeBase64(payload);
      return JSON.parse(decoded) as JwtPayload & {
        readonly user_id?: string;
        readonly full_name?: string;
        readonly roles?: string[];
      };
    } catch {
      throw new Error('Invalid JWT token');
    }
  }

  private decodeBase64(value: string): string {
    const normalized = this.normalizeBase64(value);

    if (typeof globalThis.atob === 'function') {
      return globalThis.atob(normalized);
    }

    const globalBuffer = (
      globalThis as unknown as {
        Buffer?: {
          from(
            data: string,
            encoding: string
          ): {
            toString(encoding: string): string;
          };
        };
      }
    ).Buffer;

    if (globalBuffer) {
      return globalBuffer.from(normalized, 'base64').toString('binary');
    }

    throw new Error('Base64 decoding not supported');
  }

  private normalizeBase64(value: string): string {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const padLength = normalized.length % 4;
    return padLength
      ? normalized.padEnd(normalized.length + (4 - padLength), '=')
      : normalized;
  }

  private normalizeRoles(
    role: string | string[] | undefined
  ): readonly UserRole[] {
    // All 10 system roles per ADR-060
    const allowedRoles: readonly UserRole[] = [
      'admin',
      'corpus_admin',
      'developer',
      'use_case_admin',
      'tools_admin',
      'role_admin',
      'use_case_publisher',
      'conversations_privileged',
      'user',
      'service',
    ];

    if (!role) {
      return [];
    }

    const roles = Array.isArray(role) ? role : [role];

    return roles.filter((value): value is UserRole =>
      allowedRoles.includes(value as UserRole)
    );
  }

  private mapTokens(response: AuthResponse): AuthTokens {
    return {
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      accessTokenExpiresAt: response.expires_in
        ? Date.now() + response.expires_in * 1000
        : undefined,
      refreshTokenExpiresAt: response.refresh_expires_in
        ? Date.now() + response.refresh_expires_in * 1000
        : undefined,
    };
  }

  private mergeTokens(response: AuthResponse): AuthTokens {
    const existingTokens = this.state$.value.tokens;
    const mapped = this.mapTokens(response);

    if (!existingTokens) {
      return mapped;
    }

    return {
      accessToken: mapped.accessToken,
      refreshToken: existingTokens.refreshToken,
      accessTokenExpiresAt: mapped.accessTokenExpiresAt,
      refreshTokenExpiresAt: existingTokens.refreshTokenExpiresAt,
    };
  }

  private persistTokens(tokens: AuthTokens): void {
    this.storage.setTokens(tokens);
    this.setState({
      isAuthenticated: true,
      user: this.state$.value.user,
      tokens,
    });
  }

  private restoreState(): void {
    const accessToken = this.storage.getToken(TokenType.Access);
    const refreshToken = this.storage.getToken(TokenType.Refresh);

    if (!accessToken || !refreshToken) {
      this.clearSession();
      return;
    }

    const profile = this.storage.getUserProfile<UserProfile>();

    if (profile) {
      this.setState({
        isAuthenticated: true,
        user: profile,
        tokens: this.composeTokenState(accessToken, refreshToken),
      });
      return;
    }

    this.syncStateFromTokens(accessToken, refreshToken);
  }

  private clearSession(): void {
    this.storage.clearAll();
    this.setState(AUTH_STATE_INITIAL);
  }

  private handlePostLogout(): void {
    this.clearSession();
    // Clear draft storage on logout to prevent data persisting across user sessions
    this.clearDraftStorage();
    void this.router.navigate(['/login']);
  }

  private clearDraftStorage(): void {
    // Clear all tool registration drafts stored in localStorage
    try {
      // Clear legacy key
      localStorage.removeItem('tool_registration_draft');

      // Clear all user-specific draft keys
      const keys: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('tool_registration_draft:')) {
          keys.push(key);
        }
      }
      keys.forEach((key) => localStorage.removeItem(key));
    } catch {
      // localStorage might not be available (e.g., SSR), ignore
    }
  }

  private setState(state: AuthState): void {
    this.state$.next(state);
  }

  private composeTokenState(
    accessToken: string,
    refreshToken: string
  ): AuthTokens {
    return {
      accessToken,
      refreshToken,
      accessTokenExpiresAt:
        this.storage.getTokenExpiration(TokenType.Access) ?? undefined,
      refreshTokenExpiresAt:
        this.storage.getTokenExpiration(TokenType.Refresh) ?? undefined,
    };
  }

  private syncStateFromTokens(accessToken: string, refreshToken: string): void {
    try {
      const decoded = this.decodeUserProfile(accessToken);
      this.setState({
        isAuthenticated: true,
        user: decoded,
        tokens: this.composeTokenState(accessToken, refreshToken),
      });
    } catch {
      this.clearSession();
    }
  }
}
