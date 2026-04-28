import { inject, Injectable } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  CanActivate,
  Router,
  RouterStateSnapshot,
} from '@angular/router';

import { UserRole } from './auth.models';
import { AuthService } from './auth.service';

/**
 * Role-based access control guard.
 *
 * Checks if the current user has any of the required roles specified in route data.
 * If user lacks required roles, redirects to /unauthorized.
 *
 * Usage in routes:
 * {
 *   path: 'some-route',
 *   canActivate: [RoleGuard],
 *   data: { roles: ['admin', 'conversations_privileged'] }
 * }
 */
@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): boolean {
    const requiredRoles = (route.data?.['roles'] ?? []) as (
      | UserRole
      | string
    )[];

    // If no roles specified, allow access
    if (!requiredRoles.length) {
      return true;
    }

    // Check if user has any of the required roles
    const hasAccess = this.authService.hasAnyRole(requiredRoles);

    if (hasAccess) {
      return true;
    }

    // User lacks required roles, redirect to unauthorized
    void this.router.navigate(['/unauthorized'], {
      queryParams: { returnUrl: state.url },
    });

    return false;
  }
}
