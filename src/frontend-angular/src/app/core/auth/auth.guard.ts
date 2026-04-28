import { inject, Injectable } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  CanActivate,
  Router,
  RouterStateSnapshot,
} from '@angular/router';
import { map } from 'rxjs';

import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return this.authService.getCurrentUser().pipe(
      map((user: any) => {
        if (user) {
          return true;
        }

        void this.router.navigate(['/login'], {
          queryParams: { returnUrl: state.url },
        });

        return false;
      })
    );
  }
}
