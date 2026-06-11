import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { RoleManagementService } from '../../services/role-management.service';

/**
 * Assign Use Case Dialog Component
 *
 * Dialog for assigning use cases to roles with optional expiration.
 * WCAG 2.1 AA compliant with proper labels and error messages.
 */
@Component({
  selector: 'app-assign-use-case-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
  ],
  templateUrl: './assign-use-case-dialog.component.html',
  styleUrls: ['./assign-use-case-dialog.component.scss'],
})
export class AssignUseCaseDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  assignForm: FormGroup;
  isSubmitting = false;
  error: string | null = null;
  useCases: any[] = [];
  isLoadingUseCases = true;

  constructor(
    private fb: FormBuilder,
    private roleService: RoleManagementService,
    private dialogRef: MatDialogRef<AssignUseCaseDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { roleName: string }
  ) {
    this.assignForm = this.fb.group({
      use_case_id: ['', Validators.required],
      expires_at: [null],
      metadata_reason: [''],
      metadata_approved_by: [''],
      metadata_ticket: [''],
    });
  }

  ngOnInit(): void {
    this.loadUseCases();
  }

  loadUseCases(): void {
    this.isLoadingUseCases = true;
    this.roleService.getAvailableUseCases().subscribe({
      next: (response: any) => {
        // Response is paginated with use_cases array
        this.useCases = response.use_cases || [];
        this.isLoadingUseCases = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
      error: (err) => {
        console.error('Failed to load use cases:', err);
        this.error = 'Failed to load available use cases';
        this.isLoadingUseCases = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
    });
  }

  onSubmit(): void {
    if (this.assignForm.invalid) {
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const formValue = this.assignForm.value;

    // Build metadata object
    const metadata: any = {};
    if (formValue.metadata_reason) {
      metadata.reason = formValue.metadata_reason;
    }
    if (formValue.metadata_approved_by) {
      metadata.approved_by = formValue.metadata_approved_by;
    }
    if (formValue.metadata_ticket) {
      metadata.ticket = formValue.metadata_ticket;
    }

    const request = {
      use_case_id: formValue.use_case_id,
      expires_at: formValue.expires_at
        ? formValue.expires_at.toISOString()
        : undefined,
      metadata,
    };

    this.roleService
      .assignUseCaseToRole(this.data.roleName, request)
      .subscribe({
        next: () => {
          this.dialogRef.close(true);
        },
        error: (err: any) => {
          this.isSubmitting = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.error = err.error?.detail || 'Failed to assign use case';
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }

  getUseCaseName(useCase: any): string {
    return useCase.name || useCase.use_case_id || 'Unnamed';
  }

  getUseCaseDetails(useCase: any): string {
    const parts = [];
    if (useCase.category) parts.push(useCase.category);
    if (useCase.intent_type) parts.push(useCase.intent_type);
    if (useCase.lifecycle_state) parts.push(useCase.lifecycle_state);
    return parts.length > 0 ? parts.join(' • ') : '';
  }
}
