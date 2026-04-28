import { HttpContext, HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';

import { AuthService } from '../auth/auth.service';
import { BYPASS_AUTH_INTERCEPTOR } from '../auth/http-context-tokens';

export function authInterceptor(
  request: HttpRequest<unknown>,
  next: HttpHandlerFn
) {
  const context = request.context ?? new HttpContext();

  if (context.get(BYPASS_AUTH_INTERCEPTOR)) {
    return next(request);
  }

  const authService = inject(AuthService);
  const token = authService.getAccessToken();

  if (!token) {
    return next(request);
  }

  const authorized = request.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`,
    },
  });

  return next(authorized);
}
