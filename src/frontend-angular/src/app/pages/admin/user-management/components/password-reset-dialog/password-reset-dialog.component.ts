import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { UserListItem } from '../../models/user-management.models';
import { UserManagementService } from '../../services/user-management.service';

/**
 * Password Reset Dialog Component
 *
 * Dialog for admin password reset functionality.
 * WCAG 2.1 AA compliant.
 */
@Component({
  selector: 'app-password-reset-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
  ],
  templateUrl: './password-reset-dialog.component.html',
  styleUrls: ['./password-reset-dialog.component.scss'],
})
export class PasswordResetDialogComponent {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  resetForm: FormGroup;
  isSubmitting = false;
  error: string | null = null;

  constructor(
    private fb: FormBuilder,
    private userService: UserManagementService,
    private dialogRef: MatDialogRef<PasswordResetDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { user: UserListItem }
  ) {
    this.resetForm = this.fb.group(
      {
        newPassword: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required],
        forceLogout: [true],
      },
      { validators: this.passwordMatchValidator }
    );
  }

  passwordMatchValidator(group: FormGroup): Record<string, boolean> | null {
    const password = group.get('newPassword')?.value;
    const confirm = group.get('confirmPassword')?.value;
    return password === confirm ? null : { passwordMismatch: true };
  }

  getPasswordStrength(): string {
    const password = this.resetForm.get('newPassword')?.value || '';
    if (password.length === 0) return '';
    if (password.length < 8) return 'weak';
    if (
      password.length >= 12 &&
      /[A-Z]/.test(password) &&
      /[0-9]/.test(password) &&
      /[^A-Za-z0-9]/.test(password)
    ) {
      return 'strong';
    }
    return 'medium';
  }

  onSubmit(): void {
    if (this.resetForm.invalid) {
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const { newPassword, forceLogout } = this.resetForm.value;

    this.userService
      .resetPassword(this.data.user.id, newPassword, forceLogout)
      .subscribe({
        next: () => {
          this.dialogRef.close(true);
        },
        error: (err: any) => {
          this.isSubmitting = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.error = err.error?.detail || 'Failed to reset password';
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
