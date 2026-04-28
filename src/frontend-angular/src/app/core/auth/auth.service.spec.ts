import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { firstValueFrom } from 'rxjs';

import { SecureStorageService } from '../services/secure-storage.service';
import {
  AuthResponse,
  AuthTokens,
  TokenType,
  UserProfile,
} from './auth.models';
import { AuthService } from './auth.service';

class SecureStorageServiceStub {
  tokens: AuthTokens | null = null;
  profile: unknown = null;
  cleared = false;
  accessExpires: number | null = null;
  refreshExpires: number | null = null;

  setTokens(tokens: AuthTokens): void {
    this.tokens = tokens;
    this.accessExpires = tokens.accessTokenExpiresAt ?? null;
    this.refreshExpires = tokens.refreshTokenExpiresAt ?? null;
  }

  getToken(type: TokenType): string | null {
    if (!this.tokens) {
      return null;
    }

    return type === TokenType.Access
      ? this.tokens.accessToken
      : this.tokens.refreshToken;
  }

  getTokenExpiration(type: TokenType): number | null {
    return type === TokenType.Access ? this.accessExpires : this.refreshExpires;
  }

  clearTokens(): void {
    this.tokens = null;
    this.accessExpires = null;
    this.refreshExpires = null;
  }

  setUserProfile(profile: unknown): void {
    this.profile = profile;
  }

  getUserProfile<T>(): T | null {
    return (this.profile as T) ?? null;
  }

  clearUserProfile(): void {
    this.profile = null;
  }

  clearAll(): void {
    this.cleared = true;
    this.clearTokens();
    this.clearUserProfile();
  }
}

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let router: Router;
  let storage: SecureStorageServiceStub;
  let navigateSpy: jest.SpyInstance<Promise<boolean>>;

  beforeEach(() => {
    storage = new SecureStorageServiceStub();

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
      providers: [
        { provide: SecureStorageService, useValue: storage },
        { provide: 'API_BASE_URL', useValue: '' },
      ],
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    navigateSpy = jest
      .spyOn(router, 'navigate')
      .mockResolvedValue(true as never);
  });

  afterEach(() => {
    if (httpMock) {
      httpMock.verify();
    }
    if (navigateSpy) {
      navigateSpy.mockRestore();
    }
    jest.clearAllTimers();
  });

  it('logs in and stores decoded user profile', async () => {
    const credentials = { username: 'admin', password: 'secret' };
    const accessToken = createJwt({
      sub: 'admin',
      role: ['admin'],
      user_id: '123',
      full_name: 'Admin User',
      exp: futureSeconds(900),
    });
    const refreshToken = createJwt({
      sub: 'admin',
      token_type: 'refresh',
      exp: futureSeconds(3600),
    });

    const loginPromise = firstValueFrom(service.login(credentials));

    const request = httpMock.expectOne('/auth/token');
    expect(request.request.method).toBe('POST');
    request.flush(createAuthResponse(accessToken, refreshToken));

    const profile = await loginPromise;

    expect(profile).toMatchObject<UserProfile>({
      username: 'admin',
      id: '123',
      full_name: 'Admin User',
    });
    expect(storage.tokens?.accessToken).toBe(accessToken);
    expect(service.hasRole('admin')).toBe(true);
    expect(service.hasAnyRole(['analyst', 'admin'])).toBe(true);
    expect(service.getAccessToken()).toBe(accessToken);
  });

  it('clears session when login fails', async () => {
    storage.setTokens({
      accessToken: 'old',
      refreshToken: 'old-refresh',
    });

    const credentials = { username: 'analyst', password: 'wrong' };
    const loginPromise = firstValueFrom(service.login(credentials));

    const request = httpMock.expectOne('/auth/token');
    request.flush(
      { detail: 'invalid' },
      { status: 401, statusText: 'Unauthorized' }
    );

    await expect(loginPromise).rejects.toBeDefined();
    expect(storage.cleared).toBe(true);
  });

  it('returns null when refresh token is missing', async () => {
    const result = await firstValueFrom(service.refreshToken());

    expect(result).toBeNull();
    httpMock.expectNone('/auth/refresh');
  });

  it('refreshes access token while keeping refresh token', async () => {
    await performLogin(service, httpMock);
    const currentTokens = storage.tokens;
    expect(currentTokens).not.toBeNull();

    const refreshPromise = firstValueFrom(service.refreshToken());
    const request = httpMock.expectOne('/auth/refresh');
    expect(request.request.body).toEqual({
      token: currentTokens?.refreshToken,
    });

    const newAccessToken = createJwt({
      sub: 'admin',
      role: 'admin',
      user_id: '123',
      exp: futureSeconds(1200),
    });

    request.flush(createAuthResponse(newAccessToken, 'ignored-refresh'));

    const tokens = await refreshPromise;
    expect(tokens).not.toBeNull();
    expect(tokens?.accessToken).toBe(newAccessToken);
    expect(tokens?.refreshToken).toBe(currentTokens?.refreshToken);
    expect(storage.tokens?.accessToken).toBe(newAccessToken);
  });

  it('logs out and navigates when refresh token is invalid', async () => {
    await performLogin(service, httpMock);

    const refreshPromise = firstValueFrom(service.refreshToken());
    const request = httpMock.expectOne('/auth/refresh');
    request.flush(
      { detail: 'expired' },
      { status: 401, statusText: 'Unauthorized' }
    );

    await expect(refreshPromise).rejects.toBeDefined();
    expect(storage.cleared).toBe(true);
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('logs out without server call when refresh token missing', async () => {
    const result = await firstValueFrom(service.logout());

    expect(result).toBeUndefined();
    expect(storage.cleared).toBe(true);
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
    httpMock.expectNone('/auth/revoke');
  });

  it('revokes refresh token during logout', async () => {
    const baseTokens: AuthTokens = {
      accessToken: 'access',
      refreshToken: 'refresh-token',
      accessTokenExpiresAt: futureMillis(60),
      refreshTokenExpiresAt: futureMillis(3600),
    };
    storage.setTokens(baseTokens);

    const logoutPromise = firstValueFrom(service.logout());
    const request = httpMock.expectOne('/auth/revoke');
    expect(request.request.body).toEqual({ refresh_token: 'refresh-token' });
    request.flush({});

    await logoutPromise;
    expect(storage.cleared).toBe(true);
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('decodes JWT without global atob support', async () => {
    const originalAtob = (globalThis as Record<string, unknown>).atob;
    delete (globalThis as Record<string, unknown>).atob;

    // Mock Buffer to provide fallback
    const mockBuffer = {
      from: jest.fn().mockReturnValue({
        toString: jest
          .fn()
          .mockReturnValue(
            '{"sub":"admin","role":"admin","user_id":"123","exp":' +
              futureSeconds(1800) +
              '}'
          ),
      }),
    };
    (globalThis as any).Buffer = mockBuffer;

    try {
      await performLogin(service, httpMock);
    } finally {
      (globalThis as Record<string, unknown>).atob = originalAtob;
      delete (globalThis as any).Buffer;
    }

    expect(storage.tokens?.accessToken).toBeDefined();
  });

  it('decodes JWT with Buffer fallback', async () => {
    const originalAtob = (globalThis as Record<string, unknown>).atob;
    delete (globalThis as Record<string, unknown>).atob;

    // Mock Buffer
    const mockBuffer = {
      from: jest.fn().mockReturnValue({
        toString: jest
          .fn()
          .mockReturnValue(
            '{"sub":"admin","role":"admin","user_id":"123","exp":' +
              futureSeconds(1800) +
              '}'
          ),
      }),
    };
    (globalThis as any).Buffer = mockBuffer;

    try {
      await performLogin(service, httpMock);
    } finally {
      (globalThis as Record<string, unknown>).atob = originalAtob;
      delete (globalThis as any).Buffer;
    }

    expect(storage.tokens?.accessToken).toBeDefined();
  });

  it('throws error when no base64 decoding is available', () => {
    const originalAtob = (globalThis as Record<string, unknown>).atob;
    delete (globalThis as Record<string, unknown>).atob;
    delete (globalThis as any).Buffer;

    const credentials = { username: 'admin', password: 'secret' };
    const accessToken = createJwt({
      sub: 'admin',
      role: 'admin',
      user_id: '123',
      exp: futureSeconds(1800),
    });

    try {
      service.login(credentials).subscribe({
        error: (error) => {
          expect(error.message).toContain('Base64 decoding not supported');
        },
      });

      const request = httpMock.expectOne('/auth/token');
      request.flush(createAuthResponse(accessToken, 'refresh-token'));
    } finally {
      (globalThis as Record<string, unknown>).atob = originalAtob;
    }
  });

  it('handles invalid JWT token', () => {
    const credentials = { username: 'admin', password: 'secret' };
    const invalidToken = 'invalid.token.here';

    service.login(credentials).subscribe({
      error: (error) => {
        expect(error.message).toContain('Invalid JWT token');
      },
    });

    const request = httpMock.expectOne('/auth/token');
    request.flush(createAuthResponse(invalidToken, 'refresh-token'));
  });

  it('handles logout with server error', async () => {
    const baseTokens: AuthTokens = {
      accessToken: 'access',
      refreshToken: 'refresh-token',
      accessTokenExpiresAt: futureMillis(60),
      refreshTokenExpiresAt: futureMillis(3600),
    };
    storage.setTokens(baseTokens);

    const logoutPromise = firstValueFrom(service.logout());
    const request = httpMock.expectOne('/auth/revoke');
    request.flush(
      { detail: 'Server error' },
      { status: 500, statusText: 'Internal Server Error' }
    );

    await logoutPromise;
    expect(storage.cleared).toBe(true);
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('handles token expiration correctly', () => {
    const tokens: AuthTokens = {
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      accessTokenExpiresAt: Date.now() + 3600000,
      refreshTokenExpiresAt: Date.now() + 7200000,
    };

    storage.setTokens(tokens);

    expect(storage.getTokenExpiration(TokenType.Access)).toBe(
      tokens.accessTokenExpiresAt
    );
    expect(storage.getTokenExpiration(TokenType.Refresh)).toBe(
      tokens.refreshTokenExpiresAt
    );
  });

  it('handles getCurrentUser observable', async () => {
    const mockUser: UserProfile = {
      id: '123',
      username: 'admin',
      full_name: 'Admin User',
      roles: ['admin'],
    };

    // First login to set up authenticated state properly
    const credentials = { username: 'admin', password: 'secret' };
    const accessToken = createJwt({
      sub: 'admin',
      role: 'admin',
      user_id: '123',
      full_name: 'Admin User',
      exp: futureSeconds(1800),
    });

    const loginPromise = firstValueFrom(service.login(credentials));
    const request = httpMock.expectOne('/auth/token');
    request.flush(createAuthResponse(accessToken, 'refresh-token'));
    await loginPromise;

    // Now test getCurrentUser
    const user = await firstValueFrom(service.getCurrentUser());
    expect(user).toMatchObject({
      id: '123',
      username: 'admin',
      full_name: 'Admin User',
    });
  });

  it('returns null from getCurrentUser when not authenticated', async () => {
    const user = await firstValueFrom(service.getCurrentUser());
    expect(user).toBeNull();
  });

  it('normalizes roles correctly', async () => {
    const credentials = { username: 'admin', password: 'secret' };
    const accessToken = createJwt({
      sub: 'admin',
      role: ['admin', 'user', 'invalid_role'],
      user_id: '123',
      exp: futureSeconds(1800),
    });

    const loginPromise = firstValueFrom(service.login(credentials));
    const request = httpMock.expectOne('/auth/token');
    request.flush(createAuthResponse(accessToken, 'refresh-token'));

    const profile = await loginPromise;
    expect(profile.roles).toEqual(['admin', 'user']);
    expect(profile.roles).not.toContain('invalid_role');
  });

  it('handles empty roles', async () => {
    const credentials = { username: 'user', password: 'secret' };
    const accessToken = createJwt({
      sub: 'user',
      role: undefined,
      user_id: '123',
      exp: futureSeconds(1800),
    });

    const loginPromise = firstValueFrom(service.login(credentials));
    const request = httpMock.expectOne('/auth/token');
    request.flush(createAuthResponse(accessToken, 'refresh-token'));

    const profile = await loginPromise;
    expect(profile.roles).toEqual([]);
  });

  it('handles string role', async () => {
    const credentials = { username: 'user', password: 'secret' };
    const accessToken = createJwt({
      sub: 'user',
      role: 'user',
      user_id: '123',
      exp: futureSeconds(1800),
    });

    const loginPromise = firstValueFrom(service.login(credentials));
    const request = httpMock.expectOne('/auth/token');
    request.flush(createAuthResponse(accessToken, 'refresh-token'));

    const profile = await loginPromise;
    expect(profile.roles).toEqual(['user']);
  });

  it('merges tokens when existing tokens are present', async () => {
    // First login to establish tokens
    await performLogin(service, httpMock);
    const currentTokens = storage.tokens;
    expect(currentTokens).not.toBeNull();

    const refreshPromise = firstValueFrom(service.refreshToken());
    const request = httpMock.expectOne('/auth/refresh');

    const newAccessToken = createJwt({
      sub: 'admin',
      role: 'admin',
      user_id: '123',
      exp: futureSeconds(1200),
    });

    request.flush({
      access_token: newAccessToken,
      refresh_token: 'ignored-refresh',
      token_type: 'bearer',
      expires_in: 1200,
    });

    const tokens = await refreshPromise;
    expect(tokens?.accessToken).toBe(newAccessToken);
    expect(tokens?.refreshToken).toBe(currentTokens?.refreshToken); // Should keep existing refresh token
  });

  it('handles refresh token with non-401 error', async () => {
    await performLogin(service, httpMock);

    const refreshPromise = firstValueFrom(service.refreshToken());
    const request = httpMock.expectOne('/auth/refresh');
    request.flush(
      { detail: 'Server error' },
      { status: 500, statusText: 'Internal Server Error' }
    );

    await expect(refreshPromise).rejects.toBeDefined();
    // Should not navigate to login for non-401 errors
    expect(navigateSpy).not.toHaveBeenCalledWith(['/login']);
  });
});

function createAuthResponse(
  accessToken: string,
  refreshToken: string
): AuthResponse {
  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    token_type: 'bearer',
    expires_in: 1800,
    refresh_expires_in: 604800,
  };
}

function futureSeconds(offset: number): number {
  return Math.floor(Date.now() / 1000) + offset;
}

function futureMillis(offset: number): number {
  return Date.now() + offset * 1000;
}

function performLogin(
  service: AuthService,
  httpMock: HttpTestingController
): Promise<UserProfile> {
  const credentials = { username: 'admin', password: 'secret' };
  const accessToken = createJwt({
    sub: 'admin',
    role: 'admin',
    user_id: '123',
    exp: futureSeconds(1800),
  });
  const refreshToken = createJwt({
    sub: 'admin',
    token_type: 'refresh',
    exp: futureSeconds(7200),
  });

  const loginPromise = firstValueFrom(service.login(credentials));
  httpMock
    .expectOne('/auth/token')
    .flush(createAuthResponse(accessToken, refreshToken));
  return loginPromise;
}

function createJwt(payload: Record<string, unknown>): string {
  const header = encodeSegment({ alg: 'HS256', typ: 'JWT' });
  const body = encodeSegment(payload);
  return `${header}.${body}.signature`;
}

function encodeSegment(value: Record<string, unknown>): string {
  const jsonString = JSON.stringify(value);
  const base64 = btoa(jsonString);
  return base64.replace(/=+$/u, '').replace(/\+/gu, '-').replace(/\//gu, '_');
}
