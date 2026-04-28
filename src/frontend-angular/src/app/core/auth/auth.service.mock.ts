/**
 * Reusable AuthService Mock Factory
 *
 * Provides complete mock implementations for AuthService to be used in tests.
 * Ensures all methods are properly mocked to prevent "is not a function" errors.
 *
 * Usage:
 * ```typescript
 * import { createMockAuthService } from './auth.service.mock';
 *
 * const mockAuthService = createMockAuthService();
 * TestBed.configureTestingModule({
 *   providers: [{ provide: AuthService, useValue: mockAuthService }]
 * });
 * ```
 */

import { of } from 'rxjs';
import { UserProfile, UserRole } from './auth.models';
import { AuthService } from './auth.service';

export interface MockAuthServiceConfig {
  currentUser?: UserProfile | null;
  isAuthenticated?: boolean;
  hasRole?: boolean;
  hasAnyRole?: boolean;
  accessToken?: string | null;
}

/**
 * Creates a complete mock AuthService with all methods implemented
 */
export function createMockAuthService(
  config: MockAuthServiceConfig = {}
): Partial<AuthService> {
  const {
    currentUser = {
      id: 'test-user',
      username: 'testuser',
      full_name: 'Test User',
      roles: ['user'] as UserRole[],
      expires_at: undefined,
    },
    isAuthenticated = true,
    hasRole = false,
    hasAnyRole = false,
    accessToken = 'mock-token',
  } = config;

  return {
    getCurrentUser: jest.fn().mockReturnValue(of(currentUser)),
    isAuthenticated: jest.fn().mockReturnValue(isAuthenticated),
    hasRole: jest.fn().mockReturnValue(hasRole),
    hasAnyRole: jest.fn().mockReturnValue(hasAnyRole),
    getAccessToken: jest.fn().mockReturnValue(accessToken),
    login: jest.fn().mockReturnValue(of(currentUser as UserProfile)),
    logout: jest.fn().mockReturnValue(of(void 0)),
    refreshToken: jest.fn().mockReturnValue(
      of({
        accessToken: accessToken || 'mock-access-token',
        refreshToken: 'mock-refresh-token',
        accessTokenExpiresAt: Date.now() + 3600000,
        refreshTokenExpiresAt: Date.now() + 86400000,
      })
    ),
  };
}
