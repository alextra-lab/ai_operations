import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';

import { AuthService } from './auth.service';
import { RoleGuard } from './role.guard';

describe('RoleGuard', () => {
  let guard: RoleGuard;
  let authService: jest.Mocked<AuthService>;
  let router: Router;
  let navigateSpy: jest.SpyInstance;

  beforeEach(() => {
    const authServiceMock = {
      getCurrentUser: jest.fn(),
      hasAnyRole: jest.fn(),
      isAuthenticated: jest.fn(),
      hasRole: jest.fn(),
      getAccessToken: jest.fn(),
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    };

    TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      providers: [
        RoleGuard,
        { provide: AuthService, useValue: authServiceMock },
      ],
    });

    guard = TestBed.inject(RoleGuard);
    authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
    router = TestBed.inject(Router);
    navigateSpy = jest.spyOn(router, 'navigate').mockResolvedValue(true);

    // Set default return values
    authService.isAuthenticated.mockReturnValue(true);
    authService.hasRole.mockReturnValue(false);
    authService.getAccessToken.mockReturnValue('mock-token');
  });

  afterEach(() => {
    navigateSpy.mockRestore();
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('should allow access when user has required role', () => {
    authService.hasAnyRole.mockReturnValue(true);

    const route = { data: { roles: ['admin'] } } as any;
    const state = { url: '/admin' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(true);
    expect(authService.hasAnyRole).toHaveBeenCalledWith(['admin']);
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('should deny access and redirect to unauthorized when user lacks required role', () => {
    authService.hasAnyRole.mockReturnValue(false);

    const route = { data: { roles: ['admin'] } } as any;
    const state = { url: '/admin' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(false);
    expect(authService.hasAnyRole).toHaveBeenCalledWith(['admin']);
    expect(navigateSpy).toHaveBeenCalledWith(['/unauthorized'], {
      queryParams: { returnUrl: '/admin' },
    });
  });

  it('should allow access when no roles are required', () => {
    const route = { data: {} } as any;
    const state = { url: '/dashboard' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(true);
    expect(authService.hasAnyRole).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('should allow access when roles array is empty', () => {
    const route = { data: { roles: [] } } as any;
    const state = { url: '/dashboard' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(true);
    expect(authService.hasAnyRole).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('should deny access when user lacks required role (not authenticated scenario)', () => {
    authService.hasAnyRole.mockReturnValue(false);

    const route = { data: { roles: ['admin'] } } as any;
    const state = { url: '/admin' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/unauthorized'], {
      queryParams: { returnUrl: '/admin' },
    });
    expect(authService.hasAnyRole).toHaveBeenCalledWith(['admin']);
  });

  it('should handle multiple required roles', () => {
    authService.hasAnyRole.mockReturnValue(true);

    const route = { data: { roles: ['admin', 'corpus_admin'] } } as any;
    const state = { url: '/admin' } as any;

    const result = guard.canActivate(route, state);

    expect(result).toBe(true);
    expect(authService.hasAnyRole).toHaveBeenCalledWith([
      'admin',
      'corpus_admin',
    ]);
  });
});
