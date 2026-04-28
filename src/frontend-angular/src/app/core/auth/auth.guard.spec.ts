import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { firstValueFrom, of } from 'rxjs';

import { AuthGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let authService: jest.Mocked<AuthService>;
  let router: Router;
  let navigateSpy: jest.SpyInstance;

  beforeEach(() => {
    const authServiceMock = {
      getCurrentUser: jest.fn(),
      isAuthenticated: jest.fn(),
      hasRole: jest.fn(),
      hasAnyRole: jest.fn(),
      getAccessToken: jest.fn(),
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    };

    TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      providers: [
        AuthGuard,
        { provide: AuthService, useValue: authServiceMock },
      ],
    });

    guard = TestBed.inject(AuthGuard);
    authService = TestBed.inject(AuthService) as jest.Mocked<AuthService>;
    router = TestBed.inject(Router);
    navigateSpy = jest.spyOn(router, 'navigate').mockResolvedValue(true);
  });

  afterEach(() => {
    navigateSpy.mockRestore();
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('should allow access when user is authenticated', async () => {
    const mockUser = { id: '1', username: 'admin', roles: ['admin'] };
    authService.getCurrentUser.mockReturnValue(of(mockUser));

    const route = {} as any;
    const state = { url: '/dashboard' } as any;

    const result = await firstValueFrom(guard.canActivate(route, state));

    expect(result).toBe(true);
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('should deny access and redirect to login when user is not authenticated', async () => {
    authService.getCurrentUser.mockReturnValue(of(null));

    const route = {} as any;
    const state = { url: '/dashboard' } as any;

    const result = await firstValueFrom(guard.canActivate(route, state));

    expect(result).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/dashboard' },
    });
  });

  it('should redirect to login with correct return URL', async () => {
    authService.getCurrentUser.mockReturnValue(of(null));

    const route = {} as any;
    const state = { url: '/admin/users' } as any;

    const result = await firstValueFrom(guard.canActivate(route, state));

    expect(result).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/login'], {
      queryParams: { returnUrl: '/admin/users' },
    });
  });
});
