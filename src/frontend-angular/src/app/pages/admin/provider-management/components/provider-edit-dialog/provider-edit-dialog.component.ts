/**
 * Provider Edit Dialog Component
 *
 * Dialog for editing existing Inference Gateway providers.
 */

import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import {
  ProviderConfig,
  ProviderStatus,
  ProviderType,
  UpdateProviderRequest,
} from '../../models/provider-management.models';
import { ProviderManagementService } from '../../services/provider-management.service';

@Component({
  selector: 'app-provider-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  templateUrl: './provider-edit-dialog.component.html',
  styleUrls: ['./provider-edit-dialog.component.scss'],
})
export class ProviderEditDialogComponent {
  form: FormGroup;
  isSubmitting = false;
  error: string | null = null;

  providerTypes: ProviderType[] = [
    'openai',
    'mistral',
    'anthropic',
    'local',
    'custom',
  ];
  statuses: ProviderStatus[] = ['active', 'disabled', 'error', 'testing'];

  constructor(
    private fb: FormBuilder,
    private providerService: ProviderManagementService,
    private dialogRef: MatDialogRef<ProviderEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: { provider: ProviderConfig }
  ) {
    this.form = this.fb.group({
      name: [
        data.provider.name,
        [Validators.required, Validators.maxLength(255)],
      ],
      provider_type: [data.provider.provider_type, Validators.required],
      base_url: [
        data.provider.base_url,
        [Validators.required, Validators.maxLength(500)],
      ],
      api_key: [''],
      is_enabled: [data.provider.is_enabled],
      status: [data.provider.status, Validators.required],
      priority: [
        data.provider.priority,
        [Validators.required, Validators.min(0)],
      ],
      health_check_url: [data.provider.health_check_url || ''],
    });
  }

  onSubmit(): void {
    if (this.form.invalid || !this.data.provider.id) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const request: UpdateProviderRequest = {
      name: this.form.value.name,
      provider_type: this.form.value.provider_type,
      base_url: this.form.value.base_url,
      is_enabled: this.form.value.is_enabled,
      status: this.form.value.status,
      priority: this.form.value.priority,
      health_check_url: this.form.value.health_check_url || undefined,
    };

    // Only include API key if user entered one
    if (this.form.value.api_key) {
      request.api_key = this.form.value.api_key;
    }

    this.providerService
      .updateProvider(this.data.provider.id, request)
      .subscribe({
        next: () => {
          this.dialogRef.close(true);
        },
        error: (err) => {
          console.error('Error updating provider:', err);
          this.error =
            err.error?.detail || 'Failed to update provider. Please try again.';
          this.isSubmitting = false;
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
