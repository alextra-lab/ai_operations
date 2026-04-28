import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError } from 'rxjs/operators';

import { ErrorHandlingService } from '../services/error-handling.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const errorHandlingService = inject(ErrorHandlingService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle different types of errors
      if (error.status === 401) {
        // Handle authentication errors
        handleAuthenticationError(error, router);
      } else if (error.status === 403) {
        // Handle authorization errors
        handleAuthorizationError(error);
      } else if (error.status >= 500) {
        // Handle server errors
        handleServerError(error);
      }

      // Let the error handling service process all errors
      return errorHandlingService.handleError(error);
    })
  );
};

function handleAuthenticationError(
  error: HttpErrorResponse,
  router: Router
): void {
  // Store current URL for return after login
  const currentUrl = router.url;
  if (currentUrl && currentUrl !== '/login' && currentUrl !== '/') {
    sessionStorage.setItem('returnUrl', currentUrl);
  }

  // Clear stored tokens
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('current_user');

  // Redirect to login
  console.log('Authentication failed, redirecting to login...');
  void router.navigate(['/login'], {
    queryParams: { expired: 'true' },
  });
}

function handleAuthorizationError(error: HttpErrorResponse): void {
  // Handle authorization errors (user doesn't have permission)
  console.log('Access denied for this resource');
}

function handleServerError(error: HttpErrorResponse): void {
  // Handle server errors
  console.error('Server error occurred:', error);
}
