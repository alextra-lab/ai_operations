import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly loginForm = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly sessionExpiredMessage = signal<string | null>(null);

  constructor() {
    // Check if user arrived here due to session expiry
    const expired = this.route.snapshot.queryParamMap.get('expired');
    if (expired === 'true') {
      this.sessionExpiredMessage.set(
        'Your session has expired. Please log in again.'
      );
    }
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.isSubmitting()) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const credentials = this.loginForm.getRawValue();
    this.authService
      .login(credentials)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.isSubmitting.set(false);

          // Check sessionStorage first, then query param, then default
          const storedReturnUrl = sessionStorage.getItem('returnUrl');
          const returnUrl =
            storedReturnUrl ??
            this.route.snapshot.queryParamMap.get('returnUrl') ??
            '/dashboard';

          // Clear the stored return URL
          sessionStorage.removeItem('returnUrl');

          void this.router.navigateByUrl(returnUrl);
        },
        error: (error: unknown) => {
          this.isSubmitting.set(false);
          this.errorMessage.set(this.resolveErrorMessage(error));
        },
      });
  }

  private resolveErrorMessage(error: unknown): string {
    if (
      typeof error === 'object' &&
      error !== null &&
      'error' in error &&
      typeof (error as { error?: unknown }).error === 'object'
    ) {
      const { detail } = (error as { error?: { detail?: string } }).error ?? {};
      if (detail) {
        return detail;
      }
    }

    return 'Unable to sign in with the provided credentials.';
  }
}
